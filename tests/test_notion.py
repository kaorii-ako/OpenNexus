import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from backend.connectors.base import HealthResult
from backend.connectors.notion import NotionConnector
from backend.connectors.notion_sync import NotionSync


@pytest.fixture
def cfg(tmp_path):
    from backend.core.config import (
        NexusConfig, UserConfig, LLMConfig, OllamaConfig, MemoryConfig, ServerConfig,
        SchedulerConfig, DigestConfig, ConnectorsConfig, WeatherConfig
    )
    return NexusConfig(
        data_dir=tmp_path,
        notion_cache_dir=tmp_path / "notion_cache",
        timezone="Asia/Bangkok",
        user=UserConfig(name="Test", timezone="Asia/Bangkok", role="tester"),
        llm=LLMConfig(provider="ollama", model="llama3.2", api_key="", base_url="http://localhost:11434", embed_model="nomic-embed-text"),
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


def test_no_token_health_returns_unhealthy(cfg):
    connector = NotionConnector(cfg)
    import asyncio
    result = asyncio.run(connector.health())
    assert result.healthy is False
    assert "token" in result.error.lower()


def test_no_token_get_all_pages_returns_empty(cfg):
    connector = NotionConnector(cfg)
    import asyncio
    pages = asyncio.run(connector.get_all_pages())
    assert pages == []


def test_blocks_to_md_headings(cfg):
    connector = NotionConnector(cfg)
    blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Title"}]}},
        {"type": "heading_2", "heading_2": {"rich_text": [{"plain_text": "Subtitle"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Body text"}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "Item"}]}},
    ]
    md = connector._blocks_to_md(blocks)
    assert "# Title" in md
    assert "## Subtitle" in md
    assert "Body text" in md
    assert "- Item" in md


def test_blocks_to_md_todo(cfg):
    connector = NotionConnector(cfg)
    blocks = [
        {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Task"}], "checked": True}},
        {"type": "to_do", "to_do": {"rich_text": [{"plain_text": "Undone"}], "checked": False}},
    ]
    md = connector._blocks_to_md(blocks)
    assert "- [x] Task" in md
    assert "- [ ] Undone" in md


def test_notion_sync_extract_title(cfg, tmp_path):
    syncer = NotionSync(cfg)
    page = {
        "id": "abc123",
        "properties": {
            "title": {"title": [{"plain_text": "My Page"}]}
        }
    }
    assert syncer._extract_title(page) == "My Page"


def test_notion_sync_extract_title_fallback(cfg, tmp_path):
    syncer = NotionSync(cfg)
    page = {"id": "abc123", "properties": {}}
    assert syncer._extract_title(page) == "Untitled"
