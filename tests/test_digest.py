from __future__ import annotations
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

from backend.core.config import (
    NexusConfig, UserConfig, LLMConfig, OllamaConfig, MemoryConfig, ServerConfig,
    SchedulerConfig, DigestConfig, ConnectorsConfig, WeatherConfig,
)
from backend.core.engine import OllamaEngine


def make_cfg(tmp_path: Path) -> NexusConfig:
    return NexusConfig(
        data_dir=tmp_path,
        notion_cache_dir=tmp_path / "notion_cache",
        timezone="Asia/Bangkok",
        user=UserConfig(name="Test", timezone="Asia/Bangkok", role="tester"),
        llm=LLMConfig(provider="ollama", model="llama3.2", api_key="", base_url="http://localhost:11434", embed_model="nomic-embed-text"),
        ollama=OllamaConfig("http://localhost:11434", "qwen2.5:7b", "qwen2.5-coder:7b", "deepseek-r1:7b", "nomic-embed-text"),
        memory=MemoryConfig(str(tmp_path / "chroma"), "notion_chunks", "conversation_history", "file_index"),
        server=ServerConfig("127.0.0.1", 8000, "./frontend/dist", False),
        scheduler=SchedulerConfig("0 8 * * *", "*/15 * * * *", "0 2 * * *"),
        digest=DigestConfig(write_to_notion=False, print_to_terminal=False),
        connectors=ConnectorsConfig(weather=WeatherConfig(13.7563, 100.5018, "Bangkok"), rss_sources=[]),
    )


def make_engine() -> OllamaEngine:
    engine = OllamaEngine("http://localhost:11434", "qwen2.5:7b", "nomic-embed-text")
    engine.set_models("qwen2.5-coder:7b", "deepseek-r1:7b")
    return engine


# ---------------------------------------------------------------------------
# Test 1: all connectors unavailable
# ---------------------------------------------------------------------------

def test_digest_run_no_connectors(tmp_path):
    cfg = make_cfg(tmp_path)
    engine = make_engine()

    with patch("backend.agents.digest.WeatherConnector") as MockWeather, \
         patch("backend.agents.digest.CalendarConnector") as MockCal, \
         patch("backend.agents.digest.GmailConnector") as MockGmail, \
         patch("backend.agents.digest.GitHubConnector") as MockGH, \
         patch("backend.agents.digest.ClassroomConnector") as MockClass, \
         patch("backend.agents.digest.RssConnector") as MockRss:

        MockWeather.return_value.current = AsyncMock(side_effect=Exception("no creds"))
        MockCal.return_value.today_events.side_effect = Exception("no creds")
        MockGmail.return_value.unread_count.side_effect = Exception("no creds")
        MockGH.return_value.open_prs.side_effect = Exception("no creds")
        MockClass.return_value.due_soon.side_effect = Exception("no creds")
        MockRss.return_value.fetch.side_effect = Exception("no creds")

        from backend.agents.digest import DigestAgent
        agent = DigestAgent(cfg, engine)
        result = asyncio.run(agent.run())

    assert isinstance(result, str)
    assert "Morning Briefing" in result
    assert "(unavailable)" in result


# ---------------------------------------------------------------------------
# Test 2: weather succeeds, others fail
# ---------------------------------------------------------------------------

def test_digest_includes_weather(tmp_path):
    cfg = make_cfg(tmp_path)
    engine = make_engine()

    weather_data = {
        "location": "Bangkok",
        "temp_c": 32.0,
        "wind_kmh": 5.0,
        "description": "Clear",
    }

    with patch("backend.agents.digest.WeatherConnector") as MockWeather, \
         patch("backend.agents.digest.CalendarConnector") as MockCal, \
         patch("backend.agents.digest.GmailConnector") as MockGmail, \
         patch("backend.agents.digest.GitHubConnector") as MockGH, \
         patch("backend.agents.digest.ClassroomConnector") as MockClass, \
         patch("backend.agents.digest.RssConnector") as MockRss:

        MockWeather.return_value.current = AsyncMock(return_value=weather_data)
        MockCal.return_value.today_events.side_effect = Exception("no creds")
        MockGmail.return_value.unread_count.side_effect = Exception("no creds")
        MockGH.return_value.open_prs.side_effect = Exception("no creds")
        MockClass.return_value.due_soon.side_effect = Exception("no creds")
        MockRss.return_value.fetch.side_effect = Exception("no creds")

        from backend.agents.digest import DigestAgent
        agent = DigestAgent(cfg, engine)
        result = asyncio.run(agent.run())

    assert "Bangkok" in result
    assert "32.0" in result


# ---------------------------------------------------------------------------
# Test 3: scheduler creates correct jobs
# ---------------------------------------------------------------------------

def test_scheduler_creates_jobs(tmp_path):
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from backend.core.memory import MemoryStore
    from backend.scheduler.jobs import create_scheduler

    cfg = make_cfg(tmp_path)
    engine = make_engine()
    store = MemoryStore(tmp_path / "chroma")

    scheduler = create_scheduler(cfg, engine, store)

    assert isinstance(scheduler, AsyncIOScheduler)
    job_ids = {job.id for job in scheduler.get_jobs()}
    assert "digest" in job_ids
    assert "notion_sync" in job_ids
