"""Filesystem layout for the orchestrator.

Every other orchestrator module resolves paths through here so that the repo
root is discovered once, consistently, and can be redirected in tests via the
NEXUS_ROOT environment variable.
"""
from __future__ import annotations
import os
from pathlib import Path

ROOT_MARKER = "AGENTIC_OS.md"


def repo_root() -> Path:
    """Locate the repo root: the directory holding AGENTIC_OS.md.

    Walks up from the current working directory, then falls back to the package
    location so the CLI works when invoked from a subdirectory.
    """
    override = os.environ.get("NEXUS_ROOT")
    if override:
        return Path(override).expanduser().resolve()

    for base in (Path.cwd(), Path(__file__).resolve().parent.parent.parent):
        candidate = base.resolve()
        for parent in (candidate, *candidate.parents):
            if (parent / ROOT_MARKER).is_file():
                return parent

    # No marker found — fall back to the package's own repo directory. Callers
    # that need the marker (router, guardrails) will surface a clear error.
    return Path(__file__).resolve().parent.parent.parent


def agentic_os_path() -> Path:
    return repo_root() / ROOT_MARKER


def skills_dir() -> Path:
    return repo_root() / "skills"


def vault_dir() -> Path:
    return repo_root() / "vault"


def memory_dir() -> Path:
    return repo_root() / "memory"


def events_path() -> Path:
    return memory_dir() / "events.jsonl"


def hud_dir() -> Path:
    return repo_root() / "hud"
