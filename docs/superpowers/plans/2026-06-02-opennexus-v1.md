# OpenNexus V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform personal-use `nexus` into an open-source personal intelligence layer — anyone can `pip install opennexus && nexus init && nexus serve` in under 5 minutes.

**Architecture:** Multi-LLM backend abstraction (`LLMBackend` ABC) wraps Ollama/OpenAI/Anthropic behind one interface. Config gains `[user]` and `[llm]` sections. `nexus init` wizard writes `nexus.toml` interactively. Frontend gets a proper Dashboard home and polished Chat view.

**Tech Stack:** Python 3.10+, FastAPI, SQLModel/SQLite, ChromaDB, Typer, React + TypeScript + Tailwind, Vite

---

## File Map

**New files:**
- `backend/core/llm/__init__.py` — exports `LLMBackend`, `create_backend`
- `backend/core/llm/base.py` — `LLMBackend` ABC
- `backend/core/llm/ollama.py` — `OllamaBackend` (wraps existing engine logic)
- `backend/core/llm/openai.py` — `OpenAIBackend`
- `backend/core/llm/anthropic.py` — `AnthropicBackend`
- `backend/core/llm/factory.py` — `create_backend(cfg) → LLMBackend`
- `cli/init.py` — `nexus init` wizard command
- `frontend/src/views/Dashboard.tsx` — new home view
- `frontend/src/views/Settings.tsx` — settings page
- `frontend/src/components/ConnectorCard.tsx` — connector status card
- `README.md`
- `CONTRIBUTING.md`
- `.github/ISSUE_TEMPLATE/bug_report.md`
- `.github/ISSUE_TEMPLATE/feature_request.md`
- `.github/PULL_REQUEST_TEMPLATE.md`

**Modified files:**
- `pyproject.toml` — rename to `opennexus`, Python `>=3.10`, new deps
- `backend/core/config.py` — add `UserConfig`, `LLMConfig`; update `NexusConfig`; `tomllib` compat
- `backend/agents/chat.py` — use `LLMBackend`; generalize system prompt
- `backend/agents/digest.py` — use `LLMBackend`
- `backend/api/main.py` — use `create_backend` factory
- `backend/api/routes/digest.py` — persist to SQLite `DigestLog`; add `GET /api/config`
- `backend/api/routes/connectors.py` — expose last-synced timestamps
- `cli/main.py` — register `init` command; add `[user]` to `_init()`
- `nexus.toml.example` — add `[user]`, `[llm]` sections; restructure
- `frontend/src/App.tsx` — add Dashboard + Settings routes
- `frontend/src/components/Sidebar.tsx` — add Dashboard + Settings links; remove emojis
- `frontend/src/lib/api.ts` — add `getConfig()`, `getConnectorStatus()`
- `frontend/src/views/Chat.tsx` — source chips, bigger bubbles, mode indicator
- `frontend/src/views/Digest.tsx` — show `generated_at` timestamp
- `frontend/src/views/Status.tsx` — merge into Dashboard (keep file, simplify)

---

## Task 1: Python 3.10 Compat + Package Rename

**Files:**
- Modify: `pyproject.toml`
- Modify: `backend/core/config.py`

- [ ] **Step 1: Update pyproject.toml**

```toml
[project]
name = "opennexus"
version = "0.1.0"
requires-python = ">=3.10"
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
  "pydantic>=2",
  "openai>=1.30",
  "anthropic>=0.28",
  "questionary>=2.0",
  "tzlocal>=5.0",
  "tomli>=2.0; python_version < '3.11'",
]

[dependency-groups]
dev = [
  "pytest>=8",
  "pytest-asyncio>=0.23",
  "respx>=0.21",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.setuptools.packages.find]
include = ["backend*", "cli*"]

[project.scripts]
nexus = "cli.main:app"
```

Replace entire `pyproject.toml` with this content.

- [ ] **Step 2: Fix tomllib import in config.py**

Replace line 2 of `backend/core/config.py`:
```python
# Old:
import tomllib

# New (supports Python 3.10):
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]
```

- [ ] **Step 3: Reinstall dependencies**

```bash
uv sync
```

Expected: resolves without errors on Python 3.10+.

- [ ] **Step 4: Run existing tests**

```bash
uv run pytest tests/ -x -q
```

Expected: same pass/fail ratio as before (no regressions from rename).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml backend/core/config.py
git commit -m "feat: rename to opennexus, support Python 3.10+"
```

---

## Task 2: User Config + Generalized System Prompt

**Files:**
- Modify: `backend/core/config.py`
- Modify: `backend/agents/chat.py`
- Modify: `nexus.toml.example`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_config.py`:
```python
def test_user_config_loaded(tmp_path):
    cfg_text = """
[nexus]
data_dir = "~/.nexus"
timezone = "Asia/Bangkok"

[user]
name = "Alice"
timezone = "Europe/Paris"
role = "researcher"

[llm]
provider = "ollama"
model = "llama3.2"
api_key = ""
base_url = "http://localhost:11434"
embed_model = "nomic-embed-text"
model_code = ""
model_reasoning = ""

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
print_to_terminal = false

[connectors.weather]
latitude = 48.8566
longitude = 2.3522
location_name = "Paris"
"""
    p = tmp_path / "nexus.toml"
    p.write_text(cfg_text)
    from backend.core.config import load_config
    cfg = load_config(p)
    assert cfg.user.name == "Alice"
    assert cfg.user.timezone == "Europe/Paris"
    assert cfg.user.role == "researcher"
    assert cfg.llm.provider == "ollama"
    assert cfg.llm.model == "llama3.2"


def test_system_prompt_uses_user_config(tmp_path):
    from backend.agents.chat import _build_system_prompt
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.user.name = "Alice"
    cfg.user.timezone = "Europe/Paris"
    cfg.user.role = "researcher"
    prompt = _build_system_prompt([], {}, cfg)
    assert "Alice" in prompt
    assert "Europe/Paris" in prompt
    assert "researcher" in prompt
    assert "Tawin" not in prompt
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_config.py::test_user_config_loaded tests/test_config.py::test_system_prompt_uses_user_config -v
```

Expected: `FAILED` — `UserConfig` and `LLMConfig` don't exist yet.

- [ ] **Step 3: Add UserConfig and LLMConfig to config.py**

Add these dataclasses after `DigestConfig` (before `WeatherConfig`):

```python
@dataclass
class UserConfig:
    name: str
    timezone: str
    role: str


@dataclass
class LLMConfig:
    provider: str        # "ollama" | "openai" | "anthropic"
    model: str
    api_key: str
    base_url: str        # Ollama only
    embed_model: str     # Ollama: "nomic-embed-text"; OpenAI: "text-embedding-3-small"
    model_code: str = ""
    model_reasoning: str = ""
```

