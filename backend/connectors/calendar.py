from __future__ import annotations
from datetime import datetime, timezone
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig
from backend.connectors.gmail import _load_creds


class CalendarConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("calendar", False, "No credentials — run: nexus connect google")
        return HealthResult("calendar", True)

    def today_events(self) -> list[dict]:
        if not self._creds:
            return []
        try:
            svc = build("calendar", "v3", credentials=self._creds)
            now = datetime.now(timezone.utc)
            end = now.replace(hour=23, minute=59, second=59)
            result = svc.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
                maxResults=10,
            ).execute()
            events = []
            for e in result.get("items", []):
                start = (
                    e.get("start", {}).get("dateTime")
                    or e.get("start", {}).get("date", "")
                )
                events.append({"summary": e.get("summary", "?"), "start": start})
            return events
        except Exception:
            return []
