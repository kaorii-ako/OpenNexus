<div align="center">

<h1>🔗 OpenNexus</h1>

<p><strong>Your personal AI that actually knows your life.</strong><br>
Morning briefings. Chat with your data. Runs local or cloud. You own everything.</p>

[![PyPI](https://img.shields.io/pypi/v/opennexus-ai?style=flat-square&color=blue)](https://pypi.org/project/opennexus-ai/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/opennexus-ai?style=flat-square&color=green)](https://pypi.org/project/opennexus-ai/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Stars](https://img.shields.io/github/stars/kaorii-ako/OpenNexus?style=flat-square)](https://github.com/kaorii-ako/OpenNexus/stargazers)

<br>

```bash
pip install opennexus-ai && nexus init
```

</div>

---

## Why OpenNexus?

You pay $20/mo for ChatGPT — it knows nothing about your actual life. Your inbox, your calendar, your projects, your notes. It's all disconnected.

OpenNexus is the missing layer: a **self-hosted personal AI** that pulls from your real data sources, runs a morning briefing every day, and lets you ask questions like:

> *"What do I have this week?"*  
> *"Summarize my unread emails from the last 2 days."*  
> *"What GitHub PRs are waiting on me?"*  
> *"What did I write in my notes about project X?"*

**Your data stays yours.** Run it with Ollama locally — nothing leaves your machine.

---

## Demo

<!-- Add a GIF here: record `nexus serve` → open browser → show digest + chat -->
> 🎬 **[Add demo GIF here]** — Run `nexus serve`, open localhost:8000, show the morning digest and chat.

---

## Features

| | Feature | Status |
|---|---------|--------|
| 🌅 | **Morning Digest** — daily briefing: weather, calendar, email, PRs, assignments, headlines | ✅ |
| 💬 | **AI Chat** — RAG over your Notion workspace, streaming responses | ✅ |
| 📧 | **Gmail** — unread count, top senders, summaries | ✅ |
| 📅 | **Google Calendar** — today's events, upcoming schedule | ✅ |
| 📚 | **Google Classroom** — upcoming assignments (students ❤️) | ✅ |
| 📝 | **Notion** — full workspace RAG, daily notes, capture | ✅ |
| 🐙 | **GitHub** — open PRs, notifications, review requests | ✅ |
| 🎮 | **Discord** — server messages | ✅ |
| ⛅ | **Weather** — current conditions | ✅ |
| 📰 | **RSS** — news headlines from any feed | ✅ |
| 🦙 | **Ollama (local)** — fully offline, zero data leakage | ✅ |
| 🤖 | **OpenAI / Anthropic** — cloud LLMs if you prefer | ✅ |
| 🎵 | **Spotify** — listening history | 🚧 |
| 📱 | **Telegram** — messages | 🚧 |

---

## Quick Start

**Install:**
```bash
pip install opennexus-ai
```

**Set up (interactive wizard):**
```bash
nexus init
```

**Run:**
```bash
nexus serve
# → open http://localhost:8000
```

That's it. The wizard walks you through connecting your services.

---

## LLM Support

```bash
# Local — nothing leaves your machine
nexus init  # select "ollama", then: ollama pull llama3.2

# OpenAI
nexus init  # select "openai", paste your API key

# Anthropic
nexus init  # select "anthropic", paste your API key
```

| Provider | Chat | Embeddings |
|----------|------|-----------|
| Ollama (local) | ✅ | ✅ |
| OpenAI | ✅ | ✅ |
| Anthropic | ✅ | — |

---

## CLI

```bash
nexus init            # interactive setup wizard
nexus serve           # web UI + API (http://localhost:8000)
nexus digest          # run morning briefing now
nexus ask "..."       # one-shot question
nexus chat            # interactive REPL
nexus sync            # force re-sync Notion
nexus note "..."      # capture idea → Notion
nexus log "..."       # append to today's daily note
nexus connect <svc>   # authorize a new connector
nexus doctor          # check connector health
```

**Orchestrator** (see [below](#the-orchestrator)):

```bash
nexus setup                  # check status, scaffold missing directories
nexus route "..."            # route a query through the skills, log the decision
nexus route -a "..."         # route AND answer, grounded in the loaded skills
nexus evolve                 # review the log for friction, propose one skill edit
nexus evolve --revert <id>   # undo an applied edit
nexus replay --last 20       # re-emit real history through the live renderer
nexus events --verify        # check the append-only log for tampering
nexus hud                    # dashboard + console at localhost:8420
```

### LLM providers

`provider` in `[llm]` accepts `auto`, `ollama`, `openai`, or `anthropic`.
`auto` prefers a local Ollama when one is actually running, and otherwise falls
back to whichever key is in the environment (`OPENAI_API_KEY` /
`ANTHROPIC_API_KEY`) — so the key never has to live in `nexus.toml`.

Any **OpenAI-compatible** endpoint works — NVIDIA NIM, Groq, Together, vLLM,
LM Studio. Point `openai_base_url` at it (or export `OPENAI_BASE_URL`) and set
`model` to something that endpoint actually serves:

```toml
[llm]
provider = "openai"
openai_base_url = "https://integrate.api.nvidia.com/v1"
model = "nvidia/llama-3.3-nemotron-super-49b-v1.5"
embed_model = "nvidia/nv-embedqa-e5-v5"
```

A custom endpoint with no `model` set is refused rather than silently 404ing:
those endpoints do not serve OpenAI's catalogue, so there is no safe default.

---

## The orchestrator

A skill-routing layer that keeps an honest record of its own decisions and
proposes improvements to itself from that record.

**Routing.** Every query is matched against trigger phrases in
`skills/<branch>/SKILL.md`, then resolved against the concrete projects
(`entities`) the query actually names. If resolution needs a branch that trigger
matching missed, that mid-turn correction is recorded. The outcome signal —
`clean`, `corrected`, or `unused` — is a comparison of two sets, not a
model-judged confidence score. There is no confidence score anywhere in the
schema.

**The log.** Decisions append to `memory/events.jsonl`, one JSON object per
line. It is opened for writing in exactly one function, always with `O_APPEND`.
Each record stores the line number it was written at, so `nexus events --verify`
detects a hand-edit, reorder, or deletion as a sequence mismatch.

**Self-review.** `nexus evolve` reads that log, finds recurring friction, and
proposes **one** minimal edit to **one** `SKILL.md` — with a plain-English
reason, the exact events that motivated it cited by id *and* line number, and a
diff. It waits for an explicit `y/n`. On approval it writes a vault note
containing the full pre-edit file content, which is what makes
`nexus evolve --revert <id>` restore the file byte for byte. On rejection it
records a fingerprint of the edit so the identical proposal is never offered
again.

When the evidence thresholds in `AGENTIC_OS.md` are not met, it says
**"not enough signal yet"** and proposes nothing.

**Guardrails, enforced in code.** The orchestrator may write
`skills/*/SKILL.md` and nothing else. Paths are checked after `resolve()`, so
neither a symlink nor `..` widens the scope. `AGENTIC_OS.md`, the pointer files,
and the orchestrator's own source are refused. Deny-by-default — see
`backend/orchestrator/guardrails.py`.

**Replay.** `nexus replay` is a utility in the sense `git log` is one. It reads
the same append-only log live operation writes, and renders through the same
function (`render.render_line`). There is no recorded demo because there is no
recording step — only history, and the ability to look at it. There is no demo
mode, presentation mode, or any code path that behaves differently when someone
is watching.

```
AGENTIC_OS.md          routing rules — immutable to the orchestrator
skills/                dev · trading · shared, pointers to real projects
memory/events.jsonl    append-only decision log
vault/                 markdown notes, git-tracked, opens in Obsidian
hud/                   dashboard, reads vault/ and memory/ directly
```

> **Note:** the orchestrator currently runs from a clone of this repo, because
> `AGENTIC_OS.md`, `skills/` and `hud/` live at the repo root rather than inside
> the installed package. `pip install opennexus-ai` gives you the assistant
> (`ask`, `chat`, `digest`, `serve`); clone the repo for the orchestrator.

---

## Configuration

`nexus init` creates `nexus.toml`. Key fields:

```toml
[user]
name = "Alex"
timezone = "America/New_York"
role = "developer"          # tunes digest tone

[llm]
provider = "ollama"         # "openai" | "anthropic" | "ollama"
model = "llama3.2"
api_key = ""                # leave empty for ollama

[digest]
hour = 7                    # 7 AM daily briefing
weather_lat = 40.71
weather_lon = -74.01
rss_feeds = [
  "https://hnrss.org/frontpage",
]
```

Full example: [`nexus.toml.example`](nexus.toml.example)

---

## Architecture

```
nexus.toml ──► CLI (typer)
                  │
                  ▼
           FastAPI backend ◄──► SQLite + ChromaDB
                  │
          ┌───────┴────────┐
          ▼                ▼
     Connectors         LLM layer
  (Gmail, Notion,    (Ollama / OpenAI /
   GitHub, etc.)      Anthropic)
          │
          ▼
    React frontend
    (localhost:8000)
```

- **Backend**: FastAPI + SQLModel + ChromaDB (vector store for RAG)
- **Frontend**: React + TypeScript + Vite
- **Scheduler**: APScheduler for daily digest
- **Storage**: local SQLite — no cloud required

---

## Self-Hosting

OpenNexus is designed to run on your machine or a home server. No accounts, no SaaS, no telemetry.

```bash
# Run as a service (example with systemd)
pip install opennexus-ai
nexus init
# then configure a systemd/launchd unit pointing to `nexus serve`
```

Docker support: [coming soon — PRs welcome!](https://github.com/kaorii-ako/OpenNexus/issues)

---

## Roadmap

- [ ] Docker image
- [ ] Spotify connector
- [ ] Telegram connector  
- [ ] Linear / Jira integration
- [ ] Mobile-friendly UI
- [ ] Plugin API for custom connectors
- [ ] Scheduled summaries via email/Discord

[Open an issue](https://github.com/kaorii-ako/OpenNexus/issues) to request features or vote on existing ones.

---

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
git clone https://github.com/kaorii-ako/OpenNexus
cd OpenNexus
uv sync
cd frontend && npm install
```

Good first issues labeled [`good first issue`](https://github.com/kaorii-ako/OpenNexus/labels/good%20first%20issue).

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kaorii-ako/OpenNexus&type=Date)](https://star-history.com/#kaorii-ako/OpenNexus&Date)

---

<div align="center">
  <sub>Built with ❤️ · MIT License · <a href="https://github.com/kaorii-ako/OpenNexus/issues">Issues</a> · <a href="https://github.com/kaorii-ako/OpenNexus/discussions">Discussions</a></sub>
</div>