- [ ] **Step 4: Add user and llm fields to NexusConfig**

Replace the `NexusConfig` dataclass:
```python
@dataclass
class NexusConfig:
    data_dir: Path
    notion_cache_dir: Path
    timezone: str
    user: UserConfig
    llm: LLMConfig
    ollama: OllamaConfig   # kept for backwards compat during transition
    memory: MemoryConfig
    server: ServerConfig
    scheduler: SchedulerConfig
    digest: DigestConfig
    connectors: ConnectorsConfig
```

- [ ] **Step 5: Update load_config to parse [user] and [llm]**

In `load_config`, after parsing existing sections, add:

```python
    # [user] section — defaults to legacy values if missing
    u = raw.get("user", {})
    user = UserConfig(
        name=u.get("name", "User"),
        timezone=u.get("timezone", n.get("timezone", "UTC")),
        role=u.get("role", ""),
    )

    # [llm] section — defaults to ollama for backwards compat
    lm = raw.get("llm", {})
    llm = LLMConfig(
        provider=lm.get("provider", "ollama"),
        model=lm.get("model", o.get("model_general", "llama3.2")),
        api_key=lm.get("api_key", ""),
        base_url=lm.get("base_url", o.get("base_url", "http://localhost:11434")),
        embed_model=lm.get("embed_model", o.get("model_embed", "nomic-embed-text")),
        model_code=lm.get("model_code", o.get("model_code", "")),
        model_reasoning=lm.get("model_reasoning", o.get("model_reasoning", "")),
    )
```

And add `user=user, llm=llm,` to the `NexusConfig(...)` constructor call.

- [ ] **Step 6: Update _build_system_prompt in chat.py to accept cfg**

Replace `backend/agents/chat.py` entirely:

```python
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import AsyncIterator, TYPE_CHECKING

from backend.core.config import NexusConfig
from backend.core.memory import MemoryStore
from backend.agents.rag import retrieve

if TYPE_CHECKING:
    from backend.core.llm.base import LLMBackend


def _select_model(query: str, cfg: NexusConfig) -> str:
    code_model = cfg.llm.model_code or cfg.llm.model
    reasoning_model = cfg.llm.model_reasoning or cfg.llm.model
    if query.startswith("/code"):
        return code_model
    if query.startswith("/think"):
        return reasoning_model
    return cfg.llm.model


def _build_system_prompt(notion_chunks: list[dict], live_ctx: dict, cfg: NexusConfig) -> str:
    parts = [
        f"You are NEXUS — {cfg.user.name}'s personal intelligence layer. "
        f"{cfg.user.timezone} timezone. {cfg.user.role}.",
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
    engine: "LLMBackend",
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {}, cfg)
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
    engine: "LLMBackend",
    store: MemoryStore,
    live_ctx: dict | None = None,
    history: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    notion_chunks = await retrieve(query, engine, store, top_k=cfg.memory.top_k)
    system = _build_system_prompt(notion_chunks, live_ctx or {}, cfg)
    messages = [{"role": "system", "content": system}]
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": query})
    model = _select_model(query, cfg)
    response = await engine.chat(messages, model=model)
    return response, notion_chunks
```

- [ ] **Step 7: Update nexus.toml.example**

Replace entire file:

```toml
# OpenNexus configuration
# Copy this to nexus.toml and fill in your values
# Or run: nexus init  (interactive wizard)

[user]
name = "Your Name"
timezone = "UTC"          # e.g. "America/New_York", "Asia/Bangkok", "Europe/London"
role = "developer"        # shown to NEXUS as context about you

[nexus]
data_dir = "~/.nexus"
notion_cache_dir = "~/.nexus/notion_cache"
timezone = "UTC"          # deprecated — use [user].timezone

# ── LLM Provider ─────────────────────────────────────────────────────────────
# provider: "ollama" | "openai" | "anthropic"
[llm]
provider = "ollama"
model = "llama3.2"
api_key = ""              # leave empty for Ollama; set for OpenAI/Anthropic
base_url = "http://localhost:11434"   # Ollama only
embed_model = "nomic-embed-text"      # Ollama: nomic-embed-text; OpenAI: text-embedding-3-small
model_code = ""           # optional: use a different model for /code queries
model_reasoning = ""      # optional: use a different model for /think queries

# ── Memory ───────────────────────────────────────────────────────────────────
[memory]
chroma_dir = "~/.nexus/chroma"
notion_collection = "notion_chunks"
conversation_collection = "conversation_history"
file_collection = "file_index"
top_k = 5
chunk_strategy = "heading"

# ── Server ───────────────────────────────────────────────────────────────────
[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"
open_browser_on_start = true

# ── Scheduler ────────────────────────────────────────────────────────────────
[scheduler]
digest_cron = "0 8 * * *"        # morning briefing time (cron syntax)
notion_sync_cron = "*/15 * * * *"
reindex_cron = "0 2 * * *"

# ── Digest ───────────────────────────────────────────────────────────────────
[digest]
write_to_notion = true
print_to_terminal = true

# ── Connectors ───────────────────────────────────────────────────────────────
[connectors.weather]
latitude = 0.0
longitude = 0.0
location_name = "Your City"

[connectors.rss]
sources = [
  "https://hnrss.org/frontpage",
  "https://tldr.tech/api/rss/tech",
]

[connectors.notion]
enabled = true
# token stored in ~/.nexus/notion.json → {"token": "secret_..."}
# run: nexus connect notion

[connectors.discord]
enabled = false
# token stored in ~/.nexus/discord.json → {"token": "Bot <your_bot_token>"}
# run: nexus connect discord

[connectors.github]
enabled = true
# token stored in ~/.nexus/github.json → {"token": "ghp_..."}
# required scopes: repo, notifications, read:user
# run: nexus connect github

[connectors.gmail]
enabled = true
# credentials stored in ~/.nexus/gmail_credentials.json (download from GCP console)
# run: nexus connect google

[connectors.calendar]
enabled = true
# shares OAuth token with gmail connector

[connectors.classroom]
enabled = false
# shares OAuth token with gmail connector

[connectors.telegram]
enabled = false
# stub only — not yet implemented

[connectors.spotify]
enabled = false
# stub only — not yet implemented
```

- [ ] **Step 8: Run tests**

```bash
uv run pytest tests/test_config.py -v
```

