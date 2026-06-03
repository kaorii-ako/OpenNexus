# Show HN: OpenNexus – self-hosted personal AI briefing + chat with your own data

**Title:** Show HN: OpenNexus – self-hosted AI that reads your email, calendar, Notion, GitHub and gives you a morning briefing

**Body:**

I built OpenNexus because I was tired of AI tools that know nothing about my actual life.

It's a self-hosted Python app that:
- Runs a morning digest every day (email, calendar, GitHub PRs, assignments, RSS, weather)
- Lets you chat with your Notion workspace via RAG
- Works with Ollama locally (nothing leaves your machine), OpenAI, or Anthropic
- Connects to Gmail, Google Calendar, Google Classroom, GitHub, Discord, RSS, Weather

```
pip install opennexus-ai
nexus init    # interactive wizard
nexus serve   # → http://localhost:8000
```

I'm a student and built this for myself — I have Gmail, Google Classroom, Notion, and GitHub spread across 5 tabs every morning. OpenNexus collapses all of that into one briefing + a chat interface.

Stack: FastAPI + SQLModel + ChromaDB (RAG) + React/TypeScript. SQLite for storage — no cloud required.

GitHub: https://github.com/kaorii-ako/OpenNexus
PyPI: https://pypi.org/project/opennexus-ai/

Happy to answer questions about architecture, the RAG approach, or the LLM abstraction layer.

---

**Best time to post:** Tuesday–Thursday, 8–10 AM US Eastern
**Target:** Hacker News front page → "Show HN"
