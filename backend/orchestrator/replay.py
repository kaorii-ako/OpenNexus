"""Replay — look at history.

This is a utility in the same sense `git log` is a utility. It selects real
events from memory/events.jsonl and re-emits them through `render.render_line`,
which is the identical function live routing uses to print. There is no
recording step, because there is nothing to record: the log is written by normal
operation and replay only reads it.

Consequently there is no state anywhere in this module that live operation could
consult, and nothing here can be triggered from the routing path.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

from backend.orchestrator.events import Event, EventLog

ORIGINAL = "original"
FIXED = "fixed"

# An event gap longer than this is compressed — reviewing a week of routing
# should not mean waiting a week. The compression is reported, not hidden.
MAX_GAP_SECONDS = 3.0


class SelectionError(ValueError):
    """The requested run id or timestamp selected nothing."""


def parse_since(value: str) -> datetime:
    """Accept an ISO timestamp, a date, or a relative form like `2h`, `30m`, `7d`."""
    text = value.strip()

    relative_units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}
    if len(text) > 1 and text[-1].lower() in relative_units and text[:-1].isdigit():
        amount = int(text[:-1])
        delta = timedelta(**{relative_units[text[-1].lower()]: amount})
        return datetime.now(timezone.utc) - delta

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SelectionError(
            f"could not read --since {value!r}. Use an ISO timestamp "
            "(2026-07-27T10:00:00), a date (2026-07-27), or a relative span (2h, 30m, 7d)."
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass
class Selection:
    events: list[Event]
    description: str


def select(
    log: EventLog,
    run: str | None = None,
    since: str | None = None,
    last: int | None = None,
) -> Selection:
    """Choose which real events to replay. Never fabricates or pads."""
    if run:
        chosen = log.read_run(run)
        if not chosen:
            known = log.runs()
            hint = f" Known runs: {', '.join(known[-5:])}" if known else " The log is empty."
            raise SelectionError(f"no events for run {run!r}.{hint}")
        return Selection(chosen, f"run {run}")

    if since:
        cutoff = parse_since(since)
        chosen = log.read_since(cutoff)
        if not chosen:
            raise SelectionError(
                f"no events since {cutoff.isoformat()}. Nothing happened in that window."
            )
        return Selection(chosen, f"since {cutoff.isoformat()}")

    chosen = log.read_all()
    if not chosen:
        raise SelectionError(
            "memory/events.jsonl is empty — there is no history to replay yet. "
            "Run `nexus route \"...\"` or `nexus ask \"...\"` first."
        )
    if last:
        chosen = chosen[-last:]
        return Selection(chosen, f"last {len(chosen)} event(s)")
    return Selection(chosen, f"all {len(chosen)} event(s)")


def pace(
    events: list[Event],
    mode: str = ORIGINAL,
    speed: float = 1.0,
    interval: float = 0.4,
    max_gap: float = MAX_GAP_SECONDS,
) -> Iterator[tuple[Event, float]]:
    """Yield (event, delay_before_emitting) pairs.

    In `original` mode the real inter-event gaps from the log are used, divided
    by `speed` and capped at `max_gap`. In `fixed` mode every gap is `interval`.
    """
    previous: datetime | None = None
    for event in events:
        if mode == FIXED:
            delay = interval
        else:
            current = event.dt
            if previous is None or current is None:
                delay = 0.0
            else:
                delay = max(0.0, (current - previous).total_seconds())
                delay = min(delay, max_gap)
            if current is not None:
                previous = current
        yield event, (delay / speed if speed > 0 else 0.0)


def run(
    selection: Selection,
    emit: Callable[[Event], None],
    mode: str = ORIGINAL,
    speed: float = 1.0,
    interval: float = 0.4,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Drive a replay, calling `emit` per event. Returns the number emitted."""
    count = 0
    for event, delay in pace(selection.events, mode=mode, speed=speed, interval=interval):
        if delay > 0:
            sleep(delay)
        emit(event)
        count += 1
    return count
