"""Code-enforced write scope for self-modification.

The orchestrator may edit skill trigger lists and nothing else. That is not a
policy note in a prompt — it is this module, and every write the evolution
system performs goes through `write()` here.

The enforcement model is deny-by-default on the *resolved* path:

  * the path is resolved with `Path.resolve()`, which collapses `..` and follows
    symlinks, so neither can be used to escape the allowlist;
  * a resolved path outside the repo root is refused outright;
  * `never_writable` patterns are checked first and are unconditional;
  * the write proceeds only if the resolved relative path matches one of
    `writable_globs`. Anything not explicitly permitted is refused.

Patterns are matched with `PurePath.match`, which is path-component aware —
unlike `fnmatch`, whose `*` would happily cross directory separators and let
`skills/a/b/SKILL.md` satisfy `skills/*/SKILL.md`.
"""
from __future__ import annotations

from pathlib import Path, PurePath
from typing import Any

from backend.orchestrator import constitution
from backend.orchestrator.paths import repo_root


class GuardrailViolation(PermissionError):
    """A write was attempted outside the permitted scope. Never caught-and-ignored."""


def _guard_config(config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or constitution.get()
    return cfg.get("guardrails", {})


def writable_globs(config: dict[str, Any] | None = None) -> list[str]:
    return list(_guard_config(config).get("writable_globs", []))


def never_writable(config: dict[str, Any] | None = None) -> list[str]:
    return list(_guard_config(config).get("never_writable", []))


def relative_to_root(path: Path) -> PurePath | None:
    """Resolved path relative to the repo root, or None if it escapes the root."""
    root = repo_root().resolve()
    resolved = Path(path).resolve()
    try:
        return PurePath(resolved.relative_to(root))
    except ValueError:
        return None


def check(path: Path | str, config: dict[str, Any] | None = None) -> Path:
    """Raise GuardrailViolation unless `path` is within the permitted write scope.

    Returns the resolved path on success.
    """
    target = Path(path)
    resolved = target.resolve()
    rel = relative_to_root(target)

    if rel is None:
        raise GuardrailViolation(
            f"refused: {resolved} resolves outside the repo root {repo_root()}. "
            "The orchestrator may only write inside its own repository."
        )

    for pattern in never_writable(config):
        if rel.match(pattern):
            raise GuardrailViolation(
                f"refused: {rel} matches never_writable pattern '{pattern}' in "
                "AGENTIC_OS.md. This path is permanently outside the orchestrator's "
                "write scope."
            )

    allowed = writable_globs(config)
    for pattern in allowed:
        if rel.match(pattern):
            return resolved

    raise GuardrailViolation(
        f"refused: {rel} matches none of the writable_globs {allowed} declared in "
        "AGENTIC_OS.md. Writes are deny-by-default; the orchestrator can only edit "
        "skill trigger lists."
    )


def is_writable(path: Path | str, config: dict[str, Any] | None = None) -> bool:
    try:
        check(path, config)
        return True
    except GuardrailViolation:
        return False


def write(path: Path | str, content: str, config: dict[str, Any] | None = None) -> Path:
    """The only sanctioned write path for orchestrator self-modification."""
    target = check(path, config)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def describe_scope(config: dict[str, Any] | None = None) -> str:
    """Human-readable summary, shown before every proposal and in the HUD."""
    allowed = writable_globs(config)
    denied = never_writable(config)
    lines = ["writable:"]
    lines += [f"  + {g}" for g in allowed] or ["  (nothing)"]
    lines.append("never writable:")
    lines += [f"  - {g}" for g in denied] or ["  (nothing)"]
    lines.append("everything else: refused (deny-by-default)")
    return "\n".join(lines)
