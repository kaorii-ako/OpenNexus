from __future__ import annotations
import pytest
import respx
import httpx
from pathlib import Path

from backend.core.config import (
    NexusConfig, UserConfig, LLMConfig, OllamaConfig, MemoryConfig, ServerConfig,
    SchedulerConfig, DigestConfig, ConnectorsConfig, WeatherConfig,
)
from backend.connectors.github import GitHubConnector
from backend.connectors.discord import DiscordConnector
from backend.connectors.weather import WeatherConnector
from backend.connectors.rss import RssConnector
from backend.connectors.stubs.telegram import TelegramConnector
from backend.connectors.stubs.spotify import SpotifyConnector


def make_cfg(tmp_path: Path) -> NexusConfig:
    return NexusConfig(
        data_dir=tmp_path,
        notion_cache_dir=tmp_path / "notion_cache",
        timezone="Asia/Bangkok",
        user=UserConfig(name="Test", timezone="Asia/Bangkok", role="tester"),
        llm=LLMConfig(provider="ollama", model="llama3.2", api_key="", base_url="http://localhost:11434", embed_model="nomic-embed-text"),
        ollama=OllamaConfig(
            "http://localhost:11434", "qwen2.5:7b", "qwen2.5-coder:7b",
            "deepseek-r1:7b", "nomic-embed-text",
        ),
        memory=MemoryConfig(
            str(tmp_path / "chroma"), "notion_chunks",
            "conversation_history", "file_index",
        ),
        server=ServerConfig("127.0.0.1", 8000, "./frontend/dist"),
        scheduler=SchedulerConfig("0 8 * * *", "*/15 * * * *", "0 2 * * *"),
        digest=DigestConfig(),
        connectors=ConnectorsConfig(
            weather=WeatherConfig(13.7563, 100.5018, "Bangkok"),
            rss_sources=[],
        ),
    )


# 1. GitHubConnector health — no token
@pytest.mark.asyncio
async def test_github_health_no_token(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = GitHubConnector(cfg)
    result = await connector.health()
    assert result.name == "github"
    assert result.healthy is False
    assert result.error == "No token"


# 2. DiscordConnector health — no token
@pytest.mark.asyncio
async def test_discord_health_no_token(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = DiscordConnector(cfg)
    result = await connector.health()
    assert result.name == "discord"
    assert result.healthy is False
    assert result.error == "No token"


# 3. DiscordConnector.guild_summaries — no token returns []
@pytest.mark.asyncio
async def test_discord_guild_summaries_no_token(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = DiscordConnector(cfg)
    result = await connector.guild_summaries()
    assert result == []


# 4. RssConnector health — empty sources returns False
@pytest.mark.asyncio
async def test_rss_health_empty_sources(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = RssConnector(cfg)
    result = await connector.health()
    assert result.name == "rss"
    assert result.healthy is False


# 5. RssConnector.fetch — empty sources returns []
def test_rss_fetch_empty_sources(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = RssConnector(cfg)
    assert connector.fetch() == []


# 6. WeatherConnector.current — mocked response
@pytest.mark.asyncio
@respx.mock
async def test_weather_current_mocked(tmp_path):
    cfg = make_cfg(tmp_path)
    connector = WeatherConnector(cfg)

    respx.get(url__startswith="https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200,
            json={"current_weather": {"temperature": 32.1, "windspeed": 10.5, "weathercode": 3}},
        )
    )

    result = await connector.current()
    assert result == {
        "location": "Bangkok",
        "temp_c": 32.1,
        "wind_kmh": 10.5,
        "description": "Overcast",
    }


# 7. TelegramConnector.send raises NotImplementedError
@pytest.mark.asyncio
async def test_telegram_stub_raises():
    t = TelegramConnector()
    with pytest.raises(NotImplementedError):
        await t.send("hello")


# 8. SpotifyConnector.now_playing raises NotImplementedError
@pytest.mark.asyncio
async def test_spotify_stub_raises():
    s = SpotifyConnector()
    with pytest.raises(NotImplementedError):
        await s.now_playing()
