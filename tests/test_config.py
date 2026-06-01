import os
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
