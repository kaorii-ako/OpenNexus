# NEXUS Design Spec
**Date:** 2026-06-01  
**Author:** Tawin Tangsukson  
**Status:** Approved — v2 (Notion-first, auto-start)

---

## 1. Vision

NEXUS is a local-first personal intelligence layer — not a chatbot. It knows Tawin's Notion workspace, inbox, calendar, classes, code, and feeds. Every response is grounded in real personal context retrieved from local memory. Zero telemetry. All processing on-device. Notion is the human-facing second brain; NEXUS caches it locally for instant RAG.

Future: multi-user SaaS with per-user workspace isolation and cloud-optional connectors.

---

## 2. Hardware & Runtime Environment

| Item | Value |
|---|---|
| OS | Windows 11 Pro |
| GPU | RTX 5060 |
| Python | 3.13 (via uv) |
| Node | v24 |
| Ollama | Already installed, running |
| Notion cache | `~/.nexus/notion_cache/` (local markdown mirror) |
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
│   │   ├── memory.py          # ChromaDB: notion_chunks, conversation_history, file_index
│   │   └── db.py              # SQLite via SQLModel: Conversation, Turn, DigestLog, ConnectorStatus
│   ├── connectors/
│   │   ├── base.py            # ConnectorBase abstract: connect(), fetch(), health()
│   │   ├── notion.py          # Notion API: read/write pages+DBs, sync to local cache
│   │   ├── notion_sync.py     # sync daemon: Notion pages → ~/.nexus/notion_cache/*.md
│   │   ├── gmail.py           # OAuth2 PKCE, read threads, summarize, triage labels
│   │   ├── calendar.py        # OAuth2 shared token, today/week events
│   │   ├── classroom.py       # Google Classroom API: courses, assignments, announcements
│   │   ├── github.py          # PAT, PRs/issues/notifs/commits via REST v3
│   │   ├── discord.py         # bot token, channel message fetch, summaries
│   │   ├── weather.py         # open-meteo Bangkok (13.75°N 100.52°E), no key
│   │   ├── rss.py             # feedparser, configurable sources in nexus.toml
│   │   └── stubs/
│   │       ├── telegram.py    # stub: send/receive via bot token
│   │       └── spotify.py     # stub: now playing, playback control
│   ├── agents/
│   │   ├── chat.py            # full chat pipeline (see §7)
│   │   ├── digest.py          # morning briefing composer
│   │   └── rag.py             # embed query → ChromaDB → top-K chunks
│   ├── scheduler/
│   │   └── jobs.py            # APScheduler: digest @ 08:00 BKK, notion sync @ */15, reindex @ 02:00
│   └── api/
│       ├── main.py            # FastAPI app factory, mounts /static → frontend/dist
│       └── routes/
│           ├── chat.py        # POST /api/chat, GET /api/chat/stream (SSE)
│           ├── digest.py      # GET /api/digest, POST /api/digest/run
│           ├── notion.py      # GET /api/notion/tree, /api/notion/page, /api/notion/search
│           ├── connectors.py  # GET /api/status, POST /api/connect/{service}
│           └── memory.py      # POST /api/memory/index
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── Chat.tsx       # SSE stream, context chips, message history
│   │   │   ├── Digest.tsx     # morning briefing as cards (default view)
│   │   │   ├── Notion.tsx     # page tree + content preview + search
│   │   │   └── Status.tsx     # connector health, model info, memory stats
│   │   ├── components/
│   │   │   ├── ContextChip.tsx      # shows notion page used in retrieval
│   │   │   ├── StreamMessage.tsx    # SSE streaming text with cursor
│   │   │   ├── NotionTree.tsx       # page hierarchy tree
│   │   │   ├── ConnectorBadge.tsx   # green/red health dot
│   │   │   └── Sidebar.tsx          # nav between 4 views
│   │   ├── hooks/
│   │   │   ├── useSSE.ts      # EventSource wrapper, auto-reconnect
│   │   │   └── useNotion.ts   # notion tree + page fetch
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
├── setup.ps1                  # one-shot installer + startup registration
├── pyproject.toml             # uv project, all backend deps
└── docs/
    ├── superpowers/specs/2026-06-01-nexus-design.md
    └── README.md
