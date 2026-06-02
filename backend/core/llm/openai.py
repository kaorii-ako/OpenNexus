from __future__ import annotations
from typing import AsyncIterator
from backend.core.llm.base import LLMBackend


class OpenAIBackend(LLMBackend):
    def __init__(self, api_key: str, model: str, embed_model: str = "text-embedding-3-small"):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.embed_model = embed_model

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        resp = await self._client.chat.completions.create(model=m, messages=messages)
        return resp.choices[0].message.content or ""

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        m = model or self.model
        stream = await self._client.chat.completions.create(model=m, messages=messages, stream=True)
        async for chunk in stream:
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