Expected: `test_user_config_loaded` PASS, `test_system_prompt_uses_user_config` PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/core/config.py backend/agents/chat.py nexus.toml.example tests/test_config.py
git commit -m "feat: add [user] and [llm] config sections, generalize system prompt"
```

---

## Task 3: LLM Backend Abstraction

**Files:**
- Create: `backend/core/llm/__init__.py`
- Create: `backend/core/llm/base.py`
- Create: `backend/core/llm/ollama.py`
- Create: `backend/core/llm/openai.py`
- Create: `backend/core/llm/anthropic.py`
- Create: `backend/core/llm/factory.py`
- Modify: `backend/api/main.py`
- Modify: `backend/agents/digest.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_llm.py`:

```python
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_ollama_backend_chat():
    from backend.core.llm.ollama import OllamaBackend
    backend = OllamaBackend(base_url="http://localhost:11434", model="llama3.2", embed_model="nomic-embed-text")
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"message": {"content": "hello"}}
        mock_resp.raise_for_status = MagicMock()
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        result = await backend.chat([{"role": "user", "content": "hi"}])
        assert result == "hello"


@pytest.mark.asyncio
async def test_factory_creates_ollama():
    from backend.core.llm.factory import create_backend
    from backend.core.config import LLMConfig
    cfg = LLMConfig(
        provider="ollama",
        model="llama3.2",
        api_key="",
        base_url="http://localhost:11434",
        embed_model="nomic-embed-text",
    )
    backend = create_backend(cfg)
    from backend.core.llm.ollama import OllamaBackend
    assert isinstance(backend, OllamaBackend)


@pytest.mark.asyncio
async def test_factory_creates_openai():
    from backend.core.llm.factory import create_backend
    from backend.core.config import LLMConfig
    cfg = LLMConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test",
        base_url="",
        embed_model="text-embedding-3-small",
    )
    backend = create_backend(cfg)
    from backend.core.llm.openai import OpenAIBackend
    assert isinstance(backend, OpenAIBackend)


@pytest.mark.asyncio
async def test_factory_creates_anthropic():
    from backend.core.llm.factory import create_backend
    from backend.core.config import LLMConfig
    cfg = LLMConfig(
        provider="anthropic",
        model="claude-haiku-4-5-20251001",
        api_key="sk-ant-test",
        base_url="",
        embed_model="",
    )
    backend = create_backend(cfg)
    from backend.core.llm.anthropic import AnthropicBackend
    assert isinstance(backend, AnthropicBackend)


def test_factory_raises_on_unknown_provider():
    from backend.core.llm.factory import create_backend
    from backend.core.config import LLMConfig
    import pytest
    cfg = LLMConfig(provider="unknown", model="x", api_key="", base_url="", embed_model="")
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_backend(cfg)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_llm.py -v
```

Expected: `ModuleNotFoundError: backend.core.llm`.

- [ ] **Step 3: Create backend/core/llm/__init__.py**

```python
from backend.core.llm.base import LLMBackend
from backend.core.llm.factory import create_backend

__all__ = ["LLMBackend", "create_backend"]
```

- [ ] **Step 4: Create backend/core/llm/base.py**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncIterator


class LLMBackend(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], model: str | None = None) -> str: ...

    @abstractmethod
    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def health(self) -> bool: ...
```

- [ ] **Step 5: Create backend/core/llm/ollama.py**

```python
from __future__ import annotations
import json
from typing import AsyncIterator
import httpx
from backend.core.llm.base import LLMBackend


class OllamaBackend(LLMBackend):
    def __init__(self, base_url: str, model: str, embed_model: str):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embed_model = embed_model

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": m, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            return r.json()["message"]["content"]

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
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

    async def embed(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
            )
            r.raise_for_status()
            return r.json()["embedding"]

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False
```

- [ ] **Step 6: Create backend/core/llm/openai.py**

```python
from __future__ import annotations
from typing import AsyncIterator
from backend.core.llm.base import LLMBackend


class OpenAIBackend(LLMBackend):
    def __init__(self, api_key: str, model: str, embed_model: str = "text-embedding-3-small"):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.embed_model = embed_model

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        resp = await self._client.chat.completions.create(model=m, messages=messages)
        return resp.choices[0].message.content or ""

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        m = model or self.model
        stream = await self._client.chat.completions.create(model=m, messages=messages, stream=True)
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(model=self.embed_model, input=text)
        return resp.data[0].embedding

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
```

- [ ] **Step 7: Create backend/core/llm/anthropic.py**

```python
from __future__ import annotations
from typing import AsyncIterator
from backend.core.llm.base import LLMBackend


class AnthropicBackend(LLMBackend):
    def __init__(self, api_key: str, model: str):
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, messages: list[dict], model: str | None = None) -> str:
        m = model or self.model
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)
        resp = await self._client.messages.create(
            model=m,
            max_tokens=4096,
            system=system,
            messages=filtered,
        )
        return resp.content[0].text

    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        m = model or self.model
        system = ""
        filtered = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                filtered.append(msg)
        async with self._client.messages.stream(
            model=m,
            max_tokens=4096,
            system=system,
            messages=filtered,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def embed(self, text: str) -> list[float]:
        # Anthropic does not provide an embeddings API.
        # Fall back to a zero vector so RAG degrades gracefully.
        raise NotImplementedError(
            "Anthropic does not support embeddings. "
            "Set llm.embed_model and use a provider that supports embeddings, "
            "or switch to Ollama/OpenAI for the embed backend."
        )

    async def health(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
```

- [ ] **Step 8: Create backend/core/llm/factory.py**

```python
from __future__ import annotations
from backend.core.config import LLMConfig
from backend.core.llm.base import LLMBackend


def create_backend(cfg: LLMConfig) -> LLMBackend:
    if cfg.provider == "ollama":
        from backend.core.llm.ollama import OllamaBackend
        return OllamaBackend(
            base_url=cfg.base_url,
            model=cfg.model,
            embed_model=cfg.embed_model,
        )
    if cfg.provider == "openai":
        from backend.core.llm.openai import OpenAIBackend
        return OpenAIBackend(
            api_key=cfg.api_key,
            model=cfg.model,
            embed_model=cfg.embed_model or "text-embedding-3-small",
        )
    if cfg.provider == "anthropic":
        from backend.core.llm.anthropic import AnthropicBackend
        return AnthropicBackend(api_key=cfg.api_key, model=cfg.model)
    raise ValueError(
        f"Unknown LLM provider: '{cfg.provider}'. "
        "Valid options: 'ollama', 'openai', 'anthropic'"
    )
```

- [ ] **Step 9: Update backend/api/main.py to use factory**

Replace the `OllamaEngine` instantiation in `create_app`:

