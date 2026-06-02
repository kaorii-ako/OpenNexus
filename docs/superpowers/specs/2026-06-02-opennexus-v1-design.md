# OpenNexus V1 Design Spec

**Date:** 2026-06-02  
**Status:** Approved  
**Goal:** Transform personal-use `nexus` into an open-source personal intelligence layer anyone can install, configure, and extend.  
**Target:** 5000+ GitHub stars, 1M+ PyPI downloads

---

## 1. Core Architecture Changes

### 1.1 Package Rename
- PyPI package: `nexus` → `opennexus`
  - CLI command: stays `nexus` (no breaking change for users)
  - `pyproject.toml` `name = "opennexus"`
  - Python requirement: `>=3.10` (was `>=3.13`)

### 1.2 Multi-LLM Engine

New `backend/core/llm/` module replaces direct `OllamaEngine` coupling:

```
backend/core/llm/
  __init__.py
  base.py        # LLMBackend ABC: chat(), stream_chat(), embed()
  ollama.py      # OllamaBackend — wraps existing OllamaEngine logic
  openai.py      # OpenAIBackend — openai SDK
  anthropic.py   # AnthropicBackend — anthropic SDK
  factory.py     # create_backend(cfg: LLMConfig) → LLMBackend
```

**`LLMBackend` ABC:**
```python
class LLMBackend(ABC):
    async def chat(self, messages: list[dict], model: str | None = None) -> str: ...
    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]: ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    async def health(self) -> bool: ...
```

**Config section:**
```toml
[llm]
provider = "ollama"   # "ollama" | "openai" | "anthropic"
model = "llama3.2"
api_key = ""          # empty for Ollama
base_url = "http://localhost:11434"  # Ollama only
embed_model = "nomic-embed-text"     # Ollama only; OpenAI uses text-embedding-3-small

# Optional model routing (all providers)
model_code = ""        # falls back to model if empty
model_reasoning = ""   # falls back to model if empty
```

`factory.py` creates the right backend from `cfg.llm.provider`. All existing code that calls `engine.chat()` / `engine.stream_chat()` / `engine.embed()` continues to work unchanged — only the import changes.

### 1.3 Generalized User Config

Remove hardcoded `"Tawin's personal intelligence layer. Bangkok timezone. Developer + student."` from `backend/agents/chat.py`.

New `[user]` config section:
```toml
[user]
name = "Tawin"
timezone = "Asia/Bangkok"
role = "developer + student"
```

System prompt becomes:
```python
f"You are NEXUS — {cfg.user.name}'s personal intelligence layer. {cfg.user.timezone} timezone. {cfg.user.role}."
```

---

## 2. Setup Wizard (`nexus init`)

New CLI command that runs once to generate `nexus.toml`. Replaces manual config editing.

**Flow:**
1. Prompt: name, timezone (auto-detect via `tzlocal`, allow override)
   2. Prompt: LLM provider (1=Ollama, 2=OpenAI, 3=Anthropic) + model + API key if needed
   3. Prompt: connectors to enable (multi-select checkbox via `InquirerPy` or `questionary`)
   4. Write `nexus.toml` to cwd
   5. Print next steps: `nexus connect <service>` for each enabled connector

**Implementation:** `cli/init.py` — new file, registered as `@app.command()` in `cli/main.py`.

**Dependencies added:** `questionary>=2.0` for interactive prompts, `tzlocal>=5.0` for timezone auto-detect.

**Guard:** If `nexus.toml` already exists, prompt to overwrite or abort.

---

## 3. Persistence + Reliability

### 3.1 Digest Persistence

**Problem:** `app.state.last_digest` lost on every restart.

**Fix:** New `DigestEntry` SQLModel:
```python
class DigestEntry(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    sources: str = ""   # JSON list of connector names that contributed
```

`GET /api/digest` → reads latest `DigestEntry` from SQLite.  
`POST /api/digest/run` → runs DigestAgent, writes new row, returns content.

### 3.2 Python 3.10 Compatibility

Audit and fix:
- `zoneinfo` → add `backports.zoneinfo` to dependencies with conditional import
  - `X | Y` type union syntax in function signatures → use `Optional[X]` or `Union[X, Y]` in public APIs, or `from __future__ import annotations`
  - `tomllib` → available in 3.11+; for 3.10 add `tomli` as dependency with fallback import
  - `match` statements → replace with `if/elif` (3.10 has match but safer to avoid for 3.10.0-3.10.5 edge cases)

