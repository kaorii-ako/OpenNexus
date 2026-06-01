from __future__ import annotations
import asyncio
from datetime import datetime
from typing import AsyncIterator

from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from backend.agents.rag import retrieve


def _select_model(query: str, cfg: NexusConfig) -> str:
    if query.startswith("/code"):
        return cfg.ollama.model_code
    if query.startswith("/think"):
        return cfg.ollama.model_reasoning
    return cfg.ollama.model_general


def _build_system_prompt(notion_chunks: list[dict], live_ctx: dict) -> str:
    parts = [
        "You are NEXUS — Tawin's personal intelligence layer. Bangkok timezone. Developer + student.",
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
    engine: OllamaEngine,
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {})
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
    engine: OllamaEngine,
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {})
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    response = await engine.chat(messages, model=model)
    return response, notion_chunks
