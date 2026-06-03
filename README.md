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
