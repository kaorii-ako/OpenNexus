from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMBackend(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], model: str | None = None) -> str: ...

    @abstractmethod
    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def health(self) -> bool: ...
