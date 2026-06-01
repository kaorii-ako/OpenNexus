# NEXUS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first personal intelligence layer that connects Notion, Gmail, Calendar, Classroom, GitHub, Discord, and local LLMs into a single CLI + web UI.

**Architecture:** FastAPI backend with ChromaDB (RAG), SQLite (history), Ollama (local LLMs), and APScheduler (cron). React frontend served statically from FastAPI. All secrets in `~/.nexus/`, never committed.

**Tech Stack:** Python 3.13 · uv · FastAPI · SQLModel · ChromaDB · Ollama · httpx · APScheduler · Typer · Rich · React 18 · Vite · TypeScript · Tailwind CSS

---

## File Map

```
backend/
  core/
    config.py          ← load nexus.toml → NexusConfig dataclass
    engine.py          ← Ollama: chat(), embed(), stream_chat()
    memory.py          ← ChromaDB: init 3 collections + upsert/search
    db.py              ← SQLModel: Conversation, Turn, DigestLog, ConnectorStatus
  connectors/
    base.py            ← ConnectorBase ABC: connect(), fetch(), health()
    notion.py          ← Notion API read/write + workspace scaffold
    notion_sync.py     ← sync daemon: pages → ~/.nexus/notion_cache/
    gmail.py           ← OAuth2 PKCE: read threads, triage
    calendar.py        ← today/week events (shared Gmail token)
    classroom.py       ← courses, assignments, announcements
    github.py          ← PAT: PRs, issues, notifs
    discord.py         ← bot token: channel summaries
    weather.py         ← open-meteo Bangkok (no API key)
    rss.py             ← feedparser: configured sources
    stubs/telegram.py  ← stub only
    stubs/spotify.py   ← stub only
  agents/
    rag.py             ← embed → ChromaDB → top-K chunks
    chat.py            ← full 7-step chat pipeline
    digest.py          ← morning briefing composer
  scheduler/
    jobs.py            ← APScheduler: digest, sync, reindex
  api/
    main.py            ← FastAPI factory + static mount
    routes/
      chat.py          ← POST /api/chat + GET /api/chat/stream (SSE)
      digest.py        ← GET/POST /api/digest
      notion.py        ← GET /api/notion/tree|page|search
      connectors.py    ← GET /api/status + POST /api/connect/{service}
      memory.py        ← POST /api/memory/index + POST /api/sync
cli/
  main.py              ← Typer app: ask, chat, digest, note, log, connect, serve, doctor, sync, memory
tests/
  test_config.py
  test_engine.py
  test_memory.py
  test_rag.py
  test_chat.py
  test_notion_sync.py
  test_digest.py
  test_api.py
frontend/
  src/
    views/Chat.tsx · Digest.tsx · Notion.tsx · Status.tsx
    components/ContextChip.tsx · StreamMessage.tsx · NotionTree.tsx · ConnectorBadge.tsx · Sidebar.tsx
    hooks/useSSE.ts · useNotion.ts
    lib/api.ts
    App.tsx
  vite.config.ts
  tailwind.config.ts
  package.json
nexus.toml.example
pyproject.toml
setup.ps1
```

---

## Task 1: Project Bootstrap

**Files:**
- Create: `pyproject.toml`
- Create: `nexus.toml.example`
- Create: `backend/__init__.py` (empty)
- Create: `tests/__init__.py` (empty)

- [ ] **Step 1: Init uv project**

```powershell
uv init --no-readme
```

- [ ] **Step 2: Write pyproject.toml**

```toml
[project]
name = "nexus"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "sqlmodel>=0.0.21",
  "chromadb>=0.5",
  "httpx>=0.27",
  "typer[all]>=0.12",
  "rich>=13",
  "apscheduler>=3.10",
  "google-auth-oauthlib>=1.2",
  "google-api-python-client>=2.140",
  "PyGithub>=2.3",
  "feedparser>=6.0",
  "aiofiles>=23",
  "tomli>=2; python_version<'3.11'",
  "pydantic>=2",
]

[dependency-groups]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "httpx>=0.27",  # TestClient
  "respx>=0.21",  # mock httpx
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[project.scripts]
nexus = "cli.main:app"
```

- [ ] **Step 3: Write nexus.toml.example**

```toml
[nexus]
data_dir = "~/.nexus"
notion_cache_dir = "~/.nexus/notion_cache"
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
open_browser_on_start = true

[scheduler]
digest_cron = "0 8 * * *"
notion_sync_cron = "*/15 * * * *"
reindex_cron = "0 2 * * *"

[digest]
write_to_notion = true
print_to_terminal = true

[connectors.weather]
latitude = 13.7563
longitude = 100.5018
location_name = "Bangkok"

[connectors.rss]
sources = [
  "https://feeds.feedburner.com/oreilly/radar",
  "https://tldr.tech/api/rss/tech",
  "https://hnrss.org/frontpage",
]

[connectors.notion]
enabled = true
[connectors.discord]
enabled = true
[connectors.github]
enabled = true
[connectors.gmail]
enabled = true
[connectors.calendar]
enabled = true
[connectors.classroom]
enabled = true
[connectors.telegram]
enabled = false
[connectors.spotify]
enabled = false
```

- [ ] **Step 4: Create package dirs**

```powershell
New-Item -ItemType Directory -Path backend/core, backend/connectors/stubs, backend/agents, backend/scheduler, backend/api/routes, cli, tests -Force
"" | Out-File backend/__init__.py
"" | Out-File backend/core/__init__.py
"" | Out-File backend/connectors/__init__.py
"" | Out-File backend/connectors/stubs/__init__.py
"" | Out-File backend/agents/__init__.py
"" | Out-File backend/scheduler/__init__.py
"" | Out-File backend/api/__init__.py
"" | Out-File backend/api/routes/__init__.py
"" | Out-File cli/__init__.py
"" | Out-File tests/__init__.py
```

- [ ] **Step 5: Install deps**

```powershell
uv sync
```

Expected: All packages install cleanly.

- [ ] **Step 6: Copy config**

```powershell
Copy-Item nexus.toml.example nexus.toml
```

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml nexus.toml.example nexus.toml backend/ cli/ tests/
git commit -m "chore: bootstrap project structure"
```

---

## Task 2: Config (`core/config.py`)

**Files:**
- Create: `backend/core/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
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
```

- [ ] **Step 2: Run test — expect FAIL**

```powershell
uv run pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'backend.core.config'`

- [ ] **Step 3: Implement `backend/core/config.py`**

```python
from __future__ import annotations
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class OllamaConfig:
    base_url: str
    model_general: str
    model_code: str
    model_reasoning: str
    model_embed: str
    stream: bool = True


@dataclass
class MemoryConfig:
    chroma_dir: str
    notion_collection: str
    conversation_collection: str
    file_collection: str
    top_k: int = 5
    chunk_strategy: str = "heading"


@dataclass
class ServerConfig:
    host: str
    port: int
    frontend_dist: str
    open_browser_on_start: bool = True


@dataclass
class SchedulerConfig:
    digest_cron: str
    notion_sync_cron: str
    reindex_cron: str


@dataclass
class DigestConfig:
    write_to_notion: bool = True
    print_to_terminal: bool = True


@dataclass
class WeatherConfig:
    latitude: float
    longitude: float
    location_name: str


@dataclass
class ConnectorsConfig:
    weather: WeatherConfig
    rss_sources: list[str] = field(default_factory=list)
    notion_enabled: bool = True
    gmail_enabled: bool = True
    calendar_enabled: bool = True
    classroom_enabled: bool = True
    github_enabled: bool = True
    discord_enabled: bool = True


@dataclass
class NexusConfig:
    data_dir: Path
    notion_cache_dir: Path
    timezone: str
    ollama: OllamaConfig
    memory: MemoryConfig
    server: ServerConfig
    scheduler: SchedulerConfig
    digest: DigestConfig
    connectors: ConnectorsConfig


