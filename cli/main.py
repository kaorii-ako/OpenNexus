# cli/main.py
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from backend.core.config import load_config
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from backend.agents.chat import chat_once, chat_stream

app = typer.Typer(help="NEXUS — personal intelligence layer")
console = Console(legacy_windows=False)
_cfg = None
_engine = None
_store = None


def _init():
    global _cfg, _engine, _store
    if _cfg is None:
        _cfg = load_config()
        _engine = OllamaEngine(
            base_url=_cfg.ollama.base_url,
            model=_cfg.ollama.model_general,
            embed_model=_cfg.ollama.model_embed,
        )
        _engine.set_models(_cfg.ollama.model_code, _cfg.ollama.model_reasoning)
        _store = MemoryStore(Path(_cfg.memory.chroma_dir).expanduser())
    return _cfg, _engine, _store


@app.command()
def ask(query: str = typer.Argument(..., help="Question to ask NEXUS")):
    """Single-shot query with rich markdown output."""
    cfg, engine, store = _init()

    async def _run():
        response, chunks = await chat_once(query, "cli", cfg, engine, store)
        console.print(Markdown(response))
        if chunks:
            sources = ", ".join(c.get("page_title", "?") for c in chunks[:3])
            console.print(f"[dim]Sources: {sources}[/dim]")

    asyncio.run(_run())


@app.command()
def chat():
    """Interactive REPL with persistent session history."""
    cfg, engine, store = _init()
    history = []
    console.print(Panel(
        "[bold]NEXUS Chat[/bold] — /code · /think · Ctrl+C to exit",
        style="dim"
    ))

    async def _loop():
        while True:
            try:
                query = typer.prompt("you")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]goodbye[/dim]")
                break
            tokens = []
            async for token in chat_stream(query, "interactive", cfg, engine, store, history=history):
                console.print(token, end="", highlight=False)
                tokens.append(token)
            response = "".join(tokens)
            console.print()
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": response})

    asyncio.run(_loop())


@app.command()
def serve():
    """Start FastAPI server + open browser."""
    cfg, _, _ = _init()
    import uvicorn
    from backend.api.main import create_app
    web_app = create_app(cfg)
    if cfg.server.open_browser_on_start:
        import webbrowser
        import threading
        threading.Timer(1.5, lambda: webbrowser.open(
            f"http://{cfg.server.host}:{cfg.server.port}"
        )).start()
    uvicorn.run(web_app, host=cfg.server.host, port=cfg.server.port)


@app.command()
def doctor():
    """Health check: Ollama, ChromaDB, all connectors."""
    cfg, engine, store = _init()
    import httpx

    async def _check():
        console.print(Panel("[bold]NEXUS Doctor[/bold]"))
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{cfg.ollama.base_url}/api/tags")
                models = r.json().get("models", [])
                console.print(f"[green]✓[/green] Ollama reachable — {len(models)} models loaded")
        except Exception as e:
            console.print(f"[red]✗[/red] Ollama unreachable: {e}")
        console.print("[green]✓[/green] ChromaDB accessible")
        console.print("[dim]Run 'nexus connect <service>' to set up connectors[/dim]")

    asyncio.run(_check())


@app.command()
def sync():
    """Force Notion sync now (don't wait for 15-min schedule)."""
    cfg, _, _ = _init()
    from backend.connectors.notion_sync import NotionSync

    async def _run():
        syncer = NotionSync(cfg)
        updated = await syncer.sync_all()
        console.print(f"[green]✓[/green] Notion sync complete — {len(updated)} pages updated")

    asyncio.run(_run())


@app.command()
def note(text: str = typer.Argument(..., help="Idea to capture in Notion Ideas database")):
    """Create a Notion page in the Ideas database."""
    cfg, _, _ = _init()
    from backend.connectors.notion import NotionConnector

    async def _run():
        nc = NotionConnector(cfg)
        await nc.create_idea(text)
        console.print(f"[green]✓[/green] Saved to Ideas: {text}")

    asyncio.run(_run())


@app.command()
def log(text: str = typer.Argument(..., help="Text to append to today's Notion daily page")):
    """Append a block to today's Notion daily note."""
    cfg, _, _ = _init()
    from backend.connectors.notion import NotionConnector

    async def _run():
        nc = NotionConnector(cfg)
        await nc.append_to_daily_notes(text)
        console.print("[green]✓[/green] Logged to today's daily note")

    asyncio.run(_run())


@app.command()
def digest():
    """Run morning briefing now — weather, calendar, email, GitHub, Classroom, RSS."""
    cfg, engine, store = _init()
    from backend.agents.digest import DigestAgent

    async def _run():
        agent = DigestAgent(cfg, engine)
        await agent.run()

    asyncio.run(_run())


@app.command()
def connect(
    service: str = typer.Argument("all", help="Service to connect: google | notion | github | discord | all"),
):
    """Authorize and connect external services."""
    cfg, _, _ = _init()

    if service in ("google", "all"):
        console.print("[bold]Connecting Google (Gmail · Calendar · Classroom)...[/bold]")
        try:
            from backend.connectors.google_auth import authorize_google
            authorize_google(cfg.data_dir)
            console.print("[green]✓ Google authorized[/green]")
        except FileNotFoundError as e:
            console.print(f"[red]✗ {e}[/red]")
        except Exception as e:
            console.print(f"[red]✗ Google auth failed: {e}[/red]")

    if service in ("notion", "all"):
        notion_path = cfg.data_dir / "notion.json"
        if notion_path.exists():
            console.print("[green]✓ Notion token found[/green]")
        else:
            token = typer.prompt("Paste your Notion integration token (secret_...)")
            notion_path.write_text(json.dumps({"token": token}))
            console.print(f"[green]✓ Notion token saved to {notion_path}[/green]")

    if service in ("github", "all"):
        gh_path = cfg.data_dir / "github.json"
        if gh_path.exists():
            console.print("[green]✓ GitHub token found[/green]")
        else:
            token = typer.prompt("Paste your GitHub Personal Access Token")
            gh_path.write_text(json.dumps({"token": token}))
            console.print(f"[green]✓ GitHub token saved to {gh_path}[/green]")

    if service in ("discord", "all"):
        dc_path = cfg.data_dir / "discord.json"
        if dc_path.exists():
            console.print("[green]✓ Discord token found[/green]")
        else:
            token = typer.prompt("Paste your Discord Bot token (Bot <token>)")
            dc_path.write_text(json.dumps({"token": token}))
            console.print(f"[green]✓ Discord token saved to {dc_path}[/green]")


if __name__ == "__main__":
    app()
