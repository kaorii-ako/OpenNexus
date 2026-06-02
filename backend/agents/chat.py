from __future__ import annotations
from typing import AsyncIterator, TYPE_CHECKING

from backend.core.config import NexusConfig
from backend.core.memory import MemoryStore
from backend.agents.rag import retrieve

if TYPE_CHECKING:
    from backend.core.llm.base import LLMBackend


def _select_model(query: str, cfg: NexusConfig) -> str:
    code_model = cfg.llm.model_code or cfg.llm.model
    reasoning_model = cfg.llm.model_reasoning or cfg.llm.model
    if query.startswith("/code"):
        return code_model
    if query.startswith("/think"):
        return reasoning_model
    return cfg.llm.model


def _build_system_prompt(notion_chunks: list[dict], live_ctx: dict, cfg: NexusConfig) -> str:
    parts = [
        f"You are NEXUS — {cfg.user.name}'s personal intelligence layer. "
        f"{cfg.user.timezone} timezone. {cfg.user.role}.",
        "Answer concisely, grounded in the context below.",
    ]
    if notion_chunks:
        parts.append("\n## Notion Context")
        for c in notion_chunks:
            parts.append(f"[{c.get('page_title', '?')} / {c.get('heading', '')}]\n{c['text']}")
    if live_ctx:
        parts.append("\n## Live Context")
        for k, v in live_ctx.items():
            if v:
                parts.append(f"**{k}:** {v}")
    return "\n".join(parts)


async def chat_stream(
    query: str,
    session_id: str,
    cfg: NexusConfig,
    engine: "LLMBackend",
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {}, cfg)
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    async for token in engine.stream_chat(messages, model=model):
        yield token


async def chat_once(
    query: str,
    session_id: str,
    cfg: NexusConfig,
    engine: "LLMBackend",
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {}, cfg)
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    response = await engine.chat(messages, model=model)
    return response, notion_chunks
