from __future__ import annotations
import asyncio
from datetime import date
from rich.console import Console
from rich.panel import Panel
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
