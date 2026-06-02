from __future__ import annotations
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.main import create_app
from backend.core.config import (
    NexusConfig, UserConfig, LLMConfig, OllamaConfig, MemoryConfig, ServerConfig,
    SchedulerConfig, DigestConfig, ConnectorsConfig, WeatherConfig,
)


@pytest.fixture
def cfg(tmp_path):
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


@pytest.fixture
def client(cfg):
    app = create_app(cfg)
    return TestClient(app)


def test_create_app_returns_fastapi(cfg):
    app = create_app(cfg)
    assert isinstance(app, FastAPI)


def test_status_endpoint(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    assert "connectors" in r.json()


def test_digest_get(client):
    r = client.get("/api/digest")
    assert r.status_code == 200
    assert "content" in r.json()


def test_digest_run(client):
    r = client.post("/api/digest/run")
    assert r.status_code == 200
    body = r.json()
    assert "content" in body
    assert "generated_at" in body


def test_memory_index(client):
    r = client.post("/api/memory/index", json={"path": "/tmp/test"})
    assert r.status_code == 200
    assert r.json() == {"status": "queued", "path": "/tmp/test"}


def test_sync(client):
    r = client.post("/api/sync")
    assert r.status_code == 200
    assert r.json() == {"status": "syncing"}
