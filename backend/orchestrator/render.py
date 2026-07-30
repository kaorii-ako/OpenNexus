"""The single rendering path for events.

Requirement 1c is architectural, not descriptive: live operation and `nexus
replay` must render through the same code. They do — both call `render_line()`
below, and the HUD consumes `render_model()` for both its live poll and its
replay feed. There is no second formatter anywhere in this codebase, so a
"recorded demo" that looked different from live output could not be produced
even deliberately.
"""
from __future__ import annotations

from typing import Any

from rich.text import Text

from backend.orchestrator import events as ev
from backend.orchestrator.events import Event
from backend.orchestrator.router import CLEAN, CORRECTED, UNUSED

OUTCOME_STYLE = {
    CLEAN: "green",
    CORRECTED: "yellow",
    UNUSED: "cyan",
}

TYPE_STYLE = {
    ev.ROUTE: "bold white",
    ev.ANSWER: "bold cyan",
    ev.EVOLVE_PROPOSED: "bold magenta",
    ev.EVOLVE_APPLIED: "bold green",
    ev.EVOLVE_REJECTED: "bold red",
    ev.EVOLVE_REVERTED: "bold yellow",
    ev.EVOLVE_NO_SIGNAL: "dim",
}


def _clock(event: Event) -> str:
    dt = event.dt
    return dt.strftime("%H:%M:%S") if dt else "--:--:--"


def render_model(event: Event) -> dict[str, Any]:
    """Structured render form — what the HUD draws, live or replayed."""
    p = event.payload
    model: dict[str, Any] = {
        "id": event.id,
        "seq": event.seq,
        "ts": event.ts,
        "clock": _clock(event),
        "run_id": event.run_id,
        "type": event.type,
        "outcome": p.get("outcome", ""),
        "headline": "",
        "detail": [],
    }

    if event.type == ev.ROUTE:
        loaded = p.get("loaded_branches", []) or []
        model["headline"] = p.get("query", "")
        model["branches"] = loaded
        detail = [f"loaded: {', '.join(loaded) or 'none'}"]

        triggers = p.get("matched_triggers", {}) or {}
        if triggers:
            shown = "; ".join(f"{b}←{', '.join(t)}" for b, t in sorted(triggers.items()))
            detail.append(f"triggers: {shown}")

        for c in p.get("corrections", []) or []:
            detail.append(
                f"correction: +{c.get('added_branch')} (entity '{c.get('entity')}' "
                f"had no matching trigger)"
            )
        for b in p.get("unused_branches", []) or []:
            detail.append(f"unused: {b} loaded but contributed nothing")
        model["detail"] = detail

    elif event.type == ev.ANSWER:
        model["headline"] = p.get("query", "")
        detail = [
            f"answered in {p.get('duration_ms', 0)}ms · {p.get('answer_chars', 0)} chars"
            + (f" · {p.get('model')}" if p.get("model") else "")
        ]
        detail.append(
            f"grounded in {', '.join(p.get('branches', []) or [])} "
            f"({p.get('context_chars', 0)} chars of skill context)"
            if p.get("grounded")
            else "no skill context matched — answered from general knowledge"
        )
        model["detail"] = detail

    elif event.type == ev.EVOLVE_PROPOSED:
        model["headline"] = f"proposed {p.get('pattern', '?')} → {p.get('target', '?')}"
        model["detail"] = [
            p.get("reason", ""),
            f"cites {len(p.get('cited_events', []) or [])} event(s)",
        ]

    elif event.type == ev.EVOLVE_APPLIED:
        model["headline"] = f"applied {p.get('proposal_id', '?')} → {p.get('target', '?')}"
        model["detail"] = [f"note: {p.get('note', '')}", f"revert id: {p.get('proposal_id', '')}"]

    elif event.type == ev.EVOLVE_REJECTED:
        model["headline"] = f"rejected {p.get('proposal_id', '?')} → {p.get('target', '?')}"
        model["detail"] = [p.get("reason", "") or "no reason given"]

    elif event.type == ev.EVOLVE_REVERTED:
        model["headline"] = f"reverted {p.get('proposal_id', '?')} → {p.get('target', '?')}"
        model["detail"] = [f"restored from note: {p.get('note', '')}"]

    elif event.type == ev.EVOLVE_NO_SIGNAL:
        model["headline"] = "not enough signal yet — no proposal made"
        model["detail"] = [p.get("reason", "")]

    model["detail"] = [d for d in model["detail"] if d]
    return model


def render_line(event: Event) -> Text:
    """One event as a terminal line. Live routing and replay both call this."""
    model = render_model(event)
    line = Text()
    line.append(f"{model['clock']} ", style="dim")
    line.append(f"#{model['seq']:<4} ", style="dim")
    line.append(f"{model['type']:<16} ", style=TYPE_STYLE.get(event.type, "white"))

    outcome = model.get("outcome")
    if outcome:
        line.append(f"[{outcome}] ", style=OUTCOME_STYLE.get(outcome, "white"))

    line.append(model["headline"])
    for detail in model["detail"]:
        line.append(f"\n{'':>12}└ {detail}", style="dim")
    return line
