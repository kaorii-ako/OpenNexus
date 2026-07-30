"""Local HTTP server for the HUD.

Static files plus a handful of JSON endpoints that read `vault/` and
`memory/events.jsonl` directly off disk. Stdlib only — no framework, no
database, no build step.

Binds to 127.0.0.1 by default. The config endpoint can write `nexus.toml`, which
is the reason this is a loopback service and not something to expose.
"""
from __future__ import annotations

import asyncio
import errno
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from backend.orchestrator import constitution, paths, render, skills as skills_mod, vault
from backend.orchestrator.events import (
    EVOLVE_APPLIED,
    EVOLVE_REJECTED,
    EVOLVE_REVERTED,
    ROUTE,
    EventLog,
)
from backend.orchestrator.router import CLEAN, CORRECTED, UNUSED, Orchestrator

# Sentinel for a metric with no real data behind it. The HUD renders this as a
# visible placeholder label rather than a zero, because a fabricated-looking
# number is worse than an honest gap.
NO_DATA = None


def _metrics() -> dict[str, Any]:
    log = EventLog()
    notes = vault.read_notes()
    skills = skills_mod.load_skills()

    all_events = log.read_all()
    route_events = [e for e in all_events if e.type == ROUTE]

    outcomes = {CLEAN: 0, CORRECTED: 0, UNUSED: 0}
    for event in route_events:
        outcome = event.payload.get("outcome")
        if outcome in outcomes:
            outcomes[outcome] += 1

    applied = sum(1 for e in all_events if e.type == EVOLVE_APPLIED)
    rejected = sum(1 for e in all_events if e.type == EVOLVE_REJECTED)
    reverted = sum(1 for e in all_events if e.type == EVOLVE_REVERTED)

    total_routes = len(route_events)
    clean_rate = round(100 * outcomes[CLEAN] / total_routes) if total_routes else NO_DATA

    try:
        min_events = int(constitution.get().get("evolve", {}).get("min_events", 12))
    except constitution.ConstitutionError:
        min_events = NO_DATA

    return {
        "evolve_min_events": min_events,
        "evolve_ready": min_events is not NO_DATA and total_routes >= min_events,
        "vault_notes": len(notes),
        "skill_branches": len(skills),
        "skill_pointers": sum(len(s.pointers) for s in skills.values()),
        "triggers": sum(len(s.triggers) for s in skills.values()),
        "events_total": len(all_events),
        "routes_total": total_routes,
        "outcomes": outcomes,
        "evolve_applied": applied,
        "evolve_rejected": rejected,
        "evolve_reverted": reverted,
        # Hero stat. None when no routing has happened — the HUD shows
        # "no data yet" for that, never a zero dressed up as a score.
        "clean_route_rate": clean_rate,
        "log_intact": len(log.verify()) == 0,
    }


def _status() -> dict[str, Any]:
    root = paths.repo_root()
    log = EventLog()
    skills = skills_mod.load_skills()
    try:
        constitution.get()
        constitution_ok = True
        constitution_error = ""
    except constitution.ConstitutionError as exc:
        constitution_ok = False
        constitution_error = str(exc)

    return {
        "root": str(root),
        "agentic_os": paths.agentic_os_path().is_file(),
        "constitution_ok": constitution_ok,
        "constitution_error": constitution_error,
        "skills": sorted(skills),
        "vault_dir": paths.vault_dir().is_dir(),
        "events_log": log.exists(),
        "nexus_toml": (root / "nexus.toml").is_file(),
        "integrity": log.verify(),
    }


def _skills_payload() -> list[dict[str, Any]]:
    out = []
    for branch, skill in sorted(skills_mod.load_skills().items()):
        out.append({
            "branch": branch,
            "triggers": skill.triggers,
            "pointers": [
                {
                    "name": p.file.name,
                    "target": p.target,
                    "exists": p.target_exists(),
                    "entities": p.entities,
                }
                for p in skill.pointers
            ],
        })
    return out


def _events_payload(since_seq: int = 0) -> list[dict[str, Any]]:
    log = EventLog()
    return [render.render_model(e) for e in log.read_all() if e.seq > since_seq]


