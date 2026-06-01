from __future__ import annotations
import json
from pathlib import Path
from github import Github
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig


class GitHubConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        token_path = Path(cfg.data_dir) / "github.json"
        self._token = json.loads(token_path.read_text())["token"] if token_path.exists() else None
        self._gh = Github(self._token) if self._token else None

    async def connect(self) -> None: pass

    async def health(self) -> HealthResult:
        if not self._gh:
            return HealthResult("github", False, "No token")
        try:
            self._gh.get_user().login
            return HealthResult("github", True)
        except Exception as e:
            return HealthResult("github", False, str(e))

    def open_prs(self) -> list[dict]:
        if not self._gh:
            return []
        prs = self._gh.search_issues("is:open is:pr author:@me")
        return [{"title": pr.title, "repo": pr.repository.full_name if hasattr(pr, "repository") else "?",
                 "url": pr.html_url} for pr in list(prs)[:5]]

    def notifications(self) -> list[dict]:
        if not self._gh:
            return []
        user = self._gh.get_user()
        notifs = user.get_notifications(all=False)
        return [{"subject": n.subject.title, "type": n.subject.type,
                 "repo": n.repository.full_name} for n in list(notifs)[:5]]
