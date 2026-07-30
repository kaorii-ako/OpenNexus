"""The conversational layer: route, then actually answer.

`Router` decides which skills to load. This module is what makes that decision
matter — the loaded skill content becomes the model's context, so an answer
about FlareBisect is grounded in the real pointer file rather than the model's
guess about a project it has never seen.

Two events are written per turn: the routing decision, and a record that an
answer was produced (model, duration, whether skill context was actually
injected). Both go to the same append-only log as everything else.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from backend.orchestrator.events import ANSWER, EventLog, new_run_id
from backend.orchestrator.router import Router, RoutingDecision

SYSTEM_BASE = """\
You are NEXUS, {name}'s command centre. Direct, concrete, no filler.

The context below was selected by the skill router for this specific query. It
describes real projects on this machine, with real paths. Ground your answer in
it. When it names a file or directory, use that exact path.

If the context does not cover what was asked, say so plainly rather than
inventing details about a project you cannot see. Never fabricate a file path,
a command, or a result.
"""

NO_CONTEXT_NOTE = """\
No skill context matched this query, so answer from general knowledge and say
that you are doing so if the question looked like it was about a specific
project.
"""


def _explain(exc: Exception, cfg) -> str:
    """Turn a backend exception into something the user can act on."""
    name = type(exc).__name__
    text = str(exc)
    provider = getattr(getattr(cfg, "llm", None), "provider", "") or "?"
    base_url = getattr(getattr(cfg, "llm", None), "base_url", "") or "http://localhost:11434"

    if "Connect" in name or "Connection" in name:
        if provider in ("ollama", "auto"):
            return (
                f"cannot reach Ollama at {base_url}. Start it with `ollama serve`, "
                "or set provider to 'openai' / 'anthropic' / 'auto' in nexus.toml."
            )
        return f"cannot reach the {provider} API: {text}"

    if "Authentication" in name or "401" in text or "invalid_api_key" in text:
        return f"{provider} rejected the API key. Check the key in nexus.toml or your environment."

    if "NotFound" in name or "404" in text or "model" in text.lower() and "not found" in text.lower():
        model = getattr(getattr(cfg, "llm", None), "model", "") or "(unset)"
        return f"{provider} does not have model '{model}'. Check the model name in nexus.toml."

    if "RateLimit" in name or "429" in text:
        return f"{provider} rate limit hit. Wait and retry."

    return f"{name}: {text}"


@dataclass
class Turn:
    """Everything that happened in one exchange."""

    query: str
    decision: RoutingDecision | None = None
    answer: str = ""
    model: str = ""
    duration_ms: int = 0
    context_chars: int = 0
    error: str = ""
    events: list[Any] = field(default_factory=list)


class NexusAgent:
    """Routes a query, injects the loaded skills, streams the answer."""

    def __init__(self, cfg, engine, log: EventLog | None = None, router: Router | None = None):
        self.cfg = cfg
        self.engine = engine
        self.log = log or EventLog()
        self.router = router or Router()
        self.run_id = new_run_id()
        self.history: list[dict[str, str]] = []

    # --- prompt ------------------------------------------------------------

    def _system_prompt(self, context: str) -> str:
        name = getattr(getattr(self.cfg, "user", None), "name", "") or "the user"
        base = SYSTEM_BASE.format(name=name)
        if not context:
            return base + "\n" + NO_CONTEXT_NOTE
        return f"{base}\n## Loaded skill context\n\n{context}"

    def _select_model(self, query: str) -> str | None:
        llm = getattr(self.cfg, "llm", None)
        if llm is None:
            return None
        if query.startswith("/code") and llm.model_code:
            return llm.model_code
        if query.startswith("/think") and llm.model_reasoning:
            return llm.model_reasoning
        return llm.model or None

    # --- turn --------------------------------------------------------------

    def route(self, query: str) -> tuple[RoutingDecision, Any, str]:
        """Route and log, returning the decision, its event, and the context."""
        decision = self.router.route(query)
        event = self.log.append("route", decision.to_payload(), run_id=self.run_id)
        decision.event_id = event.id
        return decision, event, self.router.context_for(decision)

    async def answer_stream(self, query: str) -> AsyncIterator[dict[str, Any]]:
        """Yield the turn as it happens.

        Emits {"type": "route"} once, then {"type": "token"} repeatedly, then a
        final {"type": "done"} or {"type": "error"}. The HUD and the CLI both
        consume this, so neither can drift from the other.
        """
        decision, route_event, context = self.route(query)
        yield {"type": "route", "event": route_event, "decision": decision}

        messages = [{"role": "system", "content": self._system_prompt(context)}]
        messages.extend(self.history[-10:])
        messages.append({"role": "user", "content": query})

        model = self._select_model(query)
        started = time.monotonic()
        chunks: list[str] = []

        try:
            async for token in self.engine.stream_chat(messages, model=model):
                chunks.append(token)
                yield {"type": "token", "text": token}
        except Exception as exc:
            # A model failure is reported, never silently swallowed, and never
            # replaced with invented text.
            yield {"type": "error", "error": _explain(exc, self.cfg)}
            return

        answer = "".join(chunks)
        duration_ms = int((time.monotonic() - started) * 1000)

        self.history.append({"role": "user", "content": query})
        self.history.append({"role": "assistant", "content": answer})

        answer_event = self.log.append(
            ANSWER,
            {
                "query": query,
                "route_event": route_event.id,
                "branches": decision.loaded_branches,
                "model": model or "",
                "duration_ms": duration_ms,
                "answer_chars": len(answer),
                "context_chars": len(context),
                "grounded": bool(context),
            },
            run_id=self.run_id,
        )

        yield {
            "type": "done",
            "answer": answer,
            "event": answer_event,
            "duration_ms": duration_ms,
            "model": model or "",
        }

    async def ask(self, query: str) -> Turn:
        """Non-streaming convenience wrapper over `answer_stream`."""
        turn = Turn(query=query)
        async for chunk in self.answer_stream(query):
            kind = chunk["type"]
            if kind == "route":
                turn.decision = chunk["decision"]
                turn.events.append(chunk["event"])
            elif kind == "error":
                turn.error = chunk["error"]
            elif kind == "done":
                turn.answer = chunk["answer"]
                turn.model = chunk["model"]
                turn.duration_ms = chunk["duration_ms"]
                turn.events.append(chunk["event"])
        return turn
