"""CLI commands for the orchestrator: route, evolve, replay, events, hud, setup.

These deliberately do not load `nexus.toml` or an LLM backend. Routing, replay
and evolution are filesystem-and-log operations; requiring an API key to inspect
your own history would be silly.
"""
from __future__ import annotations

import json as jsonlib
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from backend.orchestrator import constitution, evolve as evolve_mod, guardrails, replay as replay_mod
from backend.orchestrator import paths, render, skills as skills_mod, vault
from backend.orchestrator.events import EventLog, new_run_id
from backend.orchestrator.hud_server import DEFAULT_PORT
from backend.orchestrator.router import Orchestrator, Router

console = Console(legacy_windows=False)


def _require_constitution() -> dict:
    try:
        return constitution.get()
    except constitution.ConstitutionError as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1)


# --- nexus route --------------------------------------------------------------


def route(
    query: str = typer.Argument(..., help="Query to route"),
    answer: bool = typer.Option(False, "--answer", "-a", help="Also answer, grounded in the loaded skills"),
    show_context: bool = typer.Option(False, "--show-context", help="Print the skill content the loaded branches contribute"),
    json_out: bool = typer.Option(False, "--json", help="Emit the routing event as JSON"),
):
    """Route a query through the skill orchestrator and log the decision."""
    _require_constitution()
    orch = Orchestrator()

    if not orch.router.skills:
        console.print(
            f"[red]✗[/red] No skills found under {paths.skills_dir()}. "
            "Run [bold]nexus setup[/bold] first."
        )
        raise typer.Exit(1)

    if answer:
        _answer(query)
        return

    decision, event = orch.handle(query)

    if json_out:
        console.print_json(jsonlib.dumps(event.to_dict()))
        return

    console.print(render.render_line(event))

    if decision.was_corrected:
        console.print(
            "\n[yellow]This turn needed a mid-turn correction.[/yellow] "
            "[dim]`nexus evolve` will pick this up once the pattern repeats.[/dim]"
        )

    if show_context:
        context = orch.context_for(decision)
        if context:
            console.print(Panel(context, title="loaded skill context", border_style="dim"))
        else:
            console.print("[dim]No skill content loaded for this query.[/dim]")


def _build_agent():
    """Load config and backend, reporting any failure in actionable terms."""
    from backend.core.config import load_config
    from backend.core.llm import create_backend
    from backend.core.llm.factory import LLMUnavailable
    from backend.orchestrator.agent import NexusAgent

    try:
        cfg = load_config(paths.repo_root() / "nexus.toml")
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1)

    try:
        engine = create_backend(cfg.llm)
    except LLMUnavailable as exc:
        # markup=False: these messages contain literal [llm] / [connectors.x]
        # section names that Rich would otherwise parse away as style tags.
        console.print("[red]✗ no language model available[/red]")
        console.print(str(exc), markup=False, highlight=False)
        raise typer.Exit(1)

    return NexusAgent(cfg, engine)


def _answer(query: str) -> None:
    """Route, then stream a grounded answer."""
    import asyncio

    agent = _build_agent()

    async def _run():
        async for chunk in agent.answer_stream(query):
            kind = chunk["type"]
            if kind == "route":
                console.print(render.render_line(chunk["event"]))
                console.print()
            elif kind == "token":
                console.print(chunk["text"], end="", highlight=False)
            elif kind == "error":
                console.print(f"\n[red]✗ {chunk['error']}[/red]")
            elif kind == "done":
                console.print()
                console.print(render.render_line(chunk["event"]))

    asyncio.run(_run())


# --- nexus evolve -------------------------------------------------------------


def _print_findings(findings, notes) -> None:
    if findings:
        table = Table(title="friction found in real events", border_style="dim")
        table.add_column("pattern")
        table.add_column("branch")
        table.add_column("subject")
        table.add_column("seen", justify="right")
        for finding in findings:
            table.add_row(finding.pattern, finding.branch, finding.subject, str(finding.occurrences))
        console.print(table)
    for note in notes:
        console.print(f"[dim]· {note}[/dim]")


