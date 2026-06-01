from __future__ import annotations
from datetime import datetime
from pathlib import Path
from backend.core.config import NexusConfig
from backend.connectors.notion import NotionConnector


class NotionSync:
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._connector = NotionConnector(cfg)
        self._cache_dir = Path(cfg.notion_cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    async def sync_all(self) -> list[Path]:
        pages = await self._connector.get_all_pages()
        updated = []
        for page in pages:
            page_id = page["id"]
            title = self._extract_title(page)
            try:
                content = await self._connector.get_page_content(page_id)
                md_path = self._cache_dir / f"{page_id}.md"
                frontmatter = (
                    f"---\npage_id: {page_id}\ntitle: {title}\n"
                    f"synced: {datetime.utcnow().isoformat()}\n---\n\n"
                )
                md_path.write_text(
                    frontmatter + f"# {title}\n\n" + content,
                    encoding="utf-8",
                )
                updated.append(md_path)
            except Exception:
                continue
        return updated

    def _extract_title(self, page: dict) -> str:
        props = page.get("properties", {})
        for key in ("title", "Title", "Name"):
            if key in props:
                title_obj = props[key]
                rich = title_obj.get("title", []) or title_obj.get("rich_text", [])
                if rich:
                    return rich[0].get("plain_text", "Untitled")
        return "Untitled"
