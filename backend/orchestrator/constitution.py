"""Reads the machine-readable config block out of AGENTIC_OS.md.

AGENTIC_OS.md is prose *and* configuration in one file, on purpose: the routing
policy a human reads and the routing policy the code executes cannot drift apart
if there is only one copy of it. This module extracts the fenced ```toml block.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:  # pragma: no cover - Python 3.10
    import tomli as tomllib  # type: ignore[no-redef]

from backend.orchestrator.paths import agentic_os_path

_TOML_BLOCK = re.compile(r"```toml\s*\n(.*?)\n```", re.DOTALL)

DEFAULTS: dict[str, Any] = {
    "routing": {
        "branches": ["dev", "trading", "shared"],
        "always_load": ["shared"],
        "match": "word_boundary_ci",
        "min_trigger_len": 3,
    },
    "evolve": {
        "min_events": 12,
        "min_pattern_occurrences": 3,
        "max_proposals_per_run": 1,
    },
    "guardrails": {
        "writable_globs": ["skills/*/SKILL.md"],
        "never_writable": ["AGENTIC_OS.md", "backend/orchestrator/*.py"],
    },
}


class ConstitutionError(RuntimeError):
    """AGENTIC_OS.md is missing or has no parseable config block."""


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key].update(value)
        else:
            out[key] = value
    return out


def load(path: Path | None = None) -> dict[str, Any]:
    """Parse AGENTIC_OS.md's config block, merged over defaults."""
    target = path or agentic_os_path()
    if not target.is_file():
        raise ConstitutionError(
            f"AGENTIC_OS.md not found at {target}. The orchestrator cannot route "
            "without its routing rules. Run `nexus setup` to scaffold it."
        )

    text = target.read_text(encoding="utf-8")
    match = _TOML_BLOCK.search(text)
    if not match:
        raise ConstitutionError(
            f"{target} contains no ```toml configuration block. "
            "The machine-read section is required."
        )

    parsed = tomllib.loads(match.group(1))
    return _merge(DEFAULTS, parsed)


@lru_cache(maxsize=1)
def _cached(path_str: str, mtime: float) -> dict[str, Any]:
    return load(Path(path_str))


def get() -> dict[str, Any]:
    """Cached load, invalidated when AGENTIC_OS.md changes on disk."""
    target = agentic_os_path()
    try:
        mtime = target.stat().st_mtime
    except OSError:
        return load(target)
    return _cached(str(target), mtime)
