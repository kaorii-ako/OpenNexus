from __future__ import annotations
import json
from pathlib import Path
from datetime import date
import httpx
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._token = self._load_token()

    def _load_token(self) -> str | None:
        p = Path(self._cfg.data_dir) / "notion.json"
        if p.exists():
            return json.loads(p.read_text())["token"]
        return None

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._token:
            return HealthResult("notion", False, "No token — run: nexus connect notion")
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{NOTION_API}/users/me", headers=self._headers())
                r.raise_for_status()
            return HealthResult("notion", True)
        except Exception as e:
            return HealthResult("notion", False, str(e))

    async def search_pages(self, query: str) -> list[dict]:
        if not self._token:
            return []
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(
                f"{NOTION_API}/search",
                headers=self._headers(),
                json={"query": query, "filter": {"value": "page", "property": "object"}},
            )
            r.raise_for_status()
            return r.json().get("results", [])

    async def get_page_content(self, page_id: str) -> str:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=self._headers(),
            )
            r.raise_for_status()
            blocks = r.json().get("results", [])
        return self._blocks_to_md(blocks)

    def _blocks_to_md(self, blocks: list[dict]) -> str:
        lines = []
        for b in blocks:
            t = b.get("type", "")
            block = b.get(t, {})
            rich_text = block.get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich_text)
            if t == "heading_1":
                lines.append(f"# {text}")
            elif t == "heading_2":
                lines.append(f"## {text}")
            elif t == "heading_3":
                lines.append(f"### {text}")
            elif t in ("paragraph", "quote"):
                lines.append(text)
            elif t == "bulleted_list_item":
                lines.append(f"- {text}")
            elif t == "numbered_list_item":
                lines.append(f"1. {text}")
            elif t == "to_do":
                checked = "x" if block.get("checked") else " "
                lines.append(f"- [{checked}] {text}")
            elif t == "code":
                lang = block.get("language", "")
                lines.append(f"```{lang}\n{text}\n```")
        return "\n".join(lines)

    async def get_all_pages(self) -> list[dict]:
        if not self._token:
            return []
        pages = []
        cursor = None
        async with httpx.AsyncClient(timeout=20) as c:
            while True:
                body: dict = {
                    "filter": {"value": "page", "property": "object"},
                    "page_size": 100,
                }
                if cursor:
                    body["start_cursor"] = cursor
                r = await c.post(
                    f"{NOTION_API}/search",
                    headers=self._headers(),
                    json=body,
                )
                r.raise_for_status()
                data = r.json()
                pages.extend(data.get("results", []))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
        return pages

    async def append_to_daily_notes(self, text: str) -> None:
        if not self._token:
            return
        today = date.today().isoformat()
        pages = await self.search_pages(f"Daily Notes {today}")
        if not pages:
            return
        page_id = pages[0]["id"]
        async with httpx.AsyncClient(timeout=10) as c:
            await c.patch(
                f"{NOTION_API}/blocks/{page_id}/children",
                headers=self._headers(),
                json={
                    "children": [{
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": text}}]
                        },
                    }]
                },
            )

    async def create_idea(self, text: str) -> None:
        if not self._token:
            return
        pages = await self.search_pages("Ideas")
        if not pages:
            return
        db_id = pages[0].get("id")
        async with httpx.AsyncClient(timeout=10) as c:
            await c.post(
                f"{NOTION_API}/pages",
                headers=self._headers(),
                json={
                    "parent": {"database_id": db_id},
                    "properties": {
                        "title": {"title": [{"text": {"content": text}}]}
                    },
                },
            )

    async def scaffold_workspace(self) -> None:
        if not self._token:
            raise ValueError("No Notion token — run: nexus connect notion")
        DATABASES = {
            "📅 Daily Notes": {"Date": {"date": {}}, "Weather": {"rich_text": {}}, "Mood": {"select": {}}},
            "🚀 Projects": {"Status": {"select": {}}, "Domain": {"rich_text": {}}, "GitHub": {"url": {}}},
            "🔬 Research": {"Tags": {"multi_select": {}}, "Status": {"select": {}}},
            "🎓 Courses": {"Code": {"rich_text": {}}, "Professor": {"rich_text": {}}, "Exam Date": {"date": {}}},
            "💡 Ideas": {"Tags": {"multi_select": {}}, "Priority": {"select": {}}},
            "👥 People": {"Role": {"rich_text": {}}, "Contact": {"email": {}}},
            "📚 Resources": {"URL": {"url": {}}, "Tags": {"multi_select": {}}},
        }
        async with httpx.AsyncClient(timeout=20) as c:
            root = await c.post(
                f"{NOTION_API}/pages",
                headers=self._headers(),
                json={
                    "parent": {"type": "workspace", "workspace": True},
                    "properties": {
                        "title": {"title": [{"text": {"content": "NEXUS Workspace"}}]}
                    },
                },
            )
            root.raise_for_status()
            root_id = root.json()["id"]

            for name, extra_props in DATABASES.items():
                props = {"Name": {"title": {}}}
                props.update(extra_props)
                await c.post(
                    f"{NOTION_API}/databases",
                    headers=self._headers(),
                    json={
                        "parent": {"page_id": root_id},
                        "title": [{"text": {"content": name}}],
                        "properties": props,
                    },
                )