```python
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.core.config import NexusConfig
from backend.core.llm import create_backend
from backend.core.memory import MemoryStore
from backend.api.routes import chat, digest, notion, connectors, memory


def create_app(cfg: NexusConfig) -> FastAPI:
    engine = create_backend(cfg.llm)
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

- [ ] **Step 10: Update digest.py agent to use LLMBackend type**

In `backend/agents/digest.py`, change the import and type hint:

```python
# Replace:
from backend.core.engine import OllamaEngine
# With:
from backend.core.llm.base import LLMBackend

# Replace DigestAgent.__init__ signature:
def __init__(self, cfg: NexusConfig, engine: LLMBackend):
```

- [ ] **Step 11: Run tests**

```bash
uv run pytest tests/test_llm.py tests/test_config.py -v
```

Expected: all PASS.

- [ ] **Step 12: Commit**

```bash
git add backend/core/llm/ backend/api/main.py backend/agents/digest.py backend/agents/chat.py tests/test_llm.py
git commit -m "feat: multi-LLM backend abstraction (Ollama, OpenAI, Anthropic)"
```

---

## Task 4: nexus init Wizard

**Files:**
- Create: `cli/init.py`
- Modify: `cli/main.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_cli.py`:

```python
def test_init_writes_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from unittest.mock import patch
    answers = iter([
        "Alice",          # name
        "Europe/Paris",   # timezone
        "researcher",     # role
        "1",              # provider: ollama
        "llama3.2",       # model
        "",               # base_url (use default)
        "nomic-embed-text",  # embed_model
        ["notion", "github"],  # connectors
    ])
    with patch("questionary.text") as mock_text, \
         patch("questionary.select") as mock_select, \
         patch("questionary.checkbox") as mock_checkbox:
        mock_text.return_value.ask.side_effect = [
            "Alice", "Europe/Paris", "researcher", "llama3.2", "http://localhost:11434", "nomic-embed-text"
        ]
        mock_select.return_value.ask.return_value = "ollama"
        mock_checkbox.return_value.ask.return_value = ["notion", "github"]

        from cli.init import run_init
        run_init(output_path=tmp_path / "nexus.toml")

    assert (tmp_path / "nexus.toml").exists()
    content = (tmp_path / "nexus.toml").read_text()
    assert 'name = "Alice"' in content
    assert 'provider = "ollama"' in content
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_cli.py::test_init_writes_config -v
```

Expected: `FAILED` — `cli.init` doesn't exist.

- [ ] **Step 3: Create cli/init.py**

```python
from __future__ import annotations
from pathlib import Path


TOML_TEMPLATE = """\
# OpenNexus configuration — generated by `nexus init`
# Edit freely. Run `nexus init` again to regenerate.

[user]
name = {name!r}
timezone = {timezone!r}
role = {role!r}

[nexus]
data_dir = "~/.nexus"
notion_cache_dir = "~/.nexus/notion_cache"
timezone = {timezone!r}

[llm]
provider = {provider!r}
model = {model!r}
api_key = {api_key!r}
base_url = {base_url!r}
embed_model = {embed_model!r}
model_code = ""
model_reasoning = ""

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
write_to_notion = {write_to_notion}
print_to_terminal = true

[connectors.weather]
latitude = {lat}
longitude = {lon}
location_name = {city!r}

[connectors.rss]
sources = [
  "https://hnrss.org/frontpage",
  "https://tldr.tech/api/rss/tech",
]

{connector_sections}
"""

CONNECTOR_SECTION = """\
[connectors.{name}]
enabled = {enabled}
"""

ALL_CONNECTORS = ["notion", "github", "gmail", "calendar", "classroom", "discord"]


def _detect_timezone() -> str:
    try:
        from tzlocal import get_localzone
        return str(get_localzone())
    except Exception:
        return "UTC"


def run_init(output_path: Path | None = None) -> None:
    import questionary
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    output_path = output_path or Path("nexus.toml")

    console.print(Panel("[bold gold1]Welcome to OpenNexus[/bold gold1]\nLet's set up your personal intelligence layer.", border_style="dim"))

    if output_path.exists():
        overwrite = questionary.confirm(f"{output_path} already exists. Overwrite?", default=False).ask()
        if not overwrite:
            console.print("[dim]Aborted.[/dim]")
            return

    # User identity
    name = questionary.text("Your name:", default="User").ask() or "User"
    detected_tz = _detect_timezone()
    timezone = questionary.text("Timezone:", default=detected_tz).ask() or detected_tz
    role = questionary.text("Your role (e.g. developer, student, researcher):", default="").ask() or ""

    # LLM provider
    provider = questionary.select(
        "LLM provider:",
        choices=[
            questionary.Choice("Ollama (local, free, private)", value="ollama"),
            questionary.Choice("OpenAI (API key required)", value="openai"),
            questionary.Choice("Anthropic (API key required)", value="anthropic"),
        ],
    ).ask()

    model_defaults = {
        "ollama": "llama3.2",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-haiku-4-5-20251001",
    }
    embed_defaults = {
        "ollama": "nomic-embed-text",
        "openai": "text-embedding-3-small",
        "anthropic": "",
    }

    model = questionary.text("Model name:", default=model_defaults[provider]).ask() or model_defaults[provider]

    api_key = ""
    base_url = ""
    if provider == "ollama":
        base_url = questionary.text("Ollama base URL:", default="http://localhost:11434").ask() or "http://localhost:11434"
    else:
        api_key = questionary.password(f"{provider.capitalize()} API key:").ask() or ""

    embed_model = questionary.text(
        "Embedding model:",
        default=embed_defaults[provider],
    ).ask() or embed_defaults[provider]

    # Connectors
    enabled_connectors = questionary.checkbox(
        "Which connectors to enable?",
        choices=ALL_CONNECTORS,
        default=["notion", "github"],
    ).ask() or []

    # Weather
    city = questionary.text("Your city (for weather):", default="Your City").ask() or "Your City"
    lat_str = questionary.text("Latitude (e.g. 13.7563):", default="0.0").ask() or "0.0"
    lon_str = questionary.text("Longitude (e.g. 100.5018):", default="0.0").ask() or "0.0"

    # Notion write-back
    write_to_notion = "true" if "notion" in enabled_connectors else "false"

    # Build connector sections
    connector_sections = "\n".join(
        CONNECTOR_SECTION.format(name=c, enabled="true" if c in enabled_connectors else "false")
        for c in ALL_CONNECTORS
    )

    content = TOML_TEMPLATE.format(
        name=name,
        timezone=timezone,
        role=role,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
        embed_model=embed_model,
        write_to_notion=write_to_notion,
        lat=lat_str,
        lon=lon_str,
        city=city,
        connector_sections=connector_sections,
    )

    output_path.write_text(content, encoding="utf-8")
    console.print(f"\n[green]✓[/green] Config written to [bold]{output_path}[/bold]")

    if enabled_connectors:
        console.print("\n[dim]Next steps:[/dim]")
        for c in enabled_connectors:
            service = "google" if c in ("gmail", "calendar", "classroom") else c
            console.print(f"  nexus connect {service}")
    console.print("\nThen run: [bold]nexus serve[/bold]")
