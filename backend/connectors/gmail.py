from __future__ import annotations
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
    "https://www.googleapis.com/auth/classroom.announcements.readonly",
]


def _load_creds(data_dir: Path) -> Credentials | None:
    token_path = data_dir / "gmail_token.json"
    if not token_path.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    return creds


class GmailConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("gmail", False, "No credentials — run: nexus connect google")
        try:
            svc = build("gmail", "v1", credentials=self._creds)
            svc.users().getProfile(userId="me").execute()
            return HealthResult("gmail", True)
        except Exception as e:
            return HealthResult("gmail", False, str(e))

    def unread_count(self) -> dict:
        if not self._creds:
            return {"count": 0, "top_sender": None}
        try:
            svc = build("gmail", "v1", credentials=self._creds)
            result = svc.users().messages().list(
                userId="me", q="is:unread", maxResults=10
            ).execute()
            count = result.get("resultSizeEstimate", 0)
            messages = result.get("messages", [])
            top_sender = None
            if messages:
                msg = svc.users().messages().get(
                    userId="me", id=messages[0]["id"],
                    format="metadata", metadataHeaders=["From"]
                ).execute()
                headers = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                top_sender = headers.get("From")
            return {"count": count, "top_sender": top_sender}
        except Exception:
            return {"count": 0, "top_sender": None}