```

---

## 5. Config Schema (`nexus.toml`)

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
chunk_strategy = "heading"   # split by markdown H1/H2/H3

[server]
host = "127.0.0.1"
port = 8000
frontend_dist = "./frontend/dist"
open_browser_on_start = true   # auto-open localhost:8000 on nexus serve

[scheduler]
digest_cron = "0 8 * * *"       # 08:00 Bangkok daily
notion_sync_cron = "*/15 * * * *"  # every 15 min
reindex_cron = "0 2 * * *"     # 02:00 Bangkok nightly

[digest]
write_to_notion = true    # appends to today's Notion daily page
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

[connectors.notion]
enabled = true   # token in ~/.nexus/notion.json

[connectors.discord]
enabled = true   # token in ~/.nexus/discord.json

[connectors.github]
enabled = true   # token in ~/.nexus/github.json

[connectors.gmail]
enabled = true   # credentials in ~/.nexus/gmail_credentials.json

[connectors.calendar]
enabled = true   # shared token with gmail

[connectors.classroom]
enabled = true   # shared token with gmail (Classroom API scope added)

[connectors.telegram]
enabled = false  # stub

[connectors.spotify]
enabled = false  # stub
```

Secrets in `~/.nexus/`: `gmail_credentials.json`, `gmail_token.json`, `github.json`, `discord.json`, `notion.json`. Never committed.

---

## 6. Notion as Second Brain

Notion is the primary write surface. NEXUS never replaces Notion — it mirrors and understands it.

### Notion Workspace Scaffold

On `nexus connect notion` (first run), NEXUS creates this structure via Notion API:

```
NEXUS Workspace (root page)
├── 📅 Daily Notes          ← database, one row per day
├── 🚀 Projects             ← database: Name, Status, Domain, GitHub repo
├── 🔬 Research             ← database: Topic, Tags, Status
├── 🎓 Courses              ← database: Course code, Professor, Semester, Exam date
│   └── [Course pages]
│       ├── Lectures        ← sub-database per course
│       └── Assignments     ← sub-database per course
├── 💡 Ideas                ← database: Title, Tags, Priority, Created
├── 👥 People               ← database: Name, Role, Contact
├── 📚 Resources            ← database: Title, URL, Tags
└── 🗄️ Archive              ← moved here when done
```

### Notion Sync Daemon (`notion_sync.py`)

Runs every 15 min via APScheduler + on-demand via `nexus memory index`:

1. Fetch all pages modified since last sync timestamp
2. Convert Notion block tree → clean markdown
3. Write to `~/.nexus/notion_cache/<page_id>.md` with frontmatter
4. Trigger ChromaDB re-index on changed files only
5. Update `last_synced` in SQLite ConnectorStatus

RAG runs entirely on local cache — no Notion API calls during chat.

### Daily Note in Notion

`nexus digest` creates (or updates) today's row in the Daily Notes database with:
- Morning Briefing (weather, calendar, email, GitHub, RSS, Discord)
- Schedule block
- Top 3 Priorities (checklist)
- Notes section (`nexus log` appends here via Notion API)
- Ideas section (`nexus note` creates here)
- End of Day Reflection (empty, filled by Tawin)

---

## 7. Memory System (ChromaDB)

Three collections:

**`notion_chunks`**
- Source: `~/.nexus/notion_cache/*.md` (local Notion mirror)
- Chunked by markdown heading (H1/H2/H3 boundaries)
- Metadata: `{page_id, page_title, heading, database, mtime, word_count}`
- Re-indexed: on sync, nightly at 02:00, on-demand

**`conversation_history`**
- Source: every chat turn (user + assistant)
- One document per turn-pair
- Metadata: `{session_id, timestamp, model, sources_used}`
- Injected: last 10 turns by recency + semantic search for older relevant turns

**`file_index`**
- Source: `nexus memory index <path>` command
- Chunked: 500 tokens, 50 overlap
- Metadata: `{file_path, file_type, mtime}`

---

## 8. Chat Pipeline (Per Turn)

