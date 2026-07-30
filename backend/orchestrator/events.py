"""Append-only event log — the source of truth for the whole orchestrator.

Every routing decision, every evolution proposal, approval, rejection and revert
lands here as one JSON object on one line. Live operation writes it; `nexus
replay` and the HUD read it. There is no second store and no separate recording.

Append-only is a real property of this module, not a description of intent: the
log file is opened with mode "a" in exactly one place (`EventLog.append`) and
nowhere in this codebase is it opened for writing or truncation. `verify()`
provides tamper evidence by checking that each record's stored `seq` matches its
actual line number, which a hand-edit or deletion would break.
"""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.orchestrator.paths import events_path

# --- event types -------------------------------------------------------------

ROUTE = "route"
ANSWER = "answer"
EVOLVE_PROPOSED = "evolve_proposed"
EVOLVE_APPLIED = "evolve_applied"
EVOLVE_REJECTED = "evolve_rejected"
EVOLVE_REVERTED = "evolve_reverted"
EVOLVE_NO_SIGNAL = "evolve_no_signal"

ALL_TYPES = (
    ROUTE,
    ANSWER,
    EVOLVE_PROPOSED,
    EVOLVE_APPLIED,
    EVOLVE_REJECTED,
    EVOLVE_REVERTED,
    EVOLVE_NO_SIGNAL,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_run_id() -> str:
    """One run id per CLI invocation, so a turn's events group together."""
    return f"run_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{secrets.token_hex(3)}"


def _new_event_id() -> str:
    return f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{secrets.token_hex(4)}"


@dataclass
class Event:
    """One logged fact. `seq` is the 1-indexed line number in events.jsonl."""

    id: str
    seq: int
    ts: str
    run_id: str
    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "seq": self.seq,
            "ts": self.ts,
            "run_id": self.run_id,
            "type": self.type,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Event":
        return cls(
            id=raw.get("id", ""),
            seq=int(raw.get("seq", 0)),
            ts=raw.get("ts", ""),
            run_id=raw.get("run_id", ""),
            type=raw.get("type", ""),
            payload=raw.get("payload", {}) or {},
        )

    @property
    def dt(self) -> datetime | None:
        try:
            return datetime.fromisoformat(self.ts)
        except (ValueError, TypeError):
            return None

    def cite(self) -> str:
        """How this event is referenced in a vault note — id plus line number."""
        return f"{self.id} (events.jsonl:{self.seq})"


class EventLog:
    """Append-only reader/writer over memory/events.jsonl."""

    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path is not None else events_path()

    # --- writing -------------------------------------------------------------

    def append(self, type: str, payload: dict[str, Any], run_id: str) -> Event:
        """Append one event. The only write path to the log in this codebase."""
        if type not in ALL_TYPES:
            raise ValueError(f"unknown event type: {type!r}")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        seq = self.count() + 1
        event = Event(
            id=_new_event_id(),
            seq=seq,
            ts=_now_iso(),
            run_id=run_id,
            type=type,
            payload=payload,
        )
        line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True)

        # O_APPEND: the kernel places the write at end-of-file atomically, so a
        # concurrent `nexus route` in another shell cannot interleave or clobber.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, (line + "\n").encode("utf-8"))
        finally:
            os.close(fd)
        return event

    # --- reading -------------------------------------------------------------

    def exists(self) -> bool:
        return self.path.is_file()

    def count(self) -> int:
        if not self.path.is_file():
            return 0
        with open(self.path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())

    def iter_events(self) -> Iterator[Event]:
        """Yield every well-formed event. Malformed lines are skipped, not
        repaired — `verify()` is what reports them."""
        if not self.path.is_file():
            return
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield Event.from_dict(json.loads(line))
                except (json.JSONDecodeError, TypeError, ValueError):
                    continue

    def read_all(self) -> list[Event]:
        return list(self.iter_events())

    def read_run(self, run_id: str) -> list[Event]:
        return [e for e in self.iter_events() if e.run_id == run_id]

    def read_since(self, since: datetime) -> list[Event]:
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        out = []
        for e in self.iter_events():
            dt = e.dt
            if dt is not None and dt >= since:
                out.append(e)
        return out

    def by_type(self, *types: str) -> list[Event]:
        wanted = set(types)
        return [e for e in self.iter_events() if e.type in wanted]

    def find(self, event_id: str) -> Event | None:
        for e in self.iter_events():
            if e.id == event_id:
                return e
        return None

    def runs(self) -> list[str]:
        """Run ids in first-seen order."""
        seen: list[str] = []
        for e in self.iter_events():
            if e.run_id and e.run_id not in seen:
                seen.append(e.run_id)
        return seen

    # --- integrity -----------------------------------------------------------

    def verify(self) -> list[str]:
        """Return a list of integrity problems. Empty means the log is intact.

        A hand-edited, reordered, or partially deleted log shows up here as a
        seq mismatch, because seq is assigned at append time from the then-current
        line count and never recomputed.
        """
        problems: list[str] = []
        if not self.path.is_file():
            return problems

        seen_ids: set[str] = set()
        with open(self.path, "r", encoding="utf-8") as f:
            line_no = 0
            for raw in f:
                if not raw.strip():
                    continue
                line_no += 1
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    problems.append(f"line {line_no}: not valid JSON ({exc.msg})")
                    continue

                event = Event.from_dict(data)
                if event.seq != line_no:
                    problems.append(
                        f"line {line_no}: seq mismatch — record claims seq={event.seq}. "
                        "The log has been edited, reordered, or had lines removed."
                    )
                if not event.id:
                    problems.append(f"line {line_no}: missing event id")
                elif event.id in seen_ids:
                    problems.append(f"line {line_no}: duplicate event id {event.id}")
                seen_ids.add(event.id)

                if event.type not in ALL_TYPES:
                    problems.append(f"line {line_no}: unknown event type {event.type!r}")
                if event.dt is None:
                    problems.append(f"line {line_no}: unparseable timestamp {event.ts!r}")

        return problems