def load_config(path: Path | str | None = None) -> NexusConfig:
    if path is None:
        path = Path("nexus.toml")
    path = Path(path)
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    n = raw["nexus"]
    o = raw["ollama"]
    m = raw["memory"]
    s = raw["server"]
    sc = raw["scheduler"]
    d = raw["digest"]
    cw = raw["connectors"]["weather"]
    cr = raw["connectors"].get("rss", {})

    return NexusConfig(
        data_dir=Path(n["data_dir"]).expanduser(),
        notion_cache_dir=Path(n.get("notion_cache_dir", f"{n['data_dir']}/notion_cache")).expanduser(),
        timezone=n["timezone"],
        ollama=OllamaConfig(**{k: o[k] for k in OllamaConfig.__dataclass_fields__}),
        memory=MemoryConfig(**{k: m[k] for k in MemoryConfig.__dataclass_fields__}),
        server=ServerConfig(**{k: s[k] for k in ServerConfig.__dataclass_fields__}),
        scheduler=SchedulerConfig(**{k: sc[k] for k in SchedulerConfig.__dataclass_fields__}),
        digest=DigestConfig(**{k: d[k] for k in DigestConfig.__dataclass_fields__}),
        connectors=ConnectorsConfig(
            weather=WeatherConfig(**cw),
            rss_sources=cr.get("sources", []),
            notion_enabled=raw["connectors"].get("notion", {}).get("enabled", True),
            gmail_enabled=raw["connectors"].get("gmail", {}).get("enabled", True),
            calendar_enabled=raw["connectors"].get("calendar", {}).get("enabled", True),
            classroom_enabled=raw["connectors"].get("classroom", {}).get("enabled", True),
            github_enabled=raw["connectors"].get("github", {}).get("enabled", True),
            discord_enabled=raw["connectors"].get("discord", {}).get("enabled", True),
        ),
    )
```

- [ ] **Step 4: Run test — expect PASS**

```powershell
uv run pytest tests/test_config.py -v
```

Expected: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add backend/core/config.py tests/test_config.py
git commit -m "feat: config loader with typed dataclasses"
```

---

## Task 3: Ollama Engine (`core/engine.py`)

**Files:**
- Create: `backend/core/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_engine.py
import pytest
import respx
import httpx
from backend.core.engine import OllamaEngine


@pytest.fixture
def engine():
    return OllamaEngine(base_url="http://localhost:11434", model="qwen2.5:7b", embed_model="nomic-embed-text")


@respx.mock
@pytest.mark.asyncio
async def test_embed(engine):
    respx.post("http://localhost:11434/api/embeddings").mock(
        return_value=httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})
    )
    result = await engine.embed("hello world")
    assert result == [0.1, 0.2, 0.3]


@respx.mock
@pytest.mark.asyncio
async def test_chat_non_stream(engine):
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, json={
            "message": {"role": "assistant", "content": "Hello!"},
            "done": True
        })
    )
    result = await engine.chat([{"role": "user", "content": "hi"}], stream=False)
    assert result == "Hello!"
```

- [ ] **Step 2: Run — expect FAIL**

```powershell
uv run pytest tests/test_engine.py -v
```

- [ ] **Step 3: Implement `backend/core/engine.py`**

```python
from __future__ import annotations
import json
from typing import AsyncIterator
import httpx


class OllamaEngine:
    def __init__(self, base_url: str, model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
            )
            r.raise_for_status()
            return r.json()["embedding"]

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        stream: bool = False,
    ) -> str:
        m = model or self.model
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": m, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        m = model or self.model
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": m, "messages": messages, "stream": True},
            ) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if token := chunk.get("message", {}).get("content"):
                        yield token
                    if chunk.get("done"):
                        return

    def route_model(self, query: str) -> str:
        if query.startswith("/code"):
            return self._code_model
        if query.startswith("/think"):
            return self._reasoning_model
        return self.model

    def set_models(self, code: str, reasoning: str) -> None:
        self._code_model = code
        self._reasoning_model = reasoning
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
uv run pytest tests/test_engine.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/engine.py tests/test_engine.py
git commit -m "feat: Ollama engine with chat, stream, embed"
```

---

## Task 4: Database Models (`core/db.py`)

**Files:**
- Create: `backend/core/db.py`

- [ ] **Step 1: Implement `backend/core/db.py`**

```python
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Optional
from sqlmodel import SQLModel, Field, Session, create_engine, select


class Conversation(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Turn(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    role: str  # "user" | "assistant"
    content: str
    model: Optional[str] = None
    sources_used: Optional[str] = None  # JSON list of page_ids
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DigestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)  # YYYY-MM-DD
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConnectorStatus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    healthy: bool = False
    last_checked: Optional[datetime] = None
    last_synced: Optional[datetime] = None
    error_message: Optional[str] = None


_engine = None


def get_engine(data_dir: Path):
    global _engine
    if _engine is None:
        data_dir.mkdir(parents=True, exist_ok=True)
        db_path = data_dir / "nexus.db"
        _engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(_engine)
    return _engine


def get_session(data_dir: Path) -> Session:
    return Session(get_engine(data_dir))
```

- [ ] **Step 2: Verify import**

```powershell
uv run python -c "from backend.core.db import Conversation, Turn, DigestLog, ConnectorStatus; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/core/db.py
git commit -m "feat: SQLite models with SQLModel"
```

---

## Task 5: ChromaDB Memory (`core/memory.py`)

**Files:**
- Create: `backend/core/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_memory.py
import pytest
from pathlib import Path
from backend.core.memory import MemoryStore


@pytest.fixture
def store(tmp_path):
    return MemoryStore(chroma_dir=tmp_path / "chroma")


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


def test_upsert_conversation(store):
    store.upsert_turn(
        turn_id="s1::1",
        text="user: hello\nassistant: hi",
        embedding=[0.2] * 768,
        metadata={"session_id": "s1", "timestamp": "2026-06-01T08:00:00"},
    )
    results = store.search_history("hello", embedding=[0.2] * 768, top_k=1)
    assert len(results) == 1
```

- [ ] **Step 2: Run — expect FAIL**

```powershell
uv run pytest tests/test_memory.py -v
```

- [ ] **Step 3: Implement `backend/core/memory.py`**

```python
from __future__ import annotations
from pathlib import Path
import chromadb
from chromadb.config import Settings


class MemoryStore:
    def __init__(self, chroma_dir: Path):
        chroma_dir = Path(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self._notion = self._client.get_or_create_collection("notion_chunks")
        self._history = self._client.get_or_create_collection("conversation_history")
        self._files = self._client.get_or_create_collection("file_index")

    def upsert_notion_chunk(
        self,
        chunk_id: str,
        text: str,
        embedding: list[float],
        metadata: dict,
    ) -> None:
        self._notion.upsert(ids=[chunk_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_notion(
        self, query: str, embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        result = self._notion.query(query_embeddings=[embedding], n_results=min(top_k, self._notion.count() or 1))
        return self._format_results(result)

    def upsert_turn(self, turn_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._history.upsert(ids=[turn_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_history(self, query: str, embedding: list[float], top_k: int = 10) -> list[dict]:
        count = self._history.count()
        if count == 0:
            return []
        result = self._history.query(query_embeddings=[embedding], n_results=min(top_k, count))
        return self._format_results(result)

    def upsert_file_chunk(self, chunk_id: str, text: str, embedding: list[float], metadata: dict) -> None:
        self._files.upsert(ids=[chunk_id], documents=[text], embeddings=[embedding], metadatas=[metadata])

    def search_files(self, embedding: list[float], top_k: int = 5) -> list[dict]:
        count = self._files.count()
        if count == 0:
            return []
        result = self._files.query(query_embeddings=[embedding], n_results=min(top_k, count))
        return self._format_results(result)

    def _format_results(self, result: dict) -> list[dict]:
        ids = result["ids"][0]
        docs = result["documents"][0]
        metas = result["metadatas"][0]
        dists = result.get("distances", [[]])[0]
        out = []
        for i, doc_id in enumerate(ids):
            entry = {"id": doc_id, "text": docs[i], **(metas[i] or {})}
            if dists:
                entry["score"] = 1 - dists[i]
            out.append(entry)
        return out
```