```
User query
  │
  ▼
1. Embed query → nomic-embed-text (local)
  │
  ▼
2. ChromaDB similarity search
   - notion_chunks: top 5 by cosine similarity
   - conversation_history: last 10 turns by recency
  │
  ▼
3. Live context fetch (parallel asyncio, 2s timeout each)
   - calendar.today()        → next 3 events
   - gmail.unread_count()    → count + top sender
   - github.open_prs()       → PR titles + review status
   - classroom.due_soon()    → assignments due in 48h
   - weather.current()       → Bangkok current conditions
  │
  ▼
4. Build system prompt
   - Persona: Tawin — developer + student, Bangkok, building NEXUS
   - Notion context: top 5 chunks with page title + heading
   - Live context: calendar/email/github/classroom/weather
   - Conversation history: last 10 turns
  │
  ▼
5. Route to model
   - /code → qwen2.5-coder:7b
   - /think → deepseek-r1:7b
   - default → qwen2.5:7b
  │
  ▼
6. Stream via Ollama → SSE to client
  │
  ▼
7. On completion:
   - Save turn to SQLite
   - Embed turn-pair → upsert to conversation_history
   - Return context_chips: [{page_title, score, heading, database}] × 5
```

---

## 9. Google Classroom Connector

Shares OAuth token with Gmail/Calendar (add Classroom API scope to GCP project).

Fetches:
- Active courses (course name, section, teacher)
- Upcoming assignments (title, due date, course)
- Course announcements (last 24h)
- Grades (if available)

Used in:
- Digest: "Assignments due soon" section
- Chat: `classroom.due_soon()` injected as live context
- Status view: connector health badge

---

## 10. CLI Commands