### 3.3 Config Error Messages

Replace raw `ValueError("Missing [connectors.weather]...")` with user-friendly messages that include the fix:
```
✗ Missing [connectors.weather] in nexus.toml
  Fix: Add weather coordinates to your config, or run: nexus init
```

---

## 4. UI Revamp

### 4.1 Dashboard (Home)

Replace current digest-only page with a proper dashboard:
- **Top:** greeting (`Good morning, Tawin`) + date + weather summary
  - **Digest card:** latest digest content, "Run Briefing" button, last-generated timestamp
  - **Connector grid:** status card per connector (green=connected, red=error, grey=disabled), last sync time
  - **Quick actions:** "Ask NEXUS", "Log idea", "Force sync"

### 4.2 Chat View

- Properly sized message bubbles (not tiny text)
  - Streaming tokens visible as they arrive
  - Source chips below each AI response (which Notion pages were used)
  - `/code` and `/think` mode indicators visible in input bar
  - Persistent session — chat history stored in SQLite `ConversationTurn` model

### 4.3 Notion Explorer

- Tree sidebar already exists — needs polish
  - Page content renders markdown properly (already partially done)
  - Search bar at top of tree

### 4.4 Settings Page (New)

- Shows current config values (read-only display)
  - LLM provider + model in use
  - Connector list: enabled/disabled toggles (writes to config)
  - "Re-run setup wizard" button → `nexus init`

### 4.5 Visual Direction

Dark theme, monospace accent font, system body font. Color palette: dark bg (`#0d0d0d`), gold accent (`#d4a017` — keep existing), muted borders (`#1e1e1e`). No gradients, no animations except subtle skeleton loaders. Aesthetic: Raycast meets terminal — a tool for power users.

---

## 5. Open Source Readiness

### 5.1 README.md

Structure:
1. **Hero** — one-line description + badges (PyPI version, Python 3.10+, License)
   2. **What it does** — 3-bullet feature list
   3. **Quick start** — 3 commands: `pip install opennexus`, `nexus init`, `nexus serve`
   4. **Connector list** — table: connector, what it provides, setup command
   5. **LLM support** — table: provider, models, cost
   6. **Screenshot/GIF** — placeholder for demo recording
   7. **Contributing** — link to CONTRIBUTING.md

### 5.2 CONTRIBUTING.md

How to add a connector:
1. Subclass `ConnectorBase` in `backend/connectors/`
   2. Implement `connect()`, `health()`, and a data-fetch method
   3. Register in `ConnectorsConfig`
   4. Add to `nexus connect` command
   5. Add to digest agent if it contributes to morning briefing

### 5.3 Updated nexus.toml.example

Add new sections: `[user]`, `[llm]`. Remove Ollama-specific fields from top-level, move to `[llm]`. Keep all connector sections.

### 5.4 GitHub Repo Polish

- `LICENSE` — MIT (already exists, verify)
  - `.github/ISSUE_TEMPLATE/` — bug report + feature request templates
  - `.github/PULL_REQUEST_TEMPLATE.md`

---

## 6. Implementation Order

1. Python 3.10 compat fixes (unblocks everyone)
   2. `[user]` config + generalize system prompt (unblocks personalization)
   3. Multi-LLM engine layer (biggest value for adoption)
   4. `nexus init` wizard (removes #1 friction: manual config)
   5. Digest persistence (SQLite DigestEntry)
   6. UI revamp (Dashboard + Chat polish)
   7. Settings page
   8. README + CONTRIBUTING + .github templates
   9. PyPI rename + publish `opennexus`

---

## 7. Out of Scope (V1)

- Plugin system (V2)
  - Docker / self-hosted cloud (V2)
  - Spotify connector (V2)
  - Telegram connector (V2)
  - Mobile app (V3)
  - Multi-user support (V3)

---

## Success Criteria

- `pip install opennexus && nexus init && nexus serve` works in under 5 minutes on any machine with Python 3.10+
  - All three LLM providers functional
  - Morning digest includes at least 3 live data sources
  - UI looks polished enough to screenshot for README
  - Tests pass on Python 3.10, 3.11, 3.12, 3.13