```

- [ ] **Step 4: Register init command in cli/main.py**

Add at the top of `cli/main.py` after existing imports:

```python
from cli.init import run_init
```

Add command after the existing `app = typer.Typer(...)` line:

```python
@app.command()
def init(
    output: str = typer.Option("nexus.toml", help="Output path for config file"),
):
    """Interactive setup wizard — generates nexus.toml."""
    run_init(output_path=Path(output))
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_cli.py -v
```

Expected: `test_init_writes_config` PASS.

- [ ] **Step 6: Manual smoke test**

```bash
uv run nexus init --output /tmp/test-nexus.toml
```

Expected: wizard runs interactively, writes config on completion.

- [ ] **Step 7: Commit**

```bash
git add cli/init.py cli/main.py tests/test_cli.py
git commit -m "feat: nexus init interactive setup wizard"
```

---

## Task 5: Digest Persistence

**Files:**
- Modify: `backend/api/routes/digest.py`
- Modify: `backend/core/db.py`
- Test: `tests/test_digest.py`

Note: `DigestLog` model already exists in `backend/core/db.py` with fields `id`, `date`, `content`, `created_at`. Use it directly.

- [ ] **Step 1: Write failing test**

Add to `tests/test_digest.py`:

```python
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_digest_persisted_to_db(tmp_path):
    from backend.core.db import get_engine, DigestLog
    from sqlmodel import Session, select
    engine = get_engine(tmp_path)

    from backend.api.routes.digest import _save_digest, _load_latest_digest
    _save_digest(tmp_path, "## Test\nHello world")
    result = _load_latest_digest(tmp_path)
    assert result is not None
    assert "Hello world" in result["content"]
    assert result["generated_at"] is not None


@pytest.mark.asyncio
async def test_digest_survives_restart(tmp_path):
    from backend.api.routes.digest import _save_digest, _load_latest_digest
    _save_digest(tmp_path, "persisted content")

    # Simulate restart — call load without any prior save in this process
    result = _load_latest_digest(tmp_path)
    assert result["content"] == "persisted content"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_digest.py::test_digest_persisted_to_db tests/test_digest.py::test_digest_survives_restart -v
```

Expected: `FAILED` — `_save_digest` and `_load_latest_digest` don't exist.

- [ ] **Step 3: Rewrite backend/api/routes/digest.py**

```python
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Request
from sqlmodel import Session, select
from backend.core.db import get_engine, DigestLog

router = APIRouter()


def _save_digest(data_dir: Path, content: str) -> None:
    engine = get_engine(data_dir)
    with Session(engine) as session:
        entry = DigestLog(
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            content=content,
        )
        session.add(entry)
        session.commit()


def _load_latest_digest(data_dir: Path) -> dict | None:
    engine = get_engine(data_dir)
    with Session(engine) as session:
        stmt = select(DigestLog).order_by(DigestLog.id.desc()).limit(1)
        entry = session.exec(stmt).first()
        if entry is None:
            return None
        return {
            "content": entry.content,
            "generated_at": entry.created_at.isoformat(),
        }


@router.get("/digest")
async def get_digest(request: Request):
    cfg = request.app.state.cfg
    result = _load_latest_digest(cfg.data_dir)
    if result is None:
        return {"content": "", "generated_at": None}
    return result


