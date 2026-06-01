import os
import pytest
from pathlib import Path
from backend.core.config import load_config, NexusConfig

def test_load_config_defaults(tmp_path):
    cfg_path = tmp_path / "nexus.toml"
    cfg_path.write_text("""
[nexus]
data_dir = "/tmp/nexus_test"
timezone = "Asia/Bangkok"
[ollama]
base_url = "http://localhost:11434"
model_general = "qwen2.5:7b"
model_code = "qwen2.5-coder:7b"
model_reasoning = "deepseek-r1:7b"
model_embed = "nomic-embed-text"
stream = true
[memory]
chroma_dir = "/tmp/nexus_test/chroma"
notion_collection = "notion_chunks"
conversation_collection = "conversation_history"
file_collection = "file_index"
top_k = 5
chunk_strategy = "heading"
[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"
open_browser_on_start = false
[scheduler]
digest_cron = "0 8 * * *"
notion_sync_cron = "*/15 * * * *"
reindex_cron = "0 2 * * *"
[digest]
write_to_notion = false
print_to_terminal = true
[connectors.weather]
latitude = 13.7563
longitude = 100.5018
location_name = "Bangkok"
[connectors.rss]
sources = []
""")
    cfg = load_config(cfg_path)
    assert isinstance(cfg, NexusConfig)
    assert cfg.ollama.model_general == "qwen2.5:7b"
    assert cfg.server.port == 8000
    assert cfg.memory.top_k == 5


def test_load_config_path_expansion(tmp_path):
    cfg_path = tmp_path / "nexus.toml"
    cfg_path.write_text("""
[nexus]
data_dir = "~/.nexus"
timezone = "Asia/Bangkok"
[ollama]
base_url = "http://localhost:11434"
model_general = "qwen2.5:7b"
model_code = "qwen2.5-coder:7b"
model_reasoning = "deepseek-r1:7b"
model_embed = "nomic-embed-text"
stream = true
[memory]
chroma_dir = "~/.nexus/chroma"
notion_collection = "notion_chunks"
conversation_collection = "conversation_history"
file_collection = "file_index"
top_k = 5
chunk_strategy = "heading"
[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"
open_browser_on_start = false
[scheduler]
digest_cron = "0 8 * * *"
notion_sync_cron = "*/15 * * * *"
reindex_cron = "0 2 * * *"
[digest]
write_to_notion = false
print_to_terminal = true
[connectors.weather]
latitude = 13.7563
longitude = 100.5018
location_name = "Bangkok"
[connectors.rss]
sources = []
""")
    cfg = load_config(cfg_path)
    assert not str(cfg.data_dir).startswith("~")
    assert not str(cfg.notion_cache_dir).startswith("~")
    assert cfg.notion_cache_dir == cfg.data_dir / "notion_cache"


def test_load_config_missing_section_raises(tmp_path):
    cfg_path = tmp_path / "nexus.toml"
    cfg_path.write_text("[nexus]\ndata_dir = '/tmp'\ntimezone = 'UTC'\n")
    with pytest.raises(ValueError, match="Missing required section"):
        load_config(cfg_path)


def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError, match="nexus.toml"):
        load_config("/nonexistent/path/nexus.toml")


def test_load_config_connector_defaults(tmp_path):
    cfg_path = tmp_path / "nexus.toml"
    cfg_path.write_text("""
[nexus]
data_dir = "/tmp/nexus_test"
timezone = "Asia/Bangkok"
[ollama]
base_url = "http://localhost:11434"
model_general = "qwen2.5:7b"
model_code = "qwen2.5-coder:7b"
model_reasoning = "deepseek-r1:7b"
model_embed = "nomic-embed-text"
stream = true
[memory]
chroma_dir = "/tmp/nexus_test/chroma"
notion_collection = "notion_chunks"
conversation_collection = "conversation_history"
file_collection = "file_index"
top_k = 5
chunk_strategy = "heading"
[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"
open_browser_on_start = false
[scheduler]
digest_cron = "0 8 * * *"
notion_sync_cron = "*/15 * * * *"
reindex_cron = "0 2 * * *"
[digest]
write_to_notion = false
print_to_terminal = true
[connectors.weather]
latitude = 13.7563
longitude = 100.5018
location_name = "Bangkok"
""")
    cfg = load_config(cfg_path)
    assert cfg.connectors.rss_sources == []
    assert cfg.connectors.notion_enabled is True
    assert cfg.connectors.gmail_enabled is True
