# NEXUS Design Spec
**Date:** 2026-06-01  
**Author:** Tawin Tangsukson  
**Status:** Approved

---

## 1. Vision

NEXUS is a local-first personal intelligence layer — not a chatbot. It knows Tawin's vault, inbox, calendar, code, and feeds. Every response is grounded in real personal context retrieved from local memory. Zero cloud. Zero telemetry. Zero data leaves the machine.

Future: multi-user SaaS with per-user vault isolation and cloud-optional connectors.

---

## 2. Hardware & Runtime Environment

| Item | Value |
|---|---|
| OS | Windows 11 Pro |
| GPU | RTX 5060 |
| Python | 3.13 (via uv) |
| Node | v24 |
| Ollama | Already installed, running |
| Vault | `C:\Users\Tawin Tangsukson\Documents\NEXUSVault` |
| Secrets | `~/.nexus/` (gitignored) |

---

## 3. Ollama Models

| Role | Model |
|---|---|
| General chat | `qwen2.5:7b` |
| Code questions | `qwen2.5-coder:7b` |
| Reasoning / planning | `deepseek-r1:7b` |
| Embeddings | `nomic-embed-text` |

Model routing: CLI detects context. `/code` prefix → coder. `/think` prefix → deepseek-r1. Default → qwen2.5:7b.

---

## 4. Project Structure

```
OpenNexus/
├── backend/
│   ├── core/
│   │   ├── config.py          # load nexus.toml, typed dataclass
│   │   ├── engine.py          # Ollama client: chat(), embed(), stream_chat()
│   │   ├── memory.py          # ChromaDB: vault_chunks, conversation_history, file_index collections
│   │   └── db.py              # SQLite via SQLModel: Conversation, Turn, DigestLog, ConnectorStatus
│   ├── connectors/
│   │   ├── base.py            # ConnectorBase abstract: connect(), fetch(), health()
│   │   ├── obsidian.py        # read/write vault, scaffold, daily note, RAG index trigger
│   │   ├── gmail.py           # OAuth2 PKCE, read threads, summarize, triage labels
│   │   ├── calendar.py        # OAuth2 shared token, today/week events
│   │   ├── github.py          # PAT, PRs/issues/notifs/commits via REST v3
│   │   ├── discord.py         # bot token, channel message fetch, summaries
│   │   ├── weather.py         # open-meteo Bangkok (13.75°N 100.52°E), no key
│   │   ├── rss.py             # feedparser, configurable sources in nexus.toml
│   │   └── stubs/
│   │       ├── telegram.py    # stub: send/receive via bot token
│   │       ├── spotify.py     # stub: now playing, playback control
│   │       └── notion.py      # stub: read/write pages and databases
│   ├── agents/
│   │   ├── chat.py            # full chat pipeline (see §7)
│   │   ├── digest.py          # morning briefing composer
│   │   └── rag.py             # embed query → ChromaDB → top-K chunks
│   ├── scheduler/
│   │   └── jobs.py            # APScheduler: digest @ 08:00 Asia/Bangkok, vault re-index @ 02:00
│   └── api/
│       ├── main.py            # FastAPI app factory, mounts /static → frontend/dist
│       └── routes/
│           ├── chat.py        # POST /api/chat, GET /api/chat/stream (SSE)
│           ├── digest.py      # GET /api/digest, POST /api/digest/run
│           ├── vault.py       # GET /api/vault/tree, /api/vault/file, /api/vault/search
│           ├── connectors.py  # GET /api/status, POST /api/connect/{service}
│           └── memory.py      # POST /api/memory/index
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Chat.tsx       # SSE stream, context chips, message history
│   │   │   ├── Digest.tsx     # morning briefing as cards (default view)
│   │   │   ├── Vault.tsx      # file tree + markdown preview + search
│   │   │   └── Status.tsx     # connector health, model info, memory stats
│   │   ├── components/
│   │   │   ├── ContextChip.tsx      # shows vault note used in retrieval
│   │   │   ├── StreamMessage.tsx    # SSE streaming text with cursor
│   │   │   ├── VaultTree.tsx        # recursive file tree
│   │   │   ├── ConnectorBadge.tsx   # green/red health dot
│   │   │   └── Sidebar.tsx          # nav between 4 views
│   │   ├── hooks/
│   │   │   ├── useSSE.ts      # EventSource wrapper, auto-reconnect
│   │   │   └── useVault.ts    # vault tree + file fetch
│   │   ├── lib/
│   │   │   └── api.ts         # typed fetch wrappers for all routes
│   │   └── App.tsx            # router, theme provider
│   ├── index.html
│   ├── vite.config.ts         # proxy /api → :8000 (enables future process split)
│   ├── tailwind.config.ts     # terminal-noir theme tokens
│   └── package.json
├── cli/
│   └── main.py                # typer CLI entrypoint
├── nexus.toml.example         # all non-secret config with comments
├── setup.ps1                  # one-shot installer
├── pyproject.toml             # uv project, all backend deps
└── docs/
    ├── superpowers/specs/2026-06-01-nexus-design.md
    ├── obsidian-setup-guide.md
    └── README.md
```