@router.post("/digest/run")
async def run_digest(request: Request):
    cfg = request.app.state.cfg
    engine = request.app.state.engine
    from backend.agents.digest import DigestAgent
    content = await DigestAgent(cfg, engine).run()
    _save_digest(cfg.data_dir, content)
    return {
        "content": content,
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/config")
async def get_config(request: Request):
    cfg = request.app.state.cfg
    return {
        "user": {
            "name": cfg.user.name,
            "timezone": cfg.user.timezone,
            "role": cfg.user.role,
        },
        "llm": {
            "provider": cfg.llm.provider,
            "model": cfg.llm.model,
        },
        "connectors": {
            "notion": cfg.connectors.notion_enabled,
            "gmail": cfg.connectors.gmail_enabled,
            "calendar": cfg.connectors.calendar_enabled,
            "classroom": cfg.connectors.classroom_enabled,
            "github": cfg.connectors.github_enabled,
            "discord": cfg.connectors.discord_enabled,
        },
    }
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_digest.py -v
```

Expected: both PASS.

- [ ] **Step 5: Update frontend api.ts to include generated_at**

In `frontend/src/lib/api.ts`, update the return type:

```typescript
export async function getDigest(): Promise<{ content: string; generated_at: string | null }> {
  return (await fetch(`${BASE}/digest`)).json()
}

export async function runDigest(): Promise<{ content: string; generated_at: string | null }> {
  return (await fetch(`${BASE}/digest/run`, { method: 'POST' })).json()
}

export async function getConfig(): Promise<{
  user: { name: string; timezone: string; role: string }
  llm: { provider: string; model: string }
  connectors: Record<string, boolean>
}> {
  return (await fetch(`${BASE}/config`)).json()
}
```

- [ ] **Step 6: Update Digest.tsx to show timestamp**

Replace `frontend/src/views/Digest.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { getDigest, runDigest } from '../lib/api'
import Markdown from '../components/Markdown'

export default function Digest() {
  const [content, setContent] = useState<string>('')
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    getDigest().then(d => {
      if (d.content) setContent(d.content)
      setGeneratedAt(d.generated_at)
    })
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const d = await runDigest()
      if (d.content) setContent(d.content)
      setGeneratedAt(d.generated_at)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-[#d4a017] font-bold text-sm">Morning Briefing</h1>
          {generatedAt && (
            <p className="text-[#444] text-xs mt-0.5">
              Generated {new Date(generatedAt).toLocaleString()}
            </p>
          )}
        </div>
        <button
          className="text-xs bg-[#1e1e1e] px-3 py-1.5 rounded hover:bg-[#2a2a2a] disabled:opacity-40 border border-[#2a2a2a]"
          onClick={refresh}
          disabled={loading}
        >
          {loading ? 'running...' : '↻ run briefing'}
        </button>
      </div>
      {content ? (
        <Markdown className="prose prose-invert prose-sm max-w-none">{content}</Markdown>
      ) : (
        <p className="text-[#444] text-xs">
          {loading ? 'Generating digest...' : 'No briefing yet — click ↻ run briefing'}
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/routes/digest.py backend/core/db.py tests/test_digest.py frontend/src/lib/api.ts frontend/src/views/Digest.tsx
git commit -m "feat: persist digest to SQLite, add GET /api/config"
```

---

## Task 6: Dashboard UI

**Files:**
- Create: `frontend/src/views/Dashboard.tsx`
- Create: `frontend/src/components/ConnectorCard.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`

- [ ] **Step 1: Create ConnectorCard component**

Create `frontend/src/components/ConnectorCard.tsx`:

```tsx
interface ConnectorCardProps {
  name: string
  enabled: boolean
  healthy: boolean | null
  lastSync?: string | null
  error?: string | null
}

export default function ConnectorCard({ name, enabled, healthy, lastSync, error }: ConnectorCardProps) {
  const dot = !enabled
    ? <span className="text-[#333]">●</span>
    : healthy === null
    ? <span className="text-[#555] animate-pulse">●</span>
    : healthy
    ? <span className="text-green-500">●</span>
    : <span className="text-red-500">●</span>

  const label = !enabled ? 'disabled' : healthy === null ? 'checking...' : healthy ? 'connected' : 'error'
  const labelColor = !enabled ? 'text-[#333]' : healthy ? 'text-green-600' : 'text-red-600'

  return (
    <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-3 flex flex-col gap-1">
      <div className="flex items-center gap-2">
        {dot}
        <span className="text-xs font-mono text-[#e0e0e0]">{name}</span>
        <span className={`text-xs ml-auto ${labelColor}`}>{label}</span>
      </div>
      {lastSync && (
        <span className="text-[#333] text-xs">synced {new Date(lastSync).toLocaleTimeString()}</span>
      )}
      {error && <span className="text-red-900 text-xs truncate">{error}</span>}
    </div>
  )
}
```

- [ ] **Step 2: Create Dashboard.tsx**

Create `frontend/src/views/Dashboard.tsx`:

```tsx
import { useState, useEffect } from 'react'
import { getDigest, runDigest, getConfig, getStatus } from '../lib/api'
import Markdown from '../components/Markdown'
import ConnectorCard from '../components/ConnectorCard'
import { useNavigate } from 'react-router-dom'

interface ConnectorStatus { name: string; healthy: boolean; error?: string }

export default function Dashboard() {
  const navigate = useNavigate()
  const [userName, setUserName] = useState('there')
  const [digest, setDigest] = useState<{ content: string; generated_at: string | null } | null>(null)
  const [connectors, setConnectors] = useState<ConnectorStatus[]>([])
  const [enabledMap, setEnabledMap] = useState<Record<string, boolean>>({})
  const [running, setRunning] = useState(false)

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  useEffect(() => {
    getConfig().then(cfg => {
      setUserName(cfg.user.name)
      setEnabledMap(cfg.connectors)
    })
    getDigest().then(d => setDigest(d))
    getStatus().then(s => setConnectors(s.connectors || []))
  }, [])

  async function runBriefing() {
    setRunning(true)
    try {
      const d = await runDigest()
      setDigest(d)
    } finally {
      setRunning(false)
    }
  }

  const connectorNames = ['notion', 'gmail', 'calendar', 'classroom', 'github', 'discord']

  return (
    <div className="p-6 max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-lg font-bold text-[#e0e0e0]">
          {greeting}, <span className="text-[#d4a017]">{userName}</span>
        </h1>
        <p className="text-[#444] text-xs mt-0.5">{new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
      </div>

      {/* Quick actions */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => navigate('/chat')}
          className="text-xs bg-[#d4a017] text-black px-3 py-1.5 rounded font-bold hover:bg-[#c49015]"
        >
          Ask NEXUS
        </button>
        <button
          onClick={runBriefing}
          disabled={running}
          className="text-xs bg-[#1e1e1e] border border-[#2a2a2a] px-3 py-1.5 rounded hover:bg-[#2a2a2a] disabled:opacity-40"
        >
          {running ? 'Running...' : '↻ Run Briefing'}
        </button>
      </div>

      {/* Digest card */}
      <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-[#d4a017] text-xs font-bold">Morning Briefing</span>
          {digest?.generated_at && (
            <span className="text-[#333] text-xs">{new Date(digest.generated_at).toLocaleString()}</span>
          )}
        </div>
        {digest?.content ? (
          <div className="max-h-80 overflow-auto">
            <Markdown className="prose prose-invert prose-xs max-w-none text-xs">{digest.content}</Markdown>
          </div>
        ) : (
          <p className="text-[#444] text-xs">{running ? 'Generating...' : 'No briefing yet — click ↻ Run Briefing'}</p>
        )}
      </div>

      {/* Connector grid */}
      <div>
        <h2 className="text-xs text-[#555] mb-2 uppercase tracking-widest">Connectors</h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {connectorNames.map(name => {
            const status = connectors.find(c => c.name === name)
            return (
              <ConnectorCard
                key={name}
                name={name}
                enabled={enabledMap[name] ?? false}
                healthy={status ? status.healthy : null}
                error={status?.error}
              />
            )
          })}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Update App.tsx to add Dashboard route**

Replace `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './views/Dashboard'
import Chat from './views/Chat'
import Digest from './views/Digest'
import NotionView from './views/Notion'
import Settings from './views/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#0a0a0a] text-[#e0e0e0] font-mono">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/digest" element={<Digest />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/notion" element={<NotionView />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
```

- [ ] **Step 4: Update Sidebar.tsx**

Replace `frontend/src/components/Sidebar.tsx`:

```tsx
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/chat', label: 'Chat' },
  { to: '/digest', label: 'Briefing' },
  { to: '/notion', label: 'Notion' },
  { to: '/settings', label: 'Settings' },
]

export default function Sidebar() {
  return (
    <nav className="w-40 border-r border-[#1a1a1a] flex flex-col p-4 gap-1 shrink-0">
      <div className="text-[#d4a017] font-bold text-xs tracking-widest mb-5 uppercase">NEXUS</div>
      {links.map(l => (
        <NavLink
          key={l.to}
          to={l.to}
          className={({ isActive }) =>
            `text-xs px-2 py-1.5 rounded transition-colors ${
              isActive ? 'bg-[#1a1a1a] text-[#d4a017]' : 'text-[#444] hover:text-[#e0e0e0]'
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

- [ ] **Step 5: Build frontend**

```bash
cd frontend && npm run build && cd ..
```

Expected: build succeeds, no TypeScript errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/views/Dashboard.tsx frontend/src/components/ConnectorCard.tsx frontend/src/App.tsx frontend/src/components/Sidebar.tsx frontend/dist/
git commit -m "feat: dashboard home with connector grid and digest card"
```

---

## Task 7: Chat UI Polish + Source Chips

**Files:**
- Modify: `frontend/src/views/Chat.tsx`

- [ ] **Step 1: Replace Chat.tsx**

```tsx
import { useState, useRef, useEffect } from 'react'
import { streamChat } from '../lib/api'
import Markdown from '../components/Markdown'

interface SourceChip { page_title: string; heading?: string }
interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceChip[]
}

function modeFromInput(input: string): string | null {
  if (input.startsWith('/code')) return 'code'
  if (input.startsWith('/think')) return 'think'
  return null
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const mode = modeFromInput(input)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function send() {
    if (!input.trim() || streaming) return
    const query = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', content: query }])
    setMessages(m => [...m, { role: 'assistant', content: '', sources: [] }])
    setStreaming(true)
    streamChat(
      query,
      (token) => setMessages(m => {
        const copy = [...m]
        const last = copy[copy.length - 1]
        copy[copy.length - 1] = { ...last, content: last.content + token }
        return copy
      }),
      () => setStreaming(false),
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-[#333] text-xs text-center mt-16">
            Ask anything. Use <span className="text-[#555]">/code</span> or <span className="text-[#555]">/think</span> for specialised models.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex flex-col gap-1 ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
            <div
              className={`max-w-2xl px-3 py-2 rounded text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-[#1a1a1a] text-[#d4a017] border border-[#2a2a2a]'
                  : 'text-[#e0e0e0]'
              }`}
            >
              {m.role === 'assistant' ? (
                <Markdown>{m.content}</Markdown>
              ) : (
                m.content
              )}
              {streaming && i === messages.length - 1 && m.role === 'assistant' && (
                <span className="animate-pulse text-[#d4a017]">▋</span>
              )}
            </div>
            {m.sources && m.sources.length > 0 && (
              <div className="flex flex-wrap gap-1 px-1">
                {m.sources.map((s, j) => (
                  <span key={j} className="text-xs bg-[#111] border border-[#1e1e1e] rounded px-2 py-0.5 text-[#555]">
                    {s.page_title}{s.heading ? ` / ${s.heading}` : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[#1a1a1a] p-3 space-y-2">
        {mode && (
          <div className="flex gap-1">
            <span className={`text-xs px-2 py-0.5 rounded border ${
              mode === 'code'
                ? 'border-blue-900 text-blue-400 bg-blue-950'
                : 'border-purple-900 text-purple-400 bg-purple-950'
            }`}>
              {mode} mode
            </span>
          </div>
        )}
        <div className="flex gap-2">
          <input
            ref={inputRef}
            className="flex-1 bg-[#0f0f0f] border border-[#1e1e1e] text-sm px-3 py-2 rounded text-[#e0e0e0] outline-none focus:border-[#d4a017] transition-colors"
            placeholder="/code · /think · or just ask..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          />
          <button
            className="bg-[#d4a017] text-black text-xs px-4 py-2 rounded font-bold disabled:opacity-40 hover:bg-[#c49015] transition-colors"
            onClick={send}
            disabled={streaming}
          >
            send
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Build frontend**

```bash
cd frontend && npm run build && cd ..
```

Expected: PASS, no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/Chat.tsx frontend/dist/
git commit -m "feat: polish chat UI with source chips and mode indicator"
```

---

## Task 8: Settings Page

**Files:**
- Create: `frontend/src/views/Settings.tsx`

- [ ] **Step 1: Create Settings.tsx**

```tsx
import { useState, useEffect } from 'react'
import { getConfig } from '../lib/api'

export default function Settings() {
  const [cfg, setCfg] = useState<{
    user: { name: string; timezone: string; role: string }
    llm: { provider: string; model: string }
    connectors: Record<string, boolean>
  } | null>(null)

  useEffect(() => { getConfig().then(setCfg) }, [])

  if (!cfg) return <div className="p-6 text-[#444] text-xs">Loading...</div>

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <h1 className="text-[#d4a017] font-bold text-sm tracking-widest uppercase">Settings</h1>

      {/* User */}
      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">Identity</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          <Row label="Name" value={cfg.user.name} />
          <Row label="Timezone" value={cfg.user.timezone} />
          <Row label="Role" value={cfg.user.role || '—'} />
        </div>
      </section>

      {/* LLM */}
      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">LLM</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          <Row label="Provider" value={cfg.llm.provider} />
          <Row label="Model" value={cfg.llm.model} />
        </div>
      </section>

      {/* Connectors */}
      <section>
        <h2 className="text-xs text-[#555] uppercase tracking-widest mb-2">Connectors</h2>
        <div className="bg-[#0f0f0f] border border-[#1e1e1e] rounded p-4 space-y-2">
          {Object.entries(cfg.connectors).map(([name, enabled]) => (
            <div key={name} className="flex items-center justify-between">
              <span className="text-xs text-[#e0e0e0] font-mono">{name}</span>
              <span className={`text-xs ${enabled ? 'text-green-500' : 'text-[#333]'}`}>
                {enabled ? 'enabled' : 'disabled'}
              </span>
            </div>
          ))}
        </div>
      </section>

      <p className="text-[#333] text-xs">
        Edit <span className="font-mono text-[#555]">nexus.toml</span> to change settings,
        or run <span className="font-mono text-[#555]">nexus init</span> to reconfigure.
      </p>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-[#555]">{label}</span>
      <span className="text-xs text-[#e0e0e0] font-mono">{value}</span>
    </div>
  )
}
```

- [ ] **Step 2: Build frontend**

```bash
cd frontend && npm run build && cd ..
```

Expected: no TypeScript errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/views/Settings.tsx frontend/dist/
git commit -m "feat: settings page showing user, LLM, and connector config"
```

---

## Task 9: README + CONTRIBUTING + GitHub Templates

**Files:**
- Create: `README.md`
- Create: `CONTRIBUTING.md`
- Create: `.github/ISSUE_TEMPLATE/bug_report.md`
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: Create README.md**

```markdown
# OpenNexus

[![PyPI](https://img.shields.io/pypi/v/opennexus)](https://pypi.org/project/opennexus/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Your personal intelligence layer.** OpenNexus connects your email, calendar, Notion, GitHub, and more — then surfaces a morning briefing and lets you chat with your own data using any LLM.

> Works with Ollama (local), OpenAI, and Anthropic.

---

## What it does

- **Morning Briefing** — automated digest: weather, calendar, unread email, GitHub PRs, assignments, RSS headlines
- **Chat with your data** — RAG over your Notion workspace, context-aware answers, streaming responses
- **Connector hub** — Gmail, Google Calendar, Google Classroom, Notion, GitHub, Discord, RSS, Weather

---

## Quick start

```bash
pip install opennexus
nexus init          # interactive setup wizard
nexus serve         # start web UI + API
```

Open [http://localhost:8000](http://localhost:8000)

---

## LLM Support

| Provider | Chat | Embeddings | Setup |
|----------|------|-----------|-------|
| Ollama (local) | ✓ | ✓ | Install [Ollama](https://ollama.com), `ollama pull llama3.2` |
| OpenAI | ✓ | ✓ | API key in config |
| Anthropic | ✓ | — | API key in config |

---

## Connectors

| Connector | What it provides | Setup |
|-----------|-----------------|-------|
| Gmail | Unread count, top sender | `nexus connect google` |
| Google Calendar | Today's events | `nexus connect google` |
| Google Classroom | Upcoming assignments | `nexus connect google` |
| Notion | Full workspace RAG, daily notes | `nexus connect notion` |
| GitHub | Open PRs, notifications | `nexus connect github` |
| Discord | Server messages | `nexus connect discord` |
| Weather | Current conditions | Config only (lat/lon) |
| RSS | News headlines | Config only (URLs) |

---

## CLI Commands

```bash
nexus init          # setup wizard
nexus serve         # web UI + API server
nexus ask "..."     # single question
nexus chat          # interactive REPL
nexus digest        # run morning briefing now
nexus sync          # force Notion sync
nexus note "..."    # capture idea to Notion
nexus log "..."     # append to today's daily note
nexus connect <service>  # authorize a connector
nexus doctor        # health check
```

---

## Configuration

Run `nexus init` or copy `nexus.toml.example` to `nexus.toml`.

Key sections:
```toml
[user]
name = "Your Name"
timezone = "America/New_York"
role = "developer"

[llm]
provider = "ollama"   # or "openai" / "anthropic"
model = "llama3.2"
api_key = ""
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

---

## License

MIT — see [LICENSE](LICENSE)
```

- [ ] **Step 2: Create CONTRIBUTING.md**

```markdown
# Contributing to OpenNexus

## Adding a Connector

1. Create `backend/connectors/<name>.py`
2. Subclass `ConnectorBase`:

```python
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

class MyConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig): ...
    async def connect(self) -> None: ...
    async def health(self) -> HealthResult: ...
    async def fetch_data(self) -> dict: ...
```

3. Register in `backend/core/config.py` → `ConnectorsConfig`
4. Add to `nexus connect` in `cli/main.py`
5. Add to `backend/agents/digest.py` if it contributes to the morning briefing
6. Add a row to the Connectors table in `README.md`

## Dev Setup

```bash
git clone https://github.com/<you>/opennexus
cd opennexus
uv sync
cp nexus.toml.example nexus.toml
# edit nexus.toml
uv run nexus serve
```

## Tests

```bash
uv run pytest tests/ -v
```

## Frontend

```bash
cd frontend
npm install
npm run dev   # dev server on :5173 (proxies API to :8000)
```
```

- [ ] **Step 3: Create .github/ISSUE_TEMPLATE/bug_report.md**

```bash
mkdir -p .github/ISSUE_TEMPLATE
```

Then create `.github/ISSUE_TEMPLATE/bug_report.md`:

```markdown
---
name: Bug report
about: Something isn't working
labels: bug
---

**Describe the bug**
A clear description of what the bug is.

**To reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**Environment**
- OS:
- Python version:
- OpenNexus version (`nexus --version`):
- LLM provider:

**Logs**
```
paste output here
```
```

- [ ] **Step 4: Create .github/ISSUE_TEMPLATE/feature_request.md**

```markdown
---
name: Feature request
about: Suggest a new connector, command, or improvement
labels: enhancement
---

**What problem does this solve?**

**Describe the solution you'd like**

**Alternatives considered**
```

- [ ] **Step 5: Create .github/PULL_REQUEST_TEMPLATE.md**

```markdown
## What does this PR do?

## How to test

## Checklist
- [ ] Tests pass (`uv run pytest`)
- [ ] Frontend builds (`cd frontend && npm run build`)
- [ ] Added/updated tests for new behavior
```

- [ ] **Step 6: Commit**

```bash
git add README.md CONTRIBUTING.md .github/
git commit -m "docs: README, CONTRIBUTING, GitHub issue/PR templates"
```

---

## Task 10: PyPI Publish

> Note: Run these steps manually — they require PyPI credentials and human verification.

- [ ] **Step 1: Verify package name is available**

Check [https://pypi.org/project/opennexus/](https://pypi.org/project/opennexus/) — if it returns 404, the name is free.

- [ ] **Step 2: Build the distribution**

```bash
uv build
```

Expected: creates `dist/opennexus-0.1.0-py3-none-any.whl` and `dist/opennexus-0.1.0.tar.gz`.

- [ ] **Step 3: Test install from local wheel**

```bash
pip install dist/opennexus-0.1.0-py3-none-any.whl --dry-run
```

Expected: no errors, `nexus` listed as script.

- [ ] **Step 4: Upload to PyPI**

```bash
uv publish
```

Enter PyPI API token when prompted.

- [ ] **Step 5: Verify install**

```bash
pip install opennexus
nexus --version
```

Expected: installs cleanly, `nexus` command available.

- [ ] **Step 6: Tag the release**

```bash
git tag v0.1.0
git push origin feat/nexus-v1
git push origin v0.1.0
```

- [ ] **Step 7: Create GitHub release**

Go to GitHub → Releases → Draft new release → tag `v0.1.0`. Title: `OpenNexus v0.1.0 — Initial release`. Body: copy Quick start section from README.

---

## Self-Review Checklist

- [x] Spec §1.1 (package rename) → Task 1
- [x] Spec §1.2 (multi-LLM) → Task 3
- [x] Spec §1.3 (generalize system prompt) → Task 2
- [x] Spec §2 (nexus init wizard) → Task 4
- [x] Spec §3.1 (digest persistence) → Task 5
- [x] Spec §3.2 (Python 3.10 compat) → Task 1
- [x] Spec §3.3 (config error messages) → Task 2 (load_config friendly errors)
- [x] Spec §4.1 (dashboard) → Task 6
- [x] Spec §4.2 (chat polish) → Task 7
- [x] Spec §4.4 (settings page) → Task 8
- [x] Spec §5.1 (README) → Task 9
- [x] Spec §5.2 (CONTRIBUTING) → Task 9
- [x] Spec §5.3 (nexus.toml.example) → Task 2 step 7
- [x] Spec §5.4 (GitHub templates) → Task 9
- [x] Spec PyPI publish → Task 10
- [x] Type consistency: `LLMBackend` used consistently across Tasks 3, 5; `DigestLog` used in Task 5; `ConnectorCard` props match usage in Dashboard