def _config_payload() -> dict[str, Any]:
    """Current nexus.toml, with the API key redacted to a boolean."""
    path = paths.repo_root() / "nexus.toml"
    if not path.is_file():
        return {"exists": False}
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except Exception as exc:  # malformed config should not 500 the HUD
        return {"exists": True, "error": str(exc)}

    llm = raw.get("llm", {})
    user = raw.get("user", {})
    weather = raw.get("connectors", {}).get("weather", {})
    return {
        "exists": True,
        "user": {
            "name": user.get("name", ""),
            "timezone": user.get("timezone", ""),
            "role": user.get("role", ""),
        },
        "llm": {
            "provider": llm.get("provider", "ollama"),
            "model": llm.get("model", ""),
            "base_url": llm.get("base_url", ""),
            "embed_model": llm.get("embed_model", ""),
            # Never returned. The HUD shows "set" or "not set".
            "api_key_set": bool(llm.get("api_key")),
        },
        "weather": {
            "location_name": weather.get("location_name", ""),
            "latitude": weather.get("latitude", 0.0),
            "longitude": weather.get("longitude", 0.0),
        },
        "connectors": {
            name: bool(section.get("enabled"))
            for name, section in raw.get("connectors", {}).items()
            if isinstance(section, dict) and "enabled" in section
        },
    }


def _write_config(payload: dict[str, Any]) -> dict[str, Any]:
    """Write nexus.toml from the setup page, preserving an existing API key."""
    from cli.init import ALL_CONNECTORS, CONNECTOR_SECTION, TOML_TEMPLATE

    root = paths.repo_root()
    path = root / "nexus.toml"

    user = payload.get("user", {})
    llm = payload.get("llm", {})
    weather = payload.get("weather", {})
    enabled = set(payload.get("connectors", []) or [])

    api_key = llm.get("api_key", "")
    if not api_key and path.is_file():
        # A blank key from the form means "leave it alone", never "erase it".
        try:
            import tomllib
        except ImportError:  # pragma: no cover
            import tomli as tomllib  # type: ignore[no-redef]
        try:
            with open(path, "rb") as f:
                api_key = tomllib.load(f).get("llm", {}).get("api_key", "")
        except Exception:
            api_key = ""

    timezone = user.get("timezone") or "UTC"
    content = TOML_TEMPLATE.format(
        name=user.get("name") or "User",
        timezone=timezone,
        role=user.get("role") or "",
        provider=llm.get("provider") or "ollama",
        model=llm.get("model") or "llama3.2",
        api_key=api_key,
        base_url=llm.get("base_url") or "",
        embed_model=llm.get("embed_model") or "",
        write_to_notion="true" if "notion" in enabled else "false",
        lat=float(weather.get("latitude") or 0.0),
        lon=float(weather.get("longitude") or 0.0),
        city=weather.get("location_name") or "Your City",
        connector_sections="\n".join(
            CONNECTOR_SECTION.format(name=c, enabled="true" if c in enabled else "false")
            for c in ALL_CONNECTORS
        ),
    )
    path.write_text(content, encoding="utf-8")
    return {"ok": True, "path": str(path)}