def evolve(
    revert: str = typer.Option("", "--revert", help="Revert an applied edit by proposal id"),
    history: bool = typer.Option(False, "--history", help="List applied, rejected and reverted edits"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show findings without proposing an edit"),
):
    """Review the event log and propose one minimal skill edit."""
    _require_constitution()
    log = EventLog()
    run_id = new_run_id()

    if revert:
        try:
            restored, note_path, event = evolve_mod.revert(revert, log, run_id)
        except evolve_mod.RevertError as exc:
            console.print(f"[red]✗[/red] {exc}")
            raise typer.Exit(1)
        except guardrails.GuardrailViolation as exc:
            console.print(f"[red]✗ guardrail[/red] {exc}")
            raise typer.Exit(1)
        console.print(f"[green]✓[/green] Restored [bold]{restored}[/bold] from {note_path.name}")
        console.print(render.render_line(event))
        return

    if history:
        _print_history(log)
        return

    skills = skills_mod.load_skills()
    findings, notes = evolve_mod.analyse(log, skills)

    if dry_run:
        _print_findings(findings, notes)
        if not findings:
            console.print("[dim]Nothing actionable. No proposal would be made.[/dim]")
        return

    try:
        proposal = evolve_mod.next_proposal(log, skills)
    except evolve_mod.NotEnoughSignal as exc:
        event = log.append(
            "evolve_no_signal", {"reason": exc.reason, "route_events": len(log.by_type("route"))}, run_id
        )
        console.print(
            Panel(
                f"[bold]Not enough signal yet.[/bold]\n\n{exc.reason}\n\n"
                "[dim]No proposal was made. Keep using the system — evolution needs real "
                "routing history, and inventing a plausible improvement here would make "
                "the whole log untrustworthy.[/dim]",
                border_style="yellow",
            )
        )
        console.print(render.render_line(event))
        return

    evolve_mod.record_proposal(proposal, log, run_id)

    console.print(Panel(
        f"[bold]{proposal.pattern}[/bold] → [bold]{proposal.rel_target}[/bold]\n\n{proposal.reason}",
        title=f"proposal {proposal.id}",
        border_style="magenta",
    ))

    citations = proposal.citations()
    if citations:
        console.print("[bold]Motivating events[/bold] [dim](check these against the log)[/dim]")
        for cite in citations:
            console.print(f"  [dim]·[/dim] {cite}")
    else:
        console.print(
            "[dim]No cited events — this finding is verified against the filesystem, "
            "not inferred from the log.[/dim]"
        )

    console.print("\n[bold]Diff[/bold]")
    console.print(Syntax(proposal.diff(), "diff", theme="ansi_dark", background_color="default"))

    if proposal.caveat:
        console.print(Panel(proposal.caveat, title="what this cannot fix", border_style="yellow"))

    console.print(Panel(guardrails.describe_scope(), title="write scope", border_style="dim"))

    approved = typer.confirm("Apply this edit?", default=False)

    if not approved:
        reason = typer.prompt("Why not? (optional, helps avoid re-proposing)", default="", show_default=False)
        event = evolve_mod.reject(proposal, log, run_id, reason)
        console.print(f"[red]✗[/red] Rejected. This exact edit will not be proposed again.")
        console.print(render.render_line(event))
        return

    try:
        written, note_path, event = evolve_mod.apply(proposal, log, run_id)
    except guardrails.GuardrailViolation as exc:
        console.print(f"[red]✗ guardrail refused the write[/red]\n{exc}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Applied to [bold]{written}[/bold]")
    console.print(f"[green]✓[/green] Vault note [bold]{note_path}[/bold]")
    console.print(f"[dim]Revert with: nexus evolve --revert {proposal.id}[/dim]")
    console.print(render.render_line(event))


def _print_history(log: EventLog) -> None:
    rows = log.by_type("evolve_applied", "evolve_rejected", "evolve_reverted")
    if not rows:
        console.print("[dim]No evolution history yet.[/dim]")
        return
    table = Table(title="evolution history", border_style="dim")
    table.add_column("when")
    table.add_column("what")
    table.add_column("id")
    table.add_column("target")
    table.add_column("pattern")
    for event in rows:
        table.add_row(
            event.ts[:19],
            event.type.replace("evolve_", ""),
            str(event.payload.get("proposal_id", "")),
            str(event.payload.get("target", "")),
            str(event.payload.get("pattern", "")),
        )
    console.print(table)


# --- nexus replay -------------------------------------------------------------


def replay(
    run: str = typer.Option("", "--run", help="Replay one run id"),
    since: str = typer.Option("", "--since", help="ISO timestamp, date, or relative span (2h, 7d)"),
    last: int = typer.Option(0, "--last", help="Replay only the last N events"),
    speed: float = typer.Option(1.0, "--speed", help="Playback multiplier for original pacing"),
    pace: str = typer.Option("original", "--pace", help="original | fixed"),
    interval: float = typer.Option(0.4, "--interval", help="Seconds between events when --pace fixed"),
):
    """Re-emit real logged events. Same log, same renderer as live operation."""
    log = EventLog()
    try:
        selection = replay_mod.select(log, run=run or None, since=since or None, last=last or None)
    except replay_mod.SelectionError as exc:
        console.print(f"[yellow]·[/yellow] {exc}")
        raise typer.Exit(1)

    console.print(
        f"[dim]replaying {len(selection.events)} event(s) — {selection.description} "
        f"· pace={pace} speed={speed}x[/dim]\n"
    )

    emitted = replay_mod.run(
        selection,
        emit=lambda e: console.print(render.render_line(e)),
        mode=pace,
        speed=speed,
        interval=interval,
    )
    console.print(f"\n[dim]{emitted} event(s) replayed from memory/events.jsonl[/dim]")


# --- nexus events -------------------------------------------------------------


def events(
    verify: bool = typer.Option(False, "--verify", help="Check the log for tampering"),
    tail: int = typer.Option(20, "--tail", help="Show the last N events"),
    json_out: bool = typer.Option(False, "--json", help="Emit raw JSONL"),
):
    """Inspect the append-only event log."""
    log = EventLog()

    if verify:
        problems = log.verify()
        if not problems:
            console.print(
                f"[green]✓[/green] {log.count()} event(s), log intact "
                "[dim](seq numbers match line numbers, ids unique)[/dim]"
            )
            return
        console.print(f"[red]✗ {len(problems)} integrity problem(s)[/red]")
        for problem in problems:
            console.print(f"  [red]·[/red] {problem}")
        raise typer.Exit(1)

    all_events = log.read_all()
    if not all_events:
        console.print(
            f"[dim]{paths.events_path()} is empty. Run `nexus route \"...\"` to log something.[/dim]"
        )
        return

    shown = all_events[-tail:] if tail else all_events
    if json_out:
        for event in shown:
            print(jsonlib.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True))
        return

    for event in shown:
        console.print(render.render_line(event))
    console.print(f"\n[dim]{len(shown)} of {len(all_events)} event(s)[/dim]")


