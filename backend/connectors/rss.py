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
