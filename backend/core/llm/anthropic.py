from __future__ import annotations
from typing import AsyncIterator
from backend.core.llm.base import LLMBackend


class AnthropicBackend(LLMBackend):
    def __init__(self, api_key: str, model: str):
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)
        resp = await self._client.messages.create(
            model=m,
            max_tokens=4096,
            system=system,
            messages=filtered,
        )
        return resp.content[0].text

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        m = model or self.model
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)
        async with self._client.messages.stream(
            model=m,
            max_tokens=4096,
            system=system,
            messages=filtered,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Anthropic does not support embeddings. "
            "Switch llm.provider to 'ollama' or 'openai' for embedding support."
        )

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