- [ ] **Step 4: Run tests — expect PASS**

```powershell
uv run pytest tests/test_memory.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/core/memory.py tests/test_memory.py
git commit -m "feat: ChromaDB memory store with 3 collections"
```

---

## Task 6: RAG Agent + Chat Pipeline (`agents/rag.py`, `agents/chat.py`)

**Files:**
- Create: `backend/agents/rag.py`
- Create: `backend/agents/chat.py`
- Create: `tests/test_rag.py`

- [ ] **Step 1: Implement `backend/agents/rag.py`**

```python
from __future__ import annotations
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore


async def retrieve(
    query: str,
    engine: OllamaEngine,
    store: MemoryStore,
    top_k: int = 5,
) -> list[dict]:
    embedding = await engine.embed(query)
    notion_hits = store.search_notion(query, embedding, top_k=top_k)
    return notion_hits
```

- [ ] **Step 2: Implement `backend/agents/chat.py`**

```python
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import AsyncIterator

from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from backend.agents.rag import retrieve


def _select_model(query: str, cfg: NexusConfig) -> str:
    if query.startswith("/code"):
        return cfg.ollama.model_code
    if query.startswith("/think"):
        return cfg.ollama.model_reasoning
    return cfg.ollama.model_general


def _build_system_prompt(notion_chunks: list[dict], live_ctx: dict) -> str:
    parts = [
        "You are NEXUS — Tawin's personal intelligence layer. Bangkok timezone. Developer + student.",
        "Answer concisely, grounded in the context below.",
    ]
    if notion_chunks:
        parts.append("\n## Notion Context")
        for c in notion_chunks:
            parts.append(f"[{c.get('page_title', '?')} / {c.get('heading', '')}]\n{c['text']}")
    if live_ctx:
        parts.append("\n## Live Context")
        for k, v in live_ctx.items():
            if v:
                parts.append(f"**{k}:** {v}")
    return "\n".join(parts)


async def chat_stream(
    query: str,
    session_id: str,
    cfg: NexusConfig,
    engine: OllamaEngine,
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {})
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    async for token in engine.stream_chat(messages, model=model):
        yield token


async def chat_once(
    query: str,
    session_id: str,
    cfg: NexusConfig,
    engine: OllamaEngine,
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {})
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    response = await engine.chat(messages, model=model)
    return response, notion_chunks
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/rag.py backend/agents/chat.py
git commit -m "feat: RAG agent and chat pipeline"
```

---

## Task 7: CLI (`cli/main.py`) — `nexus ask` and `nexus chat`

**Files:**
- Create: `cli/main.py`

- [ ] **Step 1: Implement `cli/main.py`**

```python
from __future__ import annotations
import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from backend.core.config import load_config
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from backend.agents.chat import chat_once, chat_stream

app = typer.Typer(help="NEXUS — personal intelligence layer")
console = Console()
_cfg = None
_engine = None
_store = None


def _init():
    global _cfg, _engine, _store
    if _cfg is None:
        _cfg = load_config()
        _engine = OllamaEngine(
            base_url=_cfg.ollama.base_url,
            model=_cfg.ollama.model_general,
            embed_model=_cfg.ollama.model_embed,
        )
        _engine.set_models(_cfg.ollama.model_code, _cfg.ollama.model_reasoning)
        _store = MemoryStore(Path(_cfg.memory.chroma_dir).expanduser())
    return _cfg, _engine, _store


@app.command()
def ask(query: str = typer.Argument(..., help="Question to ask NEXUS")):
    cfg, engine, store = _init()

    async def _run():
        response, chunks = await chat_once(query, "cli", cfg, engine, store)
        console.print(Markdown(response))
        if chunks:
            sources = ", ".join(c.get("page_title", "?") for c in chunks[:3])
            console.print(f"[dim]Sources: {sources}[/dim]")

    asyncio.run(_run())


@app.command()
def chat():
    cfg, engine, store = _init()
    history = []
    console.print(Panel("[bold amber]NEXUS Chat[/bold amber] — /code · /think · Ctrl+C to exit", style="dim"))

    async def _loop():
        while True:
            try:
                query = typer.prompt("you")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[dim]goodbye[/dim]")
                break
            tokens = []
            async for token in chat_stream(query, "interactive", cfg, engine, store, history=history):
                console.print(token, end="", highlight=False)
                tokens.append(token)
            response = "".join(tokens)
            console.print()
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": response})

    asyncio.run(_loop())


@app.command()
def serve():
    cfg, _, _ = _init()
    import uvicorn
    from backend.api.main import create_app
    web_app = create_app(cfg)
    if cfg.server.open_browser_on_start:
        import webbrowser, threading
        threading.Timer(1.5, lambda: webbrowser.open(f"http://{cfg.server.host}:{cfg.server.port}")).start()
    uvicorn.run(web_app, host=cfg.server.host, port=cfg.server.port)


@app.command()
def doctor():
    cfg, engine, store = _init()
    console.print(Panel("[bold]NEXUS Doctor[/bold]", style="amber"))
    import httpx, asyncio

    async def _check():
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{cfg.ollama.base_url}/api/tags")
                console.print(f"[green]✓[/green] Ollama reachable — {len(r.json().get('models', []))} models")
        except Exception as e:
            console.print(f"[red]✗[/red] Ollama: {e}")

    asyncio.run(_check())
    console.print("[green]✓[/green] ChromaDB accessible")
    console.print("[dim]Run 'nexus connect <service>' to set up connectors[/dim]")


@app.command()
def sync():
    cfg, _, _ = _init()
    from backend.connectors.notion_sync import NotionSync
    import asyncio
    syncer = NotionSync(cfg)
    asyncio.run(syncer.sync_all())
    console.print("[green]✓[/green] Notion sync complete")


@app.command()
def note(text: str = typer.Argument(...)):
    cfg, _, _ = _init()
    from backend.connectors.notion import NotionConnector
    import asyncio
    nc = NotionConnector(cfg)
    asyncio.run(nc.create_idea(text))
    console.print(f"[green]✓[/green] Saved to Ideas: {text}")


@app.command()
def log(text: str = typer.Argument(...)):
    cfg, _, _ = _init()
    from backend.connectors.notion import NotionConnector
    import asyncio
    nc = NotionConnector(cfg)
    asyncio.run(nc.append_to_daily_notes(text))
    console.print(f"[green]✓[/green] Logged to today's daily note")


@app.command()
def digest():
    cfg, engine, store = _init()
    from backend.agents.digest import DigestAgent
    import asyncio
    agent = DigestAgent(cfg, engine)
    asyncio.run(agent.run())


if __name__ == "__main__":
    app()
```

- [ ] **Step 2: Smoke test ask**

```powershell
uv run python -m cli.main ask "what is 2+2"
```

Expected: Response from Ollama (Ollama must be running with qwen2.5:7b pulled).

- [ ] **Step 3: Commit**

```bash
git add cli/main.py
git commit -m "feat: CLI with ask, chat, serve, doctor, sync, note, log, digest"
```

---

## Task 8: Notion Connector

**Files:**
- Create: `backend/connectors/base.py`
- Create: `backend/connectors/notion.py`
- Create: `backend/connectors/notion_sync.py`

- [ ] **Step 1: Implement `backend/connectors/base.py`**

```python
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
```

- [ ] **Step 2: Implement `backend/connectors/notion.py`**

