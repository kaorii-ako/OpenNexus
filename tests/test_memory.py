import pytest
from pathlib import Path
from backend.core.memory import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(chroma_dir=tmp_path / "chroma")


def test_empty_search_returns_empty(store):
    result = store.search_notion("anything", embedding=[0.1] * 768, top_k=5)
    assert result == []


def test_upsert_and_search_notion(store):
    store.upsert_notion_chunk(
        chunk_id="page1::intro",
        text="NEXUS is a personal intelligence layer",
        embedding=[0.1] * 768,
        metadata={"page_id": "page1", "page_title": "About NEXUS", "heading": "Intro"},
    )
    results = store.search_notion("personal intelligence", embedding=[0.1] * 768, top_k=1)
    assert len(results) == 1
    assert results[0]["page_title"] == "About NEXUS"
    assert "score" in results[0]


def test_upsert_conversation(store):
    store.upsert_turn(
        turn_id="s1::1",
        text="user: hello\nassistant: hi",
        embedding=[0.2] * 768,
        metadata={"session_id": "s1", "timestamp": "2026-06-01T08:00:00"},
    )
    results = store.search_history("hello", embedding=[0.2] * 768, top_k=1)
    assert len(results) == 1
    assert results[0]["session_id"] == "s1"


def test_upsert_file_chunk(store):
    store.upsert_file_chunk(
        chunk_id="file1::0",
        text="def hello(): return 'world'",
        embedding=[0.3] * 768,
        metadata={"file_path": "/src/main.py", "file_type": "python"},
    )
    results = store.search_files(embedding=[0.3] * 768, top_k=1)
    assert len(results) == 1
    assert results[0]["file_type"] == "python"


def test_upsert_deduplicates(store):
    store.upsert_notion_chunk("p1::h1", "first version", [0.1] * 768, {"page_title": "v1"})
    store.upsert_notion_chunk("p1::h1", "updated version", [0.1] * 768, {"page_title": "v2"})
    results = store.search_notion("", embedding=[0.1] * 768, top_k=5)
    assert len(results) == 1
    assert results[0]["page_title"] == "v2"
