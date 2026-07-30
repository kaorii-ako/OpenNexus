"""Markdown vault — plain files, YAML frontmatter, no database.

Two kinds of note are written here by code: domain work, and orchestrator
self-edit records. Nothing else is generated. The vault opens directly as an
Obsidian vault; `vault/README.md` documents the convention for humans, and
`skills/shared/vault-writer.md` documents it for the agent.

Self-edit notes carry the complete pre-edit file content between explicit
markers. That is what makes `nexus evolve --revert` possible: the note is not a
summary of the change, it is the change plus everything needed to undo it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.orchestrator import frontmatter
from backend.orchestrator.paths import vault_dir

PRE_EDIT_START = "<!-- nexus:pre-edit-content:start -->"
PRE_EDIT_END = "<!-- nexus:pre-edit-content:end -->"
# Eight backticks: long enough that any fence inside a captured SKILL.md cannot
# terminate the block early.
FENCE = "````````"

_PRE_EDIT_BLOCK = re.compile(
    re.escape(PRE_EDIT_START) + r"\s*\n" + re.escape(FENCE) + r"[^\n]*\n(.*?)\n?" + re.escape(FENCE) + r"\s*\n" + re.escape(PRE_EDIT_END),
    re.DOTALL,
)
_WIKILINK = re.compile(r"\[\[([^\]|#]+)")
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_STRIP.sub("-", text.lower()).strip("-") or "note"


@dataclass
class Note:
    path: Path
    meta: dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def domain(self) -> str:
        return str(self.meta.get("domain", "") or "unknown")

    @property
    def title(self) -> str:
        for line in self.body.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return self.name

    def links(self) -> list[str]:
        """Outbound edges. Frontmatter `links:` is authoritative per AGENTIC_OS.md;
        inline [[wikilinks]] in the body are additionally collected so a note
        written by hand in Obsidian still shows up in the graph."""
        out = list(frontmatter.as_list(self.meta.get("links")))
        for match in _WIKILINK.finditer(self.body):
            target = match.group(1).strip()
            if target and target not in out:
                out.append(target)
        return out

    def pre_edit_content(self) -> str | None:
        """The captured pre-edit file content, if this is a self-edit note."""
        match = _PRE_EDIT_BLOCK.search(self.body)
        return match.group(1) if match else None


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_note(
    slug: str,
    body: str,
    domain: str,
    tags: list[str] | None = None,
    links: list[str] | None = None,
    subdir: str = "",
    extra: dict[str, Any] | None = None,
    root: Path | None = None,
) -> Path:
    """Write one vault note. Returns its path."""
    base = root or vault_dir()
    target_dir = base / subdir if subdir else base
    target_dir.mkdir(parents=True, exist_ok=True)

    meta: dict[str, Any] = {
        "date": _today(),
        "domain": domain,
        "tags": tags or [],
        "links": links or [],
    }
    if extra:
        meta.update(extra)

    path = target_dir / f"{slug}.md"
    path.write_text(frontmatter.dump(meta, body), encoding="utf-8")
    return path


def embed_pre_edit(content: str) -> str:
    """Wrap file content in the markers `pre_edit_content()` reads back."""
    return f"{PRE_EDIT_START}\n{FENCE}markdown\n{content.rstrip()}\n{FENCE}\n{PRE_EDIT_END}"


def read_note(path: Path) -> Note:
    meta, body = frontmatter.parse(Path(path).read_text(encoding="utf-8"))
    return Note(path=Path(path), meta=meta, body=body)


def read_notes(root: Path | None = None) -> list[Note]:
    """Every note in the vault, excluding README.md."""
    base = root or vault_dir()
    if not base.is_dir():
        return []
    notes: list[Note] = []
    for path in sorted(base.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        try:
            notes.append(read_note(path))
        except OSError:
            continue
    return notes


def find_note(name: str, root: Path | None = None) -> Note | None:
    for note in read_notes(root):
        if note.name == name:
            return note
    return None


def graph(root: Path | None = None) -> dict[str, Any]:
    """Node/edge graph built from real note frontmatter. No synthetic nodes.

    Edges pointing at a note that does not exist are still returned, flagged
    `resolved: false`, so the HUD can show a dangling link honestly rather than
    silently dropping it or inventing the missing node.
    """
    notes = read_notes(root)
    by_name = {n.name: n for n in notes}

    nodes = [
        {
            "id": n.name,
            "title": n.title,
            "domain": n.domain,
            "tags": frontmatter.as_list(n.meta.get("tags")),
            "date": str(n.meta.get("date", "")),
            "kind": str(n.meta.get("kind", "") or "note"),
            "degree": 0,
        }
        for n in notes
    ]
    index = {n["id"]: n for n in nodes}

    edges = []
    for note in notes:
        for target in note.links():
            resolved = target in by_name
            edges.append({"source": note.name, "target": target, "resolved": resolved})
            index[note.name]["degree"] += 1
            if resolved:
                index[target]["degree"] += 1

    return {"nodes": nodes, "edges": edges}
