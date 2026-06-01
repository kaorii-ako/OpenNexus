from __future__ import annotations
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore


async def retrieve(
    query: str,
    engine: OllamaEngine,
    store: MemoryStore,
    top_k: int = 5,
) -> list[dict]:
    embedding = await engine.embed(query)
    notion_hits = store.search_notion(query, embedding, top_k=top_k)
    return notion_hits