| Command | Behavior |
|---|---|
| `nexus ask "..."` | Single-shot query, rich markdown output, < 2s |
| `nexus chat` | Interactive REPL, persistent session, Ctrl+C exits |
| `nexus digest` | Run morning briefing now, write to Notion + print |
| `nexus note "..."` | Create Notion page in Ideas database, auto-tag |
| `nexus log "..."` | Append block to today's Notion daily page Notes section |
| `nexus connect <service>` | Interactive OAuth/token setup per connector |
| `nexus memory index <path>` | Ingest folder/file into ChromaDB file_index |
| `nexus serve` | Start FastAPI + open browser at localhost:8000 |
| `nexus doctor` | Health check: Ollama, ChromaDB, all connectors, scheduler |
| `nexus sync` | Force Notion sync now (don't wait for 15 min schedule) |

---

## 11. Digest Agent

Runs at 08:00 Bangkok or on-demand. Sections:

1. **Weather** — Bangkok current + today's forecast
2. **Calendar** — all events today
3. **Gmail** — unread count + top 3 AI-triaged priority emails
4. **GitHub** — open PRs, new issue notifications
5. **Google Classroom** — assignments due in 48h, new announcements
6. **RSS** — top 5 articles from last 24h
7. **Discord** — unread summary per channel
8. **Yesterday** — last entry from yesterday's Notion daily page

Written to Notion daily page `## Morning Briefing` block + printed to terminal via `rich` Panel.

---

## 12. FastAPI Routes

```
GET  /                          → serve frontend/dist/index.html
GET  /assets/*                  → serve frontend/dist/assets/

POST /api/chat                  → {query, session_id?} → {response, context_chips, model}
GET  /api/chat/stream           → SSE: data: {token} … data: [DONE]

GET  /api/digest                → latest digest from DigestLog
POST /api/digest/run            → trigger digest now

GET  /api/notion/tree           → page hierarchy JSON
GET  /api/notion/page           → {page_id} → {title, content_md, mtime}
GET  /api/notion/search         → {q} → [{page_title, heading, snippet, score}]

GET  /api/status                → {connectors: [{name, healthy, last_checked}], model, memory_stats}
POST /api/connect/{service}     → initiate OAuth or save token

POST /api/memory/index          → {path} → background task, returns job_id
POST /api/sync                  → force Notion sync now
```

---

## 13. Frontend — Terminal-Noir Aesthetic

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

Font: JetBrains Mono (Google Fonts, loaded once, cached locally)
Border radius: 4px max — flat and minimal
Animations: SSE cursor blink only
```

Four views (default: **Digest**):

**Chat** — message history left, `ContextChip` × 5 right sidebar (page title, database, heading, similarity score). Input bar bottom with `/code` `/think` hints.

**Digest** — cards: Weather, Calendar, Email, GitHub, Classroom, RSS, Discord. Refresh button → POST /api/digest/run.

**Notion** — left: `NotionTree` page hierarchy. Click page → right: markdown content rendered with syntax highlighting. Search bar → /api/notion/search.

**Status** — `ConnectorBadge` grid (Notion, Gmail, Calendar, Classroom, GitHub, Discord, Weather, RSS). Below: model, ChromaDB sizes, SQLite turn count, last Notion sync time.

---

## 14. Secrets Storage

```
~/.nexus/
├── gmail_credentials.json    # OAuth2 client_id + client_secret (GCP)
├── gmail_token.json          # OAuth2 access + refresh token (auto-refreshed)
├── github.json               # {"token": "ghp_..."}
├── discord.json              # {"token": "Bot ..."}
└── notion.json               # {"token": "secret_..."}
```

Never logged. Never in nexus.toml. `~/.nexus/` in global `.gitignore`.

---

## 15. Auto-Start on Windows Login

Both `nexus serve` and browser open automatically on login via Windows Task Scheduler.

`setup.ps1` registers two tasks:

**Task 1 — NEXUS Server**
```
Name:    NEXUS-Server
Trigger: At log on (current user)
Action:  uv run python -m cli.main serve
WorkDir: C:\Users\Tawin Tangsukson\OpenNexus
```

**Task 2 — NEXUS Browser**
```
Name:    NEXUS-Browser
Trigger: At log on + 8 second delay (wait for server ready)
Action:  Start-Process "http://localhost:8000"
```

`nexus doctor` verifies both tasks exist and are enabled. To disable: `schtasks /Delete /TN NEXUS-Server /F`.

---

## 16. Setup Script (`setup.ps1`)

Steps in order:
1. Check `uv` installed → install via `winget` if missing
2. `uv sync` — install all Python deps from `pyproject.toml`
3. `npm install` in `frontend/` → `npm run build`
4. Check Ollama running → pull 4 models if missing
5. Copy `nexus.toml.example` → `nexus.toml` if not exists
6. Create `~/.nexus/` directory
7. Add `~/.nexus/` to global git ignore
8. **Google OAuth setup** — step-by-step: open GCP console, create project, enable Gmail + Calendar + Classroom APIs, download `credentials.json`, save to `~/.nexus/gmail_credentials.json`
9. **GitHub PAT setup** — open github.com/settings/tokens, required scopes listed, paste token
10. **Discord bot setup** — open discord.com/developers, required permissions listed, paste token
11. **Notion setup** — open notion.so/my-integrations, create integration, paste token, then run workspace scaffold
12. Register `nexus` function in PowerShell `$PROFILE`
13. Register Task Scheduler tasks for auto-start
14. Run `nexus doctor` to verify everything green

---

## 17. Build Order

1. `core/config.py` + `core/engine.py` — Ollama chat + embed working
2. `core/memory.py` — ChromaDB collections init
3. `cli/main.py` — `nexus ask` working end-to-end
4. `connectors/notion.py` + `notion_sync.py` + workspace scaffold
5. `connectors/gmail.py` + `connectors/calendar.py` + `connectors/classroom.py` + `connectors/github.py`
6. `connectors/discord.py` + `connectors/weather.py` + `connectors/rss.py`
7. `agents/digest.py` + `scheduler/jobs.py`
8. `api/main.py` + all routes
9. React frontend — all 4 views
10. `setup.ps1` + Task Scheduler registration
11. `docs/README.md`

---

## 18. Non-Goals (v1)

- No LangChain, no OpenAI API, no Docker, no cloud DB
- No multi-user auth (future)
- No mobile app (future)
- No voice interface (future)
- Telegram / Spotify ship as stubs, enabled via `nexus connect`
- No Obsidian integration (Notion-first)
