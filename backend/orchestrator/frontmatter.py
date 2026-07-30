"""Minimal YAML frontmatter reader/writer.

Deliberately hand-rolled rather than pulling in PyYAML: the vault format is one
we define and document ourselves (see `skills/shared/vault-writer.md`), it is
restricted to scalars and string lists, and keeping it dependency-free means the
vault stays plain markdown that any editor — or Obsidian — can open.

Supported:
    key: value
    key: [a, b, c]
    key:
      - a
      - b
"""
from __future__ import annotations

from typing import Any

DELIM = "---"


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Split a document into (frontmatter dict, body).

    A document with no frontmatter returns ({}, original text).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != DELIM:
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == DELIM:
            end = i
            break
    if end is None:
        return {}, text

    data: dict[str, Any] = {}
    pending_key: str | None = None

    for raw in lines[1:end]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and pending_key is not None:
            data.setdefault(pending_key, [])
            if isinstance(data[pending_key], list):
                data[pending_key].append(_unquote(stripped[2:]))
            continue

        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()

        if not value:
            # Either a block list follows, or an empty scalar.
            pending_key = key
            data[key] = []
            continue

        pending_key = None
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [_unquote(p) for p in inner.split(",") if p.strip()] if inner else []
        else:
            data[key] = _unquote(value)

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return data, body


def _render_value(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "[]"
        return "[" + ", ".join(str(v) for v in value) + "]"
    return str(value)


def dump(data: dict[str, Any], body: str) -> str:
    """Render frontmatter + body back to a document."""
    lines = [DELIM]
    for key, value in data.items():
        lines.append(f"{key}: {_render_value(value)}")
    lines.append(DELIM)
    lines.append("")
    return "\n".join(lines) + body.lstrip("\n")


def as_list(value: Any) -> list[str]:
    """Coerce a frontmatter value to a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    return [text] if text else []