class Handler(BaseHTTPRequestHandler):
    server_version = "NexusHUD"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # the CLI already prints what matters

    # --- helpers ---------------------------------------------------------

    def _send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_json({"error": "not found"}, 404)
            return
        content_type, _ = mimetypes.guess_type(str(path))
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return {}

    # --- routing ---------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route_path = parsed.path
        query = parse_qs(parsed.query)

        if route_path == "/api/state":
            self._send_json({
                "metrics": _metrics(),
                "status": _status(),
                "graph": vault.graph(),
                "skills": _skills_payload(),
                "events": _events_payload(),
            })
            return

        if route_path == "/api/events":
            since = int((query.get("since_seq") or ["0"])[0])
            self._send_json({"events": _events_payload(since)})
            return

        if route_path == "/api/graph":
            self._send_json(vault.graph())
            return

        if route_path == "/api/metrics":
            self._send_json(_metrics())
            return

        if route_path == "/api/config":
            self._send_json(_config_payload())
            return

        if route_path.startswith("/api/"):
            self._send_json({"error": "unknown endpoint"}, 404)
            return

        # Static files, confined to hud/.
        hud_root = paths.hud_dir().resolve()
        relative = route_path.lstrip("/") or "index.html"
        target = (hud_root / relative).resolve()
        if not str(target).startswith(str(hud_root)):
            self._send_json({"error": "forbidden"}, 403)
            return
        self._send_file(target)

    def do_POST(self) -> None:  # noqa: N802
        route_path = urlparse(self.path).path
        payload = self._read_json()

        if route_path == "/api/route":
            query = str(payload.get("query", "")).strip()
            if not query:
                self._send_json({"error": "query is required"}, 400)
                return
            orch = Orchestrator()
            decision, event = orch.handle(query)
            self._send_json({
                "event": render.render_model(event),
                "raw": event.to_dict(),
                "corrected": decision.was_corrected,
            })
            return

        if route_path == "/api/ask":
            self._stream_answer(str(payload.get("query", "")).strip())
            return

        if route_path == "/api/config":
            try:
                self._send_json(_write_config(payload))
            except Exception as exc:
                self._send_json({"ok": False, "error": str(exc)}, 400)
            return

        self._send_json({"error": "unknown endpoint"}, 404)

    # --- streaming answer ------------------------------------------------

    def _stream_answer(self, query: str) -> None:
        """Server-sent events: routing decision, then answer tokens.

        Each request already has its own thread (ThreadingHTTPServer), so a
        fresh event loop per request is safe and keeps the async engine API
        usable from this sync handler.
        """
        if not query:
            self._send_json({"error": "query is required"}, 400)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()

        def emit(obj: dict[str, Any]) -> None:
            self.wfile.write(f"data: {json.dumps(obj, default=str)}\n\n".encode("utf-8"))
            self.wfile.flush()

        try:
            from backend.core.config import load_config
            from backend.core.llm import create_backend
            from backend.core.llm.factory import LLMUnavailable
            from backend.orchestrator.agent import NexusAgent

            try:
                cfg = load_config(paths.repo_root() / "nexus.toml")
                engine = create_backend(cfg.llm)
            except (LLMUnavailable, FileNotFoundError, ValueError) as exc:
                # Routing still works without a model, so do that much and say
                # plainly why there is no answer rather than failing silently.
                orch = Orchestrator()
                decision, event = orch.handle(query)
                emit({"type": "route", "event": render.render_model(event)})
                emit({"type": "error", "error": str(exc)})
                return

            agent = NexusAgent(cfg, engine)

            async def drive() -> None:
                async for chunk in agent.answer_stream(query):
                    kind = chunk["type"]
                    if kind == "route":
                        emit({"type": "route", "event": render.render_model(chunk["event"])})
                    elif kind == "token":
                        emit({"type": "token", "text": chunk["text"]})
                    elif kind == "error":
                        emit({"type": "error", "error": chunk["error"]})
                    elif kind == "done":
                        emit({
                            "type": "done",
                            "event": render.render_model(chunk["event"]),
                            "duration_ms": chunk["duration_ms"],
                            "model": chunk["model"],
                        })

            asyncio.run(drive())
        except BrokenPipeError:
            pass  # the browser navigated away mid-stream
        except Exception as exc:
            try:
                emit({"type": "error", "error": f"{type(exc).__name__}: {exc}"})
            except OSError:
                pass


# Above 1024: ports below that are privileged on Linux and macOS and would
# require running the HUD as root, which is a absurd thing to ask for a
# read-mostly local dashboard.
DEFAULT_PORT = 8420


class PortUnavailable(RuntimeError):
    """Bind failed, with an explanation the user can act on."""


def serve(
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    on_ready: Callable[[], None] | None = None,
) -> None:
    """Bind, then serve. `on_ready` fires only after a successful bind, so a
    caller opening a browser cannot point it at a port that failed to come up."""
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except PermissionError as exc:
        detail = (
            f"port {port} is privileged — ports below 1024 need root."
            if port < 1024
            else f"the OS refused to bind {host}:{port}."
        )
        raise PortUnavailable(f"{detail} Try: nexus hud --port {DEFAULT_PORT}") from exc
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            raise PortUnavailable(
                f"{host}:{port} is already in use — another `nexus hud` may be running. "
                f"Try: nexus hud --port {port + 1}"
            ) from exc
        raise PortUnavailable(f"could not bind {host}:{port}: {exc}") from exc

    if on_ready:
        on_ready()

    try:
        server.serve_forever()
    finally:
        server.server_close()