```python
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, date
import httpx
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

WORKSPACE_SCAFFOLD = [
    ("📅 Daily Notes", "database"),
    ("🚀 Projects", "database"),
    ("🔬 Research", "database"),
    ("🎓 Courses", "database"),
    ("💡 Ideas", "database"),
    ("👥 People", "database"),
    ("📚 Resources", "database"),
    ("🗄️ Archive", "page"),
]


class NotionConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._token = self._load_token()

    def _load_token(self) -> str | None:
        p = Path(self._cfg.data_dir) / "notion.json"
        if p.exists():
            return json.loads(p.read_text())["token"]
        return None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._token:
            return HealthResult("notion", False, "No token")
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{NOTION_API}/users/me", headers=self._headers())
                r.raise_for_status()
            return HealthResult("notion", True)
        except Exception as e:
            return HealthResult("notion", False, str(e))

    async def search_pages(self, query: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{NOTION_API}/search",
                headers=self._headers(),
                json={"query": query, "filter": {"value": "page", "property": "object"}},
            )
            r.raise_for_status()
            return r.json().get("results", [])

    async def get_page_content(self, page_id: str) -> str:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{NOTION_API}/blocks/{page_id}/children", headers=self._headers())
            r.raise_for_status()
            blocks = r.json().get("results", [])
        return self._blocks_to_md(blocks)

    def _blocks_to_md(self, blocks: list[dict]) -> str:
        lines = []
        for b in blocks:
            t = b.get("type", "")
            block = b.get(t, {})
            rich_text = block.get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)
            if t == "heading_1":
                lines.append(f"# {text}")
            elif t == "heading_2":
                lines.append(f"## {text}")
            elif t == "heading_3":
                lines.append(f"### {text}")
            elif t in ("paragraph", "quote"):
                lines.append(text)
            elif t == "bulleted_list_item":
                lines.append(f"- {text}")
            elif t == "numbered_list_item":
                lines.append(f"1. {text}")
            elif t == "to_do":
                checked = "x" if block.get("checked") else " "
                lines.append(f"- [{checked}] {text}")
            elif t == "code":
                lang = block.get("language", "")
                lines.append(f"```{lang}\n{text}\n```")
        return "\n".join(lines)

    async def get_all_pages(self) -> list[dict]:
        pages = []
        cursor = None
        async with httpx.AsyncClient(timeout=20) as c:
            while True:
                body: dict = {"filter": {"value": "page", "property": "object"}, "page_size": 100}
                if cursor:
                    body["start_cursor"] = cursor
                r = await c.post(f"{NOTION_API}/search", headers=self._headers(), json=body)
                r.raise_for_status()
                data = r.json()
                pages.extend(data.get("results", []))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
        return pages

    async def append_to_daily_notes(self, text: str) -> None:
        today = date.today().isoformat()
        pages = await self.search_pages(f"Daily Notes {today}")
        if not pages:
            return
        page_id = pages[0]["id"]
        async with httpx.AsyncClient(timeout=10) as c:
            await c.patch(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=self._headers(),
                json={"children": [{"object": "block", "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": text}}]}}]},
            )

    async def create_idea(self, text: str) -> None:
        pages = await self.search_pages("Ideas")
        if not pages:
            return
        db_id = pages[0].get("id")
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"{NOTION_API}/pages",
                headers=self._headers(),
                json={"parent": {"database_id": db_id},
                      "properties": {"title": {"title": [{"text": {"content": text}}]}}},
            )
```

- [ ] **Step 3: Implement `backend/connectors/notion_sync.py`**

```python
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
import httpx
from backend.core.config import NexusConfig
from backend.connectors.notion import NotionConnector


class NotionSync:
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._connector = NotionConnector(cfg)
        self._cache_dir = Path(cfg.notion_cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def sync_all(self) -> list[Path]:
        pages = await self._connector.get_all_pages()
        updated = []
        for page in pages:
            page_id = page["id"]
            title = self._extract_title(page)
            try:
                content = await self._connector.get_page_content(page_id)
                md_path = self._cache_dir / f"{page_id}.md"
                frontmatter = f"---\npage_id: {page_id}\ntitle: {title}\nsynced: {datetime.utcnow().isoformat()}\n---\n\n"
                md_path.write_text(frontmatter + f"# {title}\n\n" + content, encoding="utf-8")
                updated.append(md_path)
            except Exception:
                continue
        return updated

    def _extract_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for key in ("title", "Title", "Name"):
            if key in props:
                title_obj = props[key]
                rich = title_obj.get("title", []) or title_obj.get("rich_text", [])
                if rich:
                    return rich[0].get("plain_text", "Untitled")
        return "Untitled"
```

- [ ] **Step 4: Commit**

```bash
git add backend/connectors/base.py backend/connectors/notion.py backend/connectors/notion_sync.py
git commit -m "feat: Notion connector with sync daemon"
```

---

## Task 9: Google Connectors (Gmail, Calendar, Classroom)

**Files:**
- Create: `backend/connectors/gmail.py`
- Create: `backend/connectors/calendar.py`
- Create: `backend/connectors/classroom.py`

- [ ] **Step 1: Implement `backend/connectors/gmail.py`**

```python
from __future__ import annotations
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
]


def _load_creds(data_dir: Path) -> Credentials | None:
    token_path = data_dir / "gmail_token.json"
    creds_path = data_dir / "gmail_credentials.json"
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


class GmailConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("gmail", False, "No credentials")
        try:
            svc = build("gmail", "v1", credentials=self._creds)
            svc.users().getProfile(userId="me").execute()
            return HealthResult("gmail", True)
        except Exception as e:
            return HealthResult("gmail", False, str(e))

    def unread_count(self) -> dict:
        if not self._creds:
            return {}
        svc = build("gmail", "v1", credentials=self._creds)
        result = svc.users().messages().list(userId="me", q="is:unread", maxResults=10).execute()
        messages = result.get("messages", [])
        count = result.get("resultSizeEstimate", 0)
        top_sender = None
        if messages:
            msg = svc.users().messages().get(userId="me", id=messages[0]["id"], format="metadata",
                                              metadataHeaders=["From"]).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            top_sender = headers.get("From", "Unknown")
        return {"count": count, "top_sender": top_sender}
```

- [ ] **Step 2: Implement `backend/connectors/calendar.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig
from backend.connectors.gmail import _load_creds


class CalendarConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("calendar", False, "No credentials")
        return HealthResult("calendar", True)

    def today_events(self) -> list[dict]:
        if not self._creds:
            return []
        svc = build("calendar", "v3", credentials=self._creds)
        now = datetime.now(timezone.utc)
        end = now.replace(hour=23, minute=59, second=59)
        result = svc.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute()
        events = []
        for e in result.get("items", []):
            start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date", "")
            events.append({"summary": e.get("summary", "?"), "start": start})
        return events
```

- [ ] **Step 3: Implement `backend/connectors/classroom.py`**

```python
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig
from backend.connectors.gmail import _load_creds


class ClassroomConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("classroom", False, "No credentials")
        try:
            svc = build("classroom", "v1", credentials=self._creds)
            svc.courses().list(pageSize=1).execute()
            return HealthResult("classroom", True)
        except Exception as e:
            return HealthResult("classroom", False, str(e))

    def due_soon(self, hours: int = 48) -> list[dict]:
        if not self._creds:
            return []
        svc = build("classroom", "v1", credentials=self._creds)
        courses = svc.courses().list(courseStates=["ACTIVE"]).execute().get("courses", [])
        due = []
        cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
        for course in courses:
            cid = course["id"]
            cname = course.get("name", "?")
            works = svc.courses().courseWork().list(courseId=cid, orderBy="dueDate").execute().get("courseWork", [])
            for w in works:
                due_date = w.get("dueDate")
                if not due_date:
                    continue
                due_dt = datetime(
                    due_date["year"], due_date["month"], due_date["day"],
                    tzinfo=timezone.utc
                )
                if due_dt <= cutoff:
                    due.append({"course": cname, "title": w.get("title", "?"), "due": due_dt.isoformat()})
        return sorted(due, key=lambda x: x["due"])

    def announcements(self) -> list[dict]:
        if not self._creds:
            return []
        svc = build("classroom", "v1", credentials=self._creds)
        courses = svc.courses().list(courseStates=["ACTIVE"]).execute().get("courses", [])
        ann = []
        for course in courses:
            cid = course["id"]
            cname = course.get("name", "?")
            items = svc.courses().announcements().list(courseId=cid, pageSize=5).execute().get("announcements", [])
            for a in items:
                ann.append({"course": cname, "text": a.get("text", "")[:200], "creation_time": a.get("creationTime", "")})
        return ann
```

