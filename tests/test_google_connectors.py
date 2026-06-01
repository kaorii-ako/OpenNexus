# tests/test_google_connectors.py
import pytest
import asyncio
from pathlib import Path
from backend.connectors.gmail import GmailConnector, _load_creds
from backend.connectors.calendar import CalendarConnector
from backend.connectors.classroom import ClassroomConnector


@pytest.fixture
def cfg(tmp_path):
    from backend.core.config import (
        NexusConfig, OllamaConfig, MemoryConfig, ServerConfig,
        SchedulerConfig, DigestConfig, ConnectorsConfig, WeatherConfig
    )
    return NexusConfig(
        data_dir=tmp_path,
        notion_cache_dir=tmp_path / "notion_cache",
        timezone="Asia/Bangkok",
        ollama=OllamaConfig(
            base_url="http://localhost:11434",
            model_general="qwen2.5:7b",
            model_code="qwen2.5-coder:7b",
            model_reasoning="deepseek-r1:7b",
            model_embed="nomic-embed-text",
        ),
        memory=MemoryConfig(
            chroma_dir=str(tmp_path / "chroma"),
            notion_collection="notion_chunks",
            conversation_collection="conversation_history",
            file_collection="file_index",
        ),
        server=ServerConfig(
            host="127.0.0.1", port=8000,
            frontend_dist="./frontend/dist",
            open_browser_on_start=False,
        ),
        scheduler=SchedulerConfig(
            digest_cron="0 8 * * *",
            notion_sync_cron="*/15 * * * *",
            reindex_cron="0 2 * * *",
        ),
        digest=DigestConfig(write_to_notion=False, print_to_terminal=False),
        connectors=ConnectorsConfig(
            weather=WeatherConfig(latitude=13.75, longitude=100.50, location_name="Bangkok"),
        ),
    )


def test_load_creds_no_token_file(tmp_path):
    assert _load_creds(tmp_path) is None


def test_gmail_no_creds_health(cfg):
    conn = GmailConnector(cfg)
    result = asyncio.run(conn.health())
    assert result.healthy is False
    assert "credentials" in result.error.lower()


def test_gmail_no_creds_unread_count(cfg):
    conn = GmailConnector(cfg)
    result = conn.unread_count()
    assert result == {"count": 0, "top_sender": None}


def test_calendar_no_creds_health(cfg):
    conn = CalendarConnector(cfg)
    result = asyncio.run(conn.health())
    assert result.healthy is False


def test_calendar_no_creds_today_events(cfg):
    conn = CalendarConnector(cfg)
    assert conn.today_events() == []


def test_classroom_no_creds_health(cfg):
    conn = ClassroomConnector(cfg)
    result = asyncio.run(conn.health())
    assert result.healthy is False


def test_classroom_no_creds_due_soon(cfg):
    conn = ClassroomConnector(cfg)
    assert conn.due_soon() == []


def test_classroom_no_creds_announcements(cfg):
    conn = ClassroomConnector(cfg)
    assert conn.announcements() == []