# --- nexus setup --------------------------------------------------------------


def _status_rows() -> list[tuple[str, bool, str]]:
    root = paths.repo_root()
    skills = skills_mod.load_skills()
    log = EventLog()
    notes = vault.read_notes()

    rows = [
        ("AGENTIC_OS.md", paths.agentic_os_path().is_file(), str(paths.agentic_os_path())),
        ("skills/", bool(skills), f"{len(skills)} branch(es): {', '.join(sorted(skills)) or 'none'}"),
        ("vault/", paths.vault_dir().is_dir(), f"{len(notes)} note(s)"),
        ("memory/events.jsonl", log.exists(), f"{log.count()} event(s)"),
        ("hud/", (root / "hud" / "index.html").is_file(), str(paths.hud_dir())),
        ("nexus.toml", (root / "nexus.toml").is_file(), "LLM config — only needed for ask/chat/digest"),
    ]
    return rows


def setup(
    check: bool = typer.Option(False, "--check", help="Report status without creating anything"),
):
    """Check orchestrator setup, and scaffold anything missing."""
    console.print(Panel("[bold]NEXUS orchestrator setup[/bold]", border_style="dim"))

    if not check:
        for directory in (paths.vault_dir(), paths.memory_dir()):
            directory.mkdir(parents=True, exist_ok=True)
        for sub in ("evolution", "dev", "trading"):
            (paths.vault_dir() / sub).mkdir(parents=True, exist_ok=True)

    table = Table(border_style="dim")
    table.add_column("component")
    table.add_column("", justify="center")
    table.add_column("detail")

    missing = []
    for name, ok, detail in _status_rows():
        table.add_row(name, "[green]✓[/green]" if ok else "[red]✗[/red]", detail)
        if not ok:
            missing.append(name)
    console.print(table)

    try:
        console.print(Panel(guardrails.describe_scope(), title="write scope", border_style="dim"))
    except constitution.ConstitutionError as exc:
        console.print(f"[red]✗[/red] {exc}")

    if missing:
        console.print(f"[yellow]Missing:[/yellow] {', '.join(missing)}")
        if "nexus.toml" in missing:
            console.print("[dim]  nexus.toml → run `nexus init` (only needed for ask/chat/digest)[/dim]")
    else:
        console.print("[green]✓ everything in place[/green]")

    console.print(
        "\n[bold]Next[/bold]\n"
        '  nexus route "why is FlareBisect flaky"   route a query, log the decision\n'
        "  nexus hud                                open the dashboard\n"
        "  nexus evolve                             review the log for friction\n"
        "  nexus replay --last 20                   look at history"
    )


# --- nexus hud ----------------------------------------------------------------


def hud(
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port to serve the HUD on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open a browser window"),
):
    """Serve the HUD locally, reading vault/ and memory/ directly."""
    from backend.orchestrator.hud_server import PortUnavailable, serve

    index = paths.hud_dir() / "index.html"
    if not index.is_file():
        console.print(f"[red]✗[/red] HUD not found at {index}")
        raise typer.Exit(1)

    url = f"http://{host}:{port}"

    def ready() -> None:
        # Only reached once the socket is actually bound, so the browser never
        # opens on a port that failed to come up.
        console.print(f"[bold]NEXUS HUD[/bold] → {url}  [dim]ctrl-c to stop[/dim]")
        if open_browser:
            import threading
            import webbrowser

            threading.Timer(0.4, lambda: webbrowser.open(url)).start()

    try:
        serve(host, port, on_ready=ready)
    except PortUnavailable as exc:
        console.print(f"[red]✗[/red] {exc}")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]stopped[/dim]")