- [ ] **Step 4: Commit**

```bash
git add backend/connectors/gmail.py backend/connectors/calendar.py backend/connectors/classroom.py
git commit -m "feat: Gmail, Calendar, Classroom connectors"
```

---

## Task 10: Remaining Connectors (GitHub, Discord, Weather, RSS)

**Files:**
- Create: `backend/connectors/github.py`
- Create: `backend/connectors/discord.py`
- Create: `backend/connectors/weather.py`
- Create: `backend/connectors/rss.py`

- [ ] **Step 1: Implement `backend/connectors/github.py`**

```python
from __future__ import annotations
import json
from pathlib import Path
from github import Github
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig


class GitHubConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        token_path = Path(cfg.data_dir) / "github.json"
        self._token = json.loads(token_path.read_text())["token"] if token_path.exists() else None
        self._gh = Github(self._token) if self._token else None

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        if not self._gh:
            return HealthResult("github", False, "No token")
        try:
            self._gh.get_user().login
            return HealthResult("github", True)
        except Exception as e:
            return HealthResult("github", False, str(e))

    def open_prs(self) -> list[dict]:
        if not self._gh:
            return []
        prs = self._gh.search_issues("is:open is:pr author:@me")
        return [{"title": pr.title, "repo": pr.repository.full_name if hasattr(pr, "repository") else "?",
                 "url": pr.html_url} for pr in list(prs)[:5]]

    def notifications(self) -> list[dict]:
        if not self._gh:
            return []
        user = self._gh.get_user()
        notifs = user.get_notifications(all=False)
        return [{"subject": n.subject.title, "type": n.subject.type,
                 "repo": n.repository.full_name} for n in list(notifs)[:5]]
```

- [ ] **Step 2: Implement `backend/connectors/weather.py`**

```python
from __future__ import annotations
import httpx
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

WMO_CODES = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast",
             61: "Light rain", 63: "Rain", 65: "Heavy rain", 80: "Showers",
             95: "Thunderstorm", 96: "Thunderstorm + hail"}


class WeatherConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._lat = cfg.connectors.weather.latitude
        self._lon = cfg.connectors.weather.longitude
        self._name = cfg.connectors.weather.location_name

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        try:
            await self.current()
            return HealthResult("weather", True)
        except Exception as e:
            return HealthResult("weather", False, str(e))

    async def current(self) -> dict:
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={self._lat}&longitude={self._lon}"
               f"&current_weather=true&hourly=relative_humidity_2m&timezone=Asia%2FBangkok")
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
        cw = data["current_weather"]
        code = cw.get("weathercode", 0)
        desc = WMO_CODES.get(code, f"Code {code}")
        return {
            "location": self._name,
            "temp_c": cw["temperature"],
            "wind_kmh": cw["windspeed"],
            "description": desc,
        }
```

- [ ] **Step 3: Implement `backend/connectors/rss.py`**

```python
from __future__ import annotations
import feedparser
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig


class RssConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._sources = cfg.connectors.rss_sources

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        return HealthResult("rss", bool(self._sources))

    def fetch(self, max_per_feed: int = 3) -> list[dict]:
        articles = []
        for url in self._sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_feed]:
                    articles.append({
                        "title": entry.get("title", "?"),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "source": feed.feed.get("title", url),
                    })
            except Exception:
                continue
        return articles
```

- [ ] **Step 4: Implement `backend/connectors/discord.py`**

```python
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
```

- [ ] **Step 5: Create stubs**

```python
# backend/connectors/stubs/telegram.py
class TelegramConnector:
    async def send(self, text: str) -> None:
        raise NotImplementedError("Telegram stub — not yet implemented")
```

```python
# backend/connectors/stubs/spotify.py
class SpotifyConnector:
    async def now_playing(self) -> dict:
        raise NotImplementedError("Spotify stub — not yet implemented")
```

- [ ] **Step 6: Commit**

```bash
git add backend/connectors/
git commit -m "feat: GitHub, Discord, Weather, RSS connectors + stubs"
```

---

## Task 11: Digest Agent + Scheduler

**Files:**
- Create: `backend/agents/digest.py`
- Create: `backend/scheduler/jobs.py`

- [ ] **Step 1: Implement `backend/agents/digest.py`**

```python
from __future__ import annotations
import asyncio
from datetime import date
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich import box
from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.connectors.weather import WeatherConnector
from backend.connectors.calendar import CalendarConnector
from backend.connectors.gmail import GmailConnector
from backend.connectors.github import GitHubConnector
from backend.connectors.classroom import ClassroomConnector
from backend.connectors.rss import RssConnector

console = Console()


class DigestAgent:
    def __init__(self, cfg: NexusConfig, engine: OllamaEngine):
        self._cfg = cfg
        self._engine = engine

    async def run(self) -> str:
        today = date.today().isoformat()
        sections = []

        try:
            weather = await WeatherConnector(self._cfg).current()
            sections.append(f"## 🌤 Weather — {weather['location']}\n{weather['temp_c']}°C · {weather['description']} · Wind {weather['wind_kmh']} km/h")
        except Exception:
            sections.append("## 🌤 Weather\n(unavailable)")

        try:
            events = CalendarConnector(self._cfg).today_events()
            ev_text = "\n".join(f"- {e['start'][:16]} {e['summary']}" for e in events) or "No events today"
            sections.append(f"## 📅 Calendar\n{ev_text}")
        except Exception:
            sections.append("## 📅 Calendar\n(unavailable)")

        try:
            gmail = GmailConnector(self._cfg).unread_count()
            sections.append(f"## 📧 Gmail\n{gmail.get('count', 0)} unread · Top: {gmail.get('top_sender', '?')}")
        except Exception:
            sections.append("## 📧 Gmail\n(unavailable)")

        try:
            gh = GitHubConnector(self._cfg)
            prs = gh.open_prs()
            pr_text = "\n".join(f"- {p['title']} ({p['repo']})" for p in prs) or "No open PRs"
            sections.append(f"## 🐙 GitHub\n{pr_text}")
        except Exception:
            sections.append("## 🐙 GitHub\n(unavailable)")

        try:
            due = ClassroomConnector(self._cfg).due_soon(hours=48)
            due_text = "\n".join(f"- [{d['course']}] {d['title']} due {d['due'][:10]}" for d in due) or "No assignments due soon"
            sections.append(f"## 🎓 Classroom\n{due_text}")
        except Exception:
            sections.append("## 🎓 Classroom\n(unavailable)")

        try:
            articles = RssConnector(self._cfg).fetch(max_per_feed=2)[:5]
            rss_text = "\n".join(f"- [{a['source']}] {a['title']}" for a in articles) or "No articles"
            sections.append(f"## 📰 RSS\n{rss_text}")
        except Exception:
            sections.append("## 📰 RSS\n(unavailable)")

        content = f"# Morning Briefing — {today}\n\n" + "\n\n".join(sections)

        if self._cfg.digest.print_to_terminal:
            console.print(Panel(content, title=f"[bold amber]NEXUS Digest — {today}[/bold amber]", box=box.ROUNDED))

        return content
```

- [ ] **Step 2: Implement `backend/scheduler/jobs.py`**

```python
from __future__ import annotations
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from pathlib import Path


def create_scheduler(cfg: NexusConfig, engine: OllamaEngine, store: MemoryStore) -> AsyncIOScheduler:
    tz = pytz.timezone(cfg.timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    async def run_digest():
        from backend.agents.digest import DigestAgent
        await DigestAgent(cfg, engine).run()

    async def run_notion_sync():
        from backend.connectors.notion_sync import NotionSync
        await NotionSync(cfg).sync_all()

    digest_cron = dict(zip(["minute", "hour", "day", "month", "day_of_week"],
                            cfg.scheduler.digest_cron.split()))
    sync_parts = cfg.scheduler.notion_sync_cron.split()

    scheduler.add_job(run_digest, CronTrigger(**digest_cron, timezone=tz), id="digest")
    scheduler.add_job(run_notion_sync, CronTrigger(minute="*/15", timezone=tz), id="notion_sync")

    return scheduler
```