---

## 5. Config Schema (`nexus.toml`)

```toml
[nexus]
vault_path = "C:/Users/Tawin Tangsukson/Documents/NEXUSVault"
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
vault_collection = "vault_chunks"
conversation_collection = "conversation_history"
file_collection = "file_index"
top_k = 5
chunk_strategy = "heading"   # split by markdown H1/H2/H3

[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"

[scheduler]
digest_cron = "0 8 * * *"      # 08:00 Bangkok daily
reindex_cron = "0 2 * * *"     # 02:00 Bangkok daily

[digest]
write_to_vault = true
print_to_terminal = true

[connectors.weather]
latitude = 13.7563
longitude = 100.5018
location_name = "Bangkok"

[connectors.rss]
sources = [
  "https://feeds.feedburner.com/oreilly/radar",
  "https://tldr.tech/api/rss/tech",
  "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
  "https://hnrss.org/frontpage",
]

[connectors.discord]
enabled = true  # token in ~/.nexus/discord.json

[connectors.github]
enabled = true  # token in ~/.nexus/github.json

[connectors.gmail]
enabled = true  # credentials in ~/.nexus/gmail_credentials.json

[connectors.calendar]
enabled = true  # shared token with gmail

[connectors.telegram]
enabled = false  # stub

[connectors.spotify]
enabled = false  # stub

[connectors.notion]
enabled = false  # stub
```

Secrets in `~/.nexus/`: `gmail_credentials.json`, `gmail_token.json`, `github.json`, `discord.json`. Never committed.

---

## 6. Memory System (ChromaDB)

Three collections:

**`vault_chunks`**
- Source: Obsidian vault markdown files
- Chunked by markdown heading (H1/H2/H3 boundaries)
- Metadata: `{file_path, heading, mtime, word_count}`
- Re-indexed: on `nexus memory index`, on vault write, nightly at 02:00

**`conversation_history`**
- Source: every chat turn (user + assistant)
- Chunked: one document per turn-pair
- Metadata: `{session_id, timestamp, model, sources_used}`
- Injected: last 10 turns by timestamp as recent context

**`file_index`**
- Source: `nexus memory index <path>` command
- Chunked: 500 tokens, 50 overlap (arbitrary files lack headings)
- Metadata: `{file_path, file_type, mtime}`

---

## 7. Chat Pipeline (Per Turn)

```
User query
  │
  ▼
1. Embed query → nomic-embed-text
  │
  ▼
2. ChromaDB similarity search
   - vault_chunks: top 5 by cosine similarity
   - conversation_history: last 10 turns by recency
  │
  ▼
3. Live context fetch (parallel, timeout 2s each)
   - calendar.today()    → next 3 events
   - gmail.unread_count()
   - github.open_prs()
   - weather.current()
  │
  ▼
4. Build system prompt
   - Persona section: who Tawin is, goals, preferences
   - Vault context: top 5 chunks with source note names
   - Live context: calendar/email/github/weather if relevant
   - Conversation history: last 10 turns
  │
  ▼
5. Route to model
   - /code prefix → qwen2.5-coder:7b
   - /think prefix → deepseek-r1:7b
   - default → qwen2.5:7b
  │
  ▼
6. Stream via Ollama SSE → forward as SSE to client
  │
  ▼
7. On completion:
   - Save turn to SQLite (Conversation + Turn tables)
   - Embed turn-pair → upsert to conversation_history ChromaDB
   - Return context_chips: [{note_name, score, heading}] × 5
```

---

## 8. CLI Commands

| Command | Behavior |
|---|---|
| `nexus ask "..."` | Single-shot query, streams to terminal, rich markdown output via `rich`, < 2s target |
| `nexus chat` | Interactive REPL, persistent session, Ctrl+C to exit |
| `nexus digest` | Run morning briefing now, write to daily note + print |
| `nexus note "..."` | Append new note to vault Ideas folder, timestamp + auto-tag |
| `nexus log "..."` | Append line to today's daily note ## Notes section |
| `nexus connect <service>` | Interactive token/OAuth setup per connector |
| `nexus memory index <path>` | Ingest folder/file into ChromaDB file_index |
| `nexus serve` | Start FastAPI + serve frontend at localhost:8000 |
| `nexus doctor` | Health check: Ollama, ChromaDB, connectors, vault, scheduler |

---

## 9. Digest Agent

Runs at 08:00 Bangkok or on-demand via `nexus digest`. Composes briefing from:

1. **Weather** — Bangkok current + forecast
2. **Calendar** — today's schedule (all events)
3. **Gmail** — unread count, top 3 priority emails (AI-triaged by subject/sender)
4. **GitHub** — open PRs needing review, new notifications
5. **RSS** — top 5 articles from configured feeds (published last 24h)
6. **Discord** — unread message count per enabled channel
7. **Yesterday reflection** — last entry from yesterday's daily note if exists

