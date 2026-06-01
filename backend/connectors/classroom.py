from __future__ import annotations
from datetime import datetime, timezone, timedelta
from googleapiclient.discovery import build
from backend.connectors.base import ConnectorBase, HealthResult
from backend.core.config import NexusConfig
from backend.connectors.gmail import _load_creds


class ClassroomConnector(ConnectorBase):
    def __init__(self, cfg: NexusConfig):
        self._cfg = cfg
        self._creds = _load_creds(cfg.data_dir)

    async def connect(self) -> None:
        pass

    async def health(self) -> HealthResult:
        if not self._creds:
            return HealthResult("classroom", False, "No credentials — run: nexus connect google")
        try:
            svc = build("classroom", "v1", credentials=self._creds)
            svc.courses().list(pageSize=1).execute()
            return HealthResult("classroom", True)
        except Exception as e:
            return HealthResult("classroom", False, str(e))

    def due_soon(self, hours: int = 48) -> list[dict]:
        if not self._creds:
            return []
        try:
            svc = build("classroom", "v1", credentials=self._creds)
            courses = svc.courses().list(
                courseStates=["ACTIVE"]
            ).execute().get("courses", [])
            due = []
            cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
            for course in courses:
                cid = course["id"]
                cname = course.get("name", "?")
                works = svc.courses().courseWork().list(
                    courseId=cid, orderBy="dueDate"
                ).execute().get("courseWork", [])
                for w in works:
                    due_date = w.get("dueDate")
                    if not due_date:
                        continue
                    due_dt = datetime(
                        due_date["year"],
                        due_date["month"],
                        due_date["day"],
                        tzinfo=timezone.utc,
                    )
                    if due_dt <= cutoff:
                        due.append({
                            "course": cname,
                            "title": w.get("title", "?"),
                            "due": due_dt.isoformat(),
                        })
            return sorted(due, key=lambda x: x["due"])
        except Exception:
            return []

    def announcements(self) -> list[dict]:
        if not self._creds:
            return []
        try:
            svc = build("classroom", "v1", credentials=self._creds)
            courses = svc.courses().list(
                courseStates=["ACTIVE"]
            ).execute().get("courses", [])
            ann = []
            for course in courses:
                cid = course["id"]
                cname = course.get("name", "?")
                items = svc.courses().announcements().list(
                    courseId=cid, pageSize=5
                ).execute().get("announcements", [])
                for a in items:
                    ann.append({
                        "course": cname,
                        "text": a.get("text", "")[:200],
                        "creation_time": a.get("creationTime", ""),
                    })
            return ann
        except Exception:
            return []
