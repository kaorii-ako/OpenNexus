from __future__ import annotations
import json
from pathlib import Path
import httpx
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

DISCORD_API = "https://discord.com/api/v10"


class DiscordConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        token_path = Path(cfg.data_dir) / "discord.json"
        self._token = json.loads(token_path.read_text())["token"] if token_path.exists() else None

    def _headers(self) -> dict:
        return {"Authorization": self._token or ""}

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        if not self._token:
            return HealthResult("discord", False, "No token")
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{DISCORD_API}/users/@me", headers=self._headers())
                r.raise_for_status()
            return HealthResult("discord", True)
        except Exception as e:
            return HealthResult("discord", False, str(e))

    async def guild_summaries(self) -> list[dict]:
        if not self._token:
            return []
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{DISCORD_API}/users/@me/guilds", headers=self._headers())
            r.raise_for_status()
            guilds = r.json()
        return [{"name": g["name"], "id": g["id"]} for g in guilds[:5]]
