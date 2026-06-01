from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class HealthResult:
    name: str
    healthy: bool
    error: str | None = None


class ConnectorBase(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def health(self) -> HealthResult: ...