Output written to:
- Today's Obsidian daily note `## Morning Briefing` section
- Terminal via `rich` Panel

---

## 10. Obsidian Vault Scaffold

Auto-created at first run if `vault_path` doesn't exist:

```
NEXUSVault/
├── Daily Notes/
│   └── Templates/
│       └── Daily Note Template.md
├── Projects/
│   └── Templates/
│       └── Project Template.md
├── Research/
│   └── Templates/
│       └── Research Template.md
├── Ideas/
├── People/
│   └── Templates/
│       └── Person Template.md
├── Resources/
├── Archive/
└── .obsidian/
    └── app.json              # minimal config (no plugins required)
```

Daily note filename: `YYYY-MM-DD.md` in `Daily Notes/`.

Daily note template sections:
- `## Morning Briefing` — digest output
- `## Schedule` — calendar events
- `## Top 3 Priorities` — checkboxes
- `## Notes` — `nexus log` appends here
- `## Ideas` — quick captures
- `## End of Day Reflection` — what shipped, blockers, tomorrow

---

## 11. FastAPI Routes

```
GET  /                        → serve frontend/dist/index.html
GET  /assets/*                → serve frontend/dist/assets/

POST /api/chat                → {query, session_id?} → {response, context_chips, model}
GET  /api/chat/stream         → SSE: data: {token} … data: [DONE]

GET  /api/digest              → latest digest from DigestLog
POST /api/digest/run          → trigger digest now, returns digest object

GET  /api/vault/tree          → recursive file tree JSON
GET  /api/vault/file          → {path} → {content, mtime}
GET  /api/vault/search        → {q} → [{file, heading, snippet, score}]

GET  /api/status              → {connectors: [{name, healthy, last_checked}], model, memory_stats}
POST /api/connect/{service}   → initiate OAuth or save token

POST /api/memory/index        → {path} → background task, returns job_id
```

---

## 12. Frontend — Terminal-Noir Aesthetic

```
Colors:
  background:  #0a0a0a
  surface:     #111111
  border:      #1e1e1e
  accent:      #d4a017  (amber)
  text:        #e0e0e0
  muted:       #555555
  success:     #4caf50
  error:       #cf6679

Font: JetBrains Mono (Google Fonts CDN — loads once, cached)
Border radius: 4px max — flat and minimal
Animations: none except SSE cursor blink
```

Four views (default: Digest):

**Chat** — left: message history with `StreamMessage` (SSE cursor), right sidebar: `ContextChip` × 5 showing vault note used, similarity score, heading. Input bar at bottom with `/code` and `/think` prefix hints.

**Digest** — cards: Weather, Calendar, Email, GitHub, RSS, Discord. Each card has icon + data. Refresh button triggers POST /api/digest/run.

**Vault** — left: `VaultTree` recursive folders, click file → right: markdown rendered with syntax highlighting. Search bar at top triggers /api/vault/search.

**Status** — grid of `ConnectorBadge` (green/red dot + last checked time). Below: active model name, ChromaDB collection sizes, SQLite turn count.

---

## 13. Secrets Storage

```
~/.nexus/
├── gmail_credentials.json    # OAuth2 client_id + client_secret (from GCP)
├── gmail_token.json          # OAuth2 access + refresh token (auto-refreshed)
├── github.json               # {"token": "ghp_..."}
└── discord.json              # {"token": "Bot ..."}
```

All loaded at startup via `core/config.py`. Never logged. Never in nexus.toml. `~/.nexus/` added to global `.gitignore`.

---

## 14. Setup Script (`setup.ps1`)

Steps in order:
1. Check uv installed → install if missing
2. `uv sync` — install all Python deps
3. `npm install` in `frontend/` → `npm run build`
4. Check Ollama running → pull 4 models if missing
5. Create vault scaffold at configured path
6. Copy `nexus.toml.example` → `nexus.toml` if not exists
7. Create `~/.nexus/` directory
8. Walk through Google OAuth setup (open browser → GCP console URL + instructions)
9. Walk through GitHub PAT setup (open browser + instructions)
10. Walk through Discord bot token setup
11. Register `nexus` function in PowerShell profile (`$PROFILE`)
12. Run `nexus doctor` to verify everything

---

## 15. Build Order

1. `core/config.py` + `core/engine.py` — Ollama chat + embed working
2. `core/memory.py` — ChromaDB collections init
3. `cli/main.py` — `nexus ask` working end-to-end
4. `connectors/obsidian.py` + vault scaffold
5. `connectors/gmail.py` + `connectors/calendar.py` + `connectors/github.py`
6. `agents/digest.py` + `scheduler/jobs.py`
7. `api/main.py` + all routes
8. React frontend — all 4 views
9. `setup.ps1`
10. `docs/README.md` + `docs/obsidian-setup-guide.md`

---

## 16. Non-Goals (v1)

- No LangChain, no OpenAI API, no Docker, no cloud DB
- No multi-user auth (future)
- No mobile app (future)
- No voice interface (future)
- Telegram / Spotify / Notion ship as stubs, enabled via `nexus connect`