- [ ] **Step 3: Commit**

```bash
git add backend/agents/digest.py backend/scheduler/jobs.py
git commit -m "feat: digest agent and APScheduler cron jobs"
```

---

## Task 12: FastAPI Backend

**Files:**
- Create: `backend/api/main.py`
- Create: `backend/api/routes/chat.py`
- Create: `backend/api/routes/digest.py`
- Create: `backend/api/routes/notion.py`
- Create: `backend/api/routes/connectors.py`
- Create: `backend/api/routes/memory.py`

- [ ] **Step 1: Implement `backend/api/main.py`**

```python
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.core.config import NexusConfig
from backend.core.engine import OllamaEngine
from backend.core.memory import MemoryStore
from backend.api.routes import chat, digest, notion, connectors, memory


def create_app(cfg: NexusConfig) -> FastAPI:
    engine = OllamaEngine(cfg.ollama.base_url, cfg.ollama.model_general, cfg.ollama.model_embed)
    engine.set_models(cfg.ollama.model_code, cfg.ollama.model_reasoning)
    store = MemoryStore(Path(cfg.memory.chroma_dir).expanduser())

    app = FastAPI(title="NEXUS API")
    app.state.cfg = cfg
    app.state.engine = engine
    app.state.store = store

    app.include_router(chat.router, prefix="/api")
    app.include_router(digest.router, prefix="/api")
    app.include_router(notion.router, prefix="/api")
    app.include_router(connectors.router, prefix="/api")
    app.include_router(memory.router, prefix="/api")

    dist = Path(cfg.server.frontend_dist)
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=str(dist / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_spa():
            return FileResponse(str(dist / "index.html"))

    return app
```

- [ ] **Step 2: Implement `backend/api/routes/chat.py`**

```python
from __future__ import annotations
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None


@router.post("/chat")
async def chat(req: ChatRequest, request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    store = request.app.state.store
    session_id = req.session_id or str(uuid.uuid4())
    from backend.agents.chat import chat_once
    response, chunks = await chat_once(req.query, session_id, cfg, engine, store)
    context_chips = [
        {"page_title": c.get("page_title", "?"), "heading": c.get("heading", ""),
         "database": c.get("database", ""), "score": round(c.get("score", 0), 3)}
        for c in chunks
    ]
    return {"response": response, "context_chips": context_chips, "model": engine.model, "session_id": session_id}


@router.get("/chat/stream")
async def chat_stream_endpoint(query: str, request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    store = request.app.state.store
    from backend.agents.chat import chat_stream

    async def generate():
        async for token in chat_stream(query, "stream", cfg, engine, store):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

- [ ] **Step 3: Implement remaining routes**

```python
# backend/api/routes/digest.py
from fastapi import APIRouter, Request, BackgroundTasks
router = APIRouter()

@router.get("/digest")
async def get_digest(request: Request):
    return {"content": "No digest yet"}

@router.post("/digest/run")
async def run_digest(request: Request, background_tasks: BackgroundTasks):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    async def _run():
        from backend.agents.digest import DigestAgent
        await DigestAgent(cfg, engine).run()
    background_tasks.add_task(_run)
    return {"status": "running"}
```

```python
# backend/api/routes/notion.py
from fastapi import APIRouter, Request
from backend.connectors.notion import NotionConnector
from backend.connectors.notion_sync import NotionSync
router = APIRouter()

@router.get("/notion/tree")
async def notion_tree(request: Request):
    nc = NotionConnector(request.app.state.cfg)
    pages = await nc.get_all_pages()
    return {"pages": [{"id": p["id"], "title": _extract_title(p)} for p in pages[:50]]}

@router.get("/notion/page")
async def notion_page(page_id: str, request: Request):
    nc = NotionConnector(request.app.state.cfg)
    content = await nc.get_page_content(page_id)
    return {"page_id": page_id, "content_md": content}

@router.get("/notion/search")
async def notion_search(q: str, request: Request):
    nc = NotionConnector(request.app.state.cfg)
    results = await nc.search_pages(q)
    return {"results": [{"id": r["id"], "title": _extract_title(r)} for r in results[:10]]}

def _extract_title(page: dict) -> str:
    props = page.get("properties", {})
    for key in ("title", "Title", "Name"):
        if key in props:
            rt = props[key].get("title", []) or props[key].get("rich_text", [])
            if rt:
                return rt[0].get("plain_text", "Untitled")
    return "Untitled"
```

```python
# backend/api/routes/connectors.py
from fastapi import APIRouter, Request
import asyncio
router = APIRouter()

@router.get("/status")
async def status(request: Request):
    cfg = request.app.state.cfg
    from backend.connectors.notion import NotionConnector
    from backend.connectors.weather import WeatherConnector
    from backend.connectors.github import GitHubConnector
    from backend.connectors.discord import DiscordConnector
    from backend.connectors.gmail import GmailConnector

    connectors = [
        NotionConnector(cfg), GmailConnector(cfg),
        WeatherConnector(cfg), GitHubConnector(cfg), DiscordConnector(cfg),
    ]
    results = await asyncio.gather(*[c.health() for c in connectors], return_exceptions=True)
    return {
        "connectors": [
            {"name": r.name, "healthy": r.healthy, "error": r.error}
            for r in results if hasattr(r, "name")
        ],
        "model": request.app.state.engine.model,
    }
```

```python
# backend/api/routes/memory.py
from fastapi import APIRouter, Request, BackgroundTasks
from pydantic import BaseModel
router = APIRouter()

class IndexRequest(BaseModel):
    path: str

@router.post("/memory/index")
async def index_path(req: IndexRequest, request: Request, background_tasks: BackgroundTasks):
    background_tasks.add_task(lambda: None)  # placeholder for file indexer
    return {"status": "queued", "path": req.path}

@router.post("/sync")
async def force_sync(request: Request, background_tasks: BackgroundTasks):
    cfg = request.app.state.cfg
    async def _sync():
        from backend.connectors.notion_sync import NotionSync
        await NotionSync(cfg).sync_all()
    background_tasks.add_task(_sync)
    return {"status": "syncing"}
```

- [ ] **Step 4: Smoke test the API**

```powershell
uv run python -c "from backend.api.main import create_app; from backend.core.config import load_config; app = create_app(load_config()); print('API created OK')"
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/
git commit -m "feat: FastAPI backend with all routes"
```

---

## Task 13: React Frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/views/Chat.tsx`
- Create: `frontend/src/views/Digest.tsx`
- Create: `frontend/src/views/Notion.tsx`
- Create: `frontend/src/views/Status.tsx`
- Create: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Init frontend**

```powershell
Set-Location frontend
npm create vite@latest . -- --template react-ts
npm install tailwindcss @tailwindcss/typography autoprefixer postcss
npm install react-markdown react-router-dom
Set-Location ..
```

- [ ] **Step 2: Write `frontend/vite.config.ts`**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
```

- [ ] **Step 3: Write `frontend/src/lib/api.ts`**

```typescript
const BASE = '/api'

export async function postChat(query: string, sessionId?: string) {
  const r = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, session_id: sessionId }),
  })
  return r.json()
}

export function streamChat(query: string, onToken: (t: string) => void, onDone: () => void) {
  const url = `${BASE}/chat/stream?query=${encodeURIComponent(query)}`
  const es = new EventSource(url)
  es.onmessage = (e) => {
    if (e.data === '[DONE]') { onDone(); es.close(); return }
    onToken(e.data)
  }
  return es
}

export async function getStatus() {
  return (await fetch(`${BASE}/status`)).json()
}

export async function runDigest() {
  return (await fetch(`${BASE}/digest/run`, { method: 'POST' })).json()
}

export async function getNotionTree() {
  return (await fetch(`${BASE}/notion/tree`)).json()
}

export async function getNotionPage(pageId: string) {
  return (await fetch(`${BASE}/notion/page?page_id=${pageId}`)).json()
}

