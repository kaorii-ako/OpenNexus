from __future__ import annotations
from typing import AsyncIterator
from backend.core.llm.base import LLMBackend


class OpenAIBackend(LLMBackend):
    """OpenAI, or any OpenAI-compatible endpoint (NVIDIA NIM, Groq, vLLM, …)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        embed_model: str = "text-embedding-3-small",
        base_url: str = "",
    ):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key, **({"base_url": base_url} if base_url else {}))
        self.model = model
        self.embed_model = embed_model
        self.base_url = base_url

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        resp = await self._client.chat.completions.create(model=m, messages=messages)
        return resp.choices[0].message.content or ""

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        m = model or self.model
        stream = await self._client.chat.completions.create(model=m, messages=messages, stream=True)
        async for chunk in stream:
            # Not every chunk carries a choice. OpenAI-compatible endpoints
            # (NVIDIA NIM among them) send a trailing usage-only chunk with an
            # empty choices list, which indexing blindly turns into an
            # IndexError right at the end of an otherwise complete answer.
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(model=self.embed_model, input=text)
        return resp.data[0].embedding

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
