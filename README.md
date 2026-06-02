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