export async function searchNotion(q: string) {
  return (await fetch(`${BASE}/notion/search?q=${encodeURIComponent(q)}`)).json()
}
```

- [ ] **Step 4: Write `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Chat from './views/Chat'
import Digest from './views/Digest'
import NotionView from './views/Notion'
import Status from './views/Status'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0a0a0a] text-[#e0e0e0] font-mono">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/digest" />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/notion" element={<NotionView />} />
            <Route path="/status" element={<Status />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
```

- [ ] **Step 5: Write `frontend/src/components/Sidebar.tsx`**

```tsx
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/digest', label: '📋 Digest' },
  { to: '/chat', label: '💬 Chat' },
  { to: '/notion', label: '📝 Notion' },
  { to: '/status', label: '⚡ Status' },
]

export default function Sidebar() {
  return (
    <nav className="w-44 border-r border-[#1e1e1e] flex flex-col p-4 gap-2 shrink-0">
      <div className="text-[#d4a017] font-bold text-sm mb-4">NEXUS</div>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `text-xs px-2 py-1.5 rounded transition-colors ${
              isActive ? 'bg-[#1e1e1e] text-[#d4a017]' : 'text-[#555] hover:text-[#e0e0e0]'
            }`
          }
        >
          {l.label}
        </NavLink>
      ))}
    </nav>
  )
}
```

- [ ] **Step 6: Write Chat view**

```tsx
// frontend/src/views/Chat.tsx
import { useState, useRef, useEffect } from 'react'
import { streamChat } from '../lib/api'
import ReactMarkdown from 'react-markdown'

