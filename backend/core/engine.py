from __future__ import annotations
import json
from typing import AsyncIterator
import httpx


class OllamaEngine:
    def __init__(self, base_url: str, model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model
        self._code_model = model
        self._reasoning_model = model

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
            )
            r.raise_for_status()
            return r.json()["embedding"]

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> str:
        m = model or self.model
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": m, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        m = model or self.model
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": m, "messages": messages, "stream": True},
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if token := chunk.get("message", {}).get("content"):
                        yield token
                    if chunk.get("done"):
                        return

    def route_model(self, query: str) -> str:
        if query.startswith("/code"):
            return self._code_model
        if query.startswith("/think"):
            return self._reasoning_model
        return self.model

    def set_models(self, code: str, reasoning: str) -> None:
        self._code_model = code
        self._reasoning_model = reasoning