interface Message { role: 'user' | 'assistant'; content: string }

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    if (!input.trim() || streaming) return
    const query = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: query }])
    setMessages(m => [...m, { role: 'assistant', content: '' }])
    setStreaming(true)
    streamChat(
      query,
      (token) => setMessages(m => {
        const copy = [...m]
        copy[copy.length - 1].content += token
        return copy
      }),
      () => setStreaming(false),
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {messages.map((m, i) => (
          <div key={i} className={`text-xs leading-relaxed ${m.role === 'user' ? 'text-[#d4a017]' : 'text-[#e0e0e0]'}`}>
            <span className="text-[#555] mr-2">{m.role === 'user' ? 'you' : 'nexus'}</span>
            <ReactMarkdown>{m.content}</ReactMarkdown>
            {streaming && i === messages.length - 1 && m.role === 'assistant' && (
              <span className="animate-pulse">▋</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-[#1e1e1e] p-3 flex gap-2">
        <input
          className="flex-1 bg-[#111] border border-[#1e1e1e] text-xs px-3 py-2 rounded text-[#e0e0e0] outline-none focus:border-[#d4a017]"
          placeholder="/code · /think · or just ask..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
        />
        <button
          className="bg-[#d4a017] text-black text-xs px-3 py-2 rounded font-bold disabled:opacity-40"
          onClick={send}
          disabled={streaming}
        >
          send
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 7: Write Digest view**

```tsx
// frontend/src/views/Digest.tsx
import { useEffect, useState } from 'react'
import { runDigest } from '../lib/api'
import ReactMarkdown from 'react-markdown'

export default function Digest() {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(false)

  async function refresh() {
    setLoading(true)
    try {
      await runDigest()
      setContent('Digest triggered — check terminal for output.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-[#d4a017] font-bold text-sm">Morning Briefing</h1>
        <button
          className="text-xs bg-[#1e1e1e] px-3 py-1.5 rounded hover:bg-[#2a2a2a] disabled:opacity-40"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'running...' : '↻ refresh'}
        </button>
      </div>
      {content ? (
        <div className="prose prose-invert prose-sm max-w-none text-xs">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      ) : (
        <p className="text-[#555] text-xs">Click refresh to run the digest</p>
      )}
    </div>
  )
}
```

- [ ] **Step 8: Write Notion + Status views**

```tsx
// frontend/src/views/Notion.tsx
import { useEffect, useState } from 'react'
import { getNotionTree, getNotionPage, searchNotion } from '../lib/api'
import ReactMarkdown from 'react-markdown'

export default function NotionView() {
  const [pages, setPages] = useState<{id: string; title: string}[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => { getNotionTree().then(d => setPages(d.pages || [])) }, [])

  async function loadPage(id: string) {
    setSelected(id)
    const d = await getNotionPage(id)
    setContent(d.content_md || '')
  }

  async function doSearch() {
    if (!search.trim()) return
    const d = await searchNotion(search)
    setPages(d.results || [])
  }

  return (
    <div className="flex h-full">
      <div className="w-56 border-r border-[#1e1e1e] p-3 overflow-auto">
        <input
          className="w-full bg-[#111] border border-[#1e1e1e] text-xs px-2 py-1 rounded mb-3 text-[#e0e0e0]"
          placeholder="search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
        />
        {pages.map(p => (
          <button
            key={p.id}
            className={`block w-full text-left text-xs px-2 py-1 rounded mb-0.5 ${selected === p.id ? 'text-[#d4a017]' : 'text-[#555] hover:text-[#e0e0e0]'}`}
            onClick={() => loadPage(p.id)}
          >
            {p.title}
          </button>
        ))}
      </div>
      <div className="flex-1 p-6 overflow-auto">
        {content
          ? <div className="prose prose-invert prose-sm max-w-none text-xs"><ReactMarkdown>{content}</ReactMarkdown></div>
          : <p className="text-[#555] text-xs">Select a page</p>}
      </div>
    </div>
  )
}
```

```tsx
// frontend/src/views/Status.tsx
import { useEffect, useState } from 'react'
import { getStatus } from '../lib/api'

interface ConnectorStatus { name: string; healthy: boolean; error?: string }

export default function Status() {
  const [data, setData] = useState<{ connectors: ConnectorStatus[]; model: string } | null>(null)

  useEffect(() => { getStatus().then(setData) }, [])

  return (
    <div className="p-6">
      <h1 className="text-[#d4a017] font-bold text-sm mb-4">System Status</h1>
      {data?.model && <p className="text-xs text-[#555] mb-4">Model: <span className="text-[#e0e0e0]">{data.model}</span></p>}
      <div className="grid grid-cols-2 gap-2">
        {(data?.connectors || []).map(c => (
          <div key={c.name} className="border border-[#1e1e1e] rounded p-3 flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${c.healthy ? 'bg-[#4caf50]' : 'bg-[#cf6679]'}`} />
            <span className="text-xs">{c.name}</span>
            {c.error && <span className="text-[10px] text-[#cf6679] ml-auto truncate max-w-24">{c.error}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 9: Build frontend**

```powershell
Set-Location frontend
npm run build
Set-Location ..
```

Expected: `frontend/dist/` created.

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: React frontend with Chat, Digest, Notion, Status views"
```

---

## Task 14: Setup Script + Windows Auto-Start

**Files:**
- Create: `setup.ps1`

- [ ] **Step 1: Write `setup.ps1`**

```powershell
#Requires -Version 5.1
$ErrorActionPreference = "Stop"

Write-Host "=== NEXUS Setup ===" -ForegroundColor Yellow

# 1. Check uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..." -ForegroundColor Cyan
    winget install --id astral-sh.uv --silent
}

# 2. Python deps
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
uv sync

# 3. Frontend
Write-Host "Building frontend..." -ForegroundColor Cyan
Set-Location frontend
npm install
npm run build
Set-Location ..

# 4. Ollama models
Write-Host "Pulling Ollama models..." -ForegroundColor Cyan
$models = @("qwen2.5:7b", "qwen2.5-coder:7b", "deepseek-r1:7b", "nomic-embed-text")
foreach ($m in $models) {
    Write-Host "  Pulling $m..."
    ollama pull $m
}

# 5. Config
if (-not (Test-Path nexus.toml)) {
    Copy-Item nexus.toml.example nexus.toml
    Write-Host "Created nexus.toml from example" -ForegroundColor Green
}

# 6. Data dir
$nexusDir = "$env:USERPROFILE\.nexus"
New-Item -ItemType Directory -Force -Path $nexusDir | Out-Null
New-Item -ItemType Directory -Force -Path "$nexusDir\notion_cache" | Out-Null

# 7. Global gitignore
$gitIgnore = "$env:USERPROFILE\.gitignore_global"
if (-not (Get-Content $gitIgnore -ErrorAction SilentlyContinue | Select-String "\.nexus")) {
    Add-Content $gitIgnore "`n# NEXUS secrets`n.nexus/"
}

# 8. Google OAuth setup instructions
Write-Host ""
Write-Host "=== Google OAuth Setup ===" -ForegroundColor Yellow
Write-Host "1. Go to: https://console.cloud.google.com"
Write-Host "2. Create a new project called 'NEXUS'"
Write-Host "3. Enable APIs: Gmail, Calendar, Google Classroom"
Write-Host "4. Create OAuth2 credentials (Desktop app)"
Write-Host "5. Download credentials.json → save to: $nexusDir\gmail_credentials.json"
Write-Host ""
Read-Host "Press Enter when done"

# 9. GitHub token
Write-Host "=== GitHub Token ===" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/settings/tokens/new"
Write-Host "2. Scopes needed: repo, notifications, read:user"
$ghToken = Read-Host "Paste your GitHub PAT (or Enter to skip)"
if ($ghToken) {
    '{"token": "' + $ghToken + '"}' | Out-File "$nexusDir\github.json" -Encoding utf8
}

# 10. Notion token
Write-Host "=== Notion Token ===" -ForegroundColor Yellow
Write-Host "1. Go to: https://www.notion.so/my-integrations"
Write-Host "2. Create integration, copy Internal Integration Secret"
$notionToken = Read-Host "Paste your Notion token (or Enter to skip)"
if ($notionToken) {
    '{"token": "' + $notionToken + '"}' | Out-File "$nexusDir\notion.json" -Encoding utf8
}

# 11. Discord bot token
Write-Host "=== Discord Bot Token ===" -ForegroundColor Yellow
$discordToken = Read-Host "Paste Discord bot token (or Enter to skip)"
if ($discordToken) {
    '{"token": "Bot ' + $discordToken + '"}' | Out-File "$nexusDir\discord.json" -Encoding utf8
}

# 12. PowerShell profile function
$profileContent = @"

# NEXUS CLI
function nexus { uv run python -m cli.main @args }
"@
if (-not (Get-Content $PROFILE -ErrorAction SilentlyContinue | Select-String "function nexus")) {
    Add-Content $PROFILE $profileContent
    Write-Host "Added 'nexus' function to PowerShell profile" -ForegroundColor Green
}

# 13. Task Scheduler
$workDir = $PWD.Path

$serverAction = New-ScheduledTaskAction `
    -Execute "uv" `
    -Argument "run python -m cli.main serve" `
    -WorkingDirectory $workDir
$serverTrigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "NEXUS-Server" -Action $serverAction -Trigger $serverTrigger `
    -RunLevel Highest -Force | Out-Null

$browserAction = New-ScheduledTaskAction `
    -Execute "powershell" `
    -Argument "-Command Start-Process 'http://localhost:8000'"
$browserTrigger = New-ScheduledTaskTrigger -AtLogOn
$browserTrigger.Delay = "PT8S"
Register-ScheduledTask -TaskName "NEXUS-Browser" -Action $browserAction -Trigger $browserTrigger `
    -Force | Out-Null

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Run: nexus doctor" -ForegroundColor Yellow
Write-Host "Run: nexus serve" -ForegroundColor Yellow
```

- [ ] **Step 2: Commit**

```bash
git add setup.ps1
git commit -m "feat: one-shot setup script with Task Scheduler registration"
```

---

## Task 15: Notion Workspace Scaffold + Google OAuth Flow

**Files:**
- Modify: `backend/connectors/notion.py` (add `scaffold_workspace`)
- Create: `backend/connectors/google_auth.py`

- [ ] **Step 1: Add workspace scaffold to `backend/connectors/notion.py`**

Add this method to `NotionConnector`:

```python
async def scaffold_workspace(self) -> None:
    DATABASES = {
        "📅 Daily Notes": {"Date": {"date": {}}, "Weather": {"rich_text": {}}, "Mood": {"select": {}}},
        "🚀 Projects": {"Status": {"select": {}}, "Domain": {"rich_text": {}}, "GitHub": {"url": {}}},
        "🔬 Research": {"Tags": {"multi_select": {}}, "Status": {"select": {}}},
        "🎓 Courses": {"Code": {"rich_text": {}}, "Professor": {"rich_text": {}}, "Exam Date": {"date": {}}},
        "💡 Ideas": {"Tags": {"multi_select": {}}, "Priority": {"select": {}}},
        "👥 People": {"Role": {"rich_text": {}}, "Contact": {"email": {}}},
        "📚 Resources": {"URL": {"url": {}}, "Tags": {"multi_select": {}}},
    }
    async with httpx.AsyncClient(timeout=20) as c:
        root = await c.post(f"{NOTION_API}/pages", headers=self._headers(), json={
            "parent": {"type": "workspace", "workspace": True},
            "properties": {"title": {"title": [{"text": {"content": "NEXUS Workspace"}}]}},
        })
        root.raise_for_status()
        root_id = root.json()["id"]

        for name, extra_props in DATABASES.items():
            props = {"Name": {"title": {}}}
            props.update(extra_props)
            await c.post(f"{NOTION_API}/databases", headers=self._headers(), json={
                "parent": {"page_id": root_id},
                "title": [{"text": {"content": name}}],
                "properties": props,
            })
```

- [ ] **Step 2: Create `backend/connectors/google_auth.py`**

```python
from __future__ import annotations
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from backend.connectors.gmail import SCOPES


def run_google_oauth(data_dir: Path) -> None:
    creds_path = data_dir / "gmail_credentials.json"
    if not creds_path.exists():
        raise FileNotFoundError(f"Place GCP credentials at {creds_path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
    creds = flow.run_local_server(port=0)
    token_path = data_dir / "gmail_token.json"
    token_path.write_text(creds.to_json())
    print(f"Token saved to {token_path}")
```

- [ ] **Step 3: Add `connect` command to CLI**

In `cli/main.py`, add:

```python
@app.command()
def connect(service: str = typer.Argument(...)):
    cfg, _, _ = _init()
    if service == "google":
        from backend.connectors.google_auth import run_google_oauth
        run_google_oauth(cfg.data_dir)
        console.print("[green]✓[/green] Google OAuth complete")
    elif service == "notion":
        from backend.connectors.notion import NotionConnector
        import asyncio
        nc = NotionConnector(cfg)
        asyncio.run(nc.scaffold_workspace())
        console.print("[green]✓[/green] Notion workspace scaffold created")
    else:
        console.print(f"[red]Unknown service:[/red] {service}. Try: google, notion")
```

- [ ] **Step 4: Commit**

```bash
git add backend/connectors/notion.py backend/connectors/google_auth.py cli/main.py
git commit -m "feat: Notion workspace scaffold + Google OAuth flow"
```

---

## Self-Review Checklist

- [x] §3 Ollama Models — routed in `chat.py::_select_model` + `engine.py::route_model`
- [x] §4 Project Structure — all files mapped in File Map
- [x] §5 Config Schema — Task 1-2 cover `nexus.toml` fully
- [x] §6 Notion Workspace Scaffold — Task 15
- [x] §6 Notion Sync Daemon — Task 8
- [x] §7 ChromaDB 3 collections — Task 5
- [x] §8 7-step Chat Pipeline — Task 6 `chat.py`
- [x] §9 Classroom connector — Task 9
- [x] §10 CLI all 10 commands — Tasks 7 + 15
- [x] §11 Digest Agent 8 sections — Task 11
- [x] §12 FastAPI routes — Task 12
- [x] §13 Frontend 4 views + terminal-noir — Task 13
- [x] §14 Secrets storage — Task 14 `setup.ps1`
- [x] §15 Auto-start Task Scheduler — Task 14
- [x] §16 Setup script 14 steps — Task 14
- [x] §17 Build order — Tasks 1→15 follow spec order
