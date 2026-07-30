"""Skill branch loading — SKILL.md trigger lists and pointer files.

A branch is a directory under `skills/`. It contains exactly one `SKILL.md`
(the trigger list, the only file the orchestrator may ever edit) and any number
of pointer files (context about a real project, never orchestrator-writable).

Pointer files declare `entities:` in frontmatter. Those entities are what the
router resolves a query against in Phase 2, and they are what makes the
correction signal mechanical rather than judged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.orchestrator import frontmatter
from backend.orchestrator.paths import skills_dir

SKILL_FILENAME = "SKILL.md"
TRIGGERS_HEADING = "## Triggers"

_BULLET = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_HEADING = re.compile(r"^\s*#{1,6}\s")


@dataclass
class Pointer:
    """A pointer file: context about one real project. Read-only to the orchestrator."""

    branch: str
    file: Path
    name: str
    target: str = ""
    entities: list[str] = field(default_factory=list)
    summary: str = ""

    def target_path(self) -> Path | None:
        return Path(self.target).expanduser() if self.target else None

    def target_exists(self) -> bool:
        """Checked against the real filesystem — this is what makes the
        stale_pointer friction pattern verifiable rather than inferred."""
        p = self.target_path()
        return bool(p and p.exists())


@dataclass
class Skill:
    """One branch: its triggers, its pointers, its raw SKILL.md content."""

    branch: str
    file: Path
    triggers: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    pointers: list[Pointer] = field(default_factory=list)

    def entities(self) -> dict[str, Pointer]:
        """Every entity this branch can answer for, mapped to its pointer."""
        out: dict[str, Pointer] = {}
        for ptr in self.pointers:
            for entity in ptr.entities:
                out[entity.lower()] = ptr
        return out


# --- parsing -----------------------------------------------------------------


def extract_triggers(content: str) -> list[str]:
    """Read the bullet list under `## Triggers`, stopping at the next heading."""
    triggers: list[str] = []
    in_section = False
    for line in content.splitlines():
        if line.strip().lower() == TRIGGERS_HEADING.lower():
            in_section = True
            continue
        if in_section:
            if _HEADING.match(line):
                break
            match = _BULLET.match(line)
            if match:
                phrase = match.group(1).strip().strip("`").strip()
                if phrase:
                    triggers.append(phrase)
    return triggers


def parse_pointer(path: Path, branch: str) -> Pointer:
    text = path.read_text(encoding="utf-8")
    meta, body = frontmatter.parse(text)
    summary = ""
    for line in body.splitlines():
        line = line.strip()
        if line and not _HEADING.match(line):
            summary = line
            break
    return Pointer(
        branch=branch,
        file=path,
        name=str(meta.get("pointer") or path.stem),
        target=str(meta.get("path") or ""),
        entities=frontmatter.as_list(meta.get("entities")),
        summary=summary,
    )


def parse_skill(path: Path, branch: str) -> Skill:
    text = path.read_text(encoding="utf-8")
    meta, _ = frontmatter.parse(text)
    return Skill(
        branch=branch,
        file=path,
        triggers=extract_triggers(text),
        meta=meta,
        content=text,
    )


def load_skills(root: Path | None = None) -> dict[str, Skill]:
    """Load every branch under skills/. Directories without a SKILL.md are skipped."""
    base = root or skills_dir()
    out: dict[str, Skill] = {}
    if not base.is_dir():
        return out

    for branch_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        skill_file = branch_dir / SKILL_FILENAME
        if not skill_file.is_file():
            continue
        branch = branch_dir.name
        skill = parse_skill(skill_file, branch)
        for md in sorted(branch_dir.glob("*.md")):
            if md.name == SKILL_FILENAME:
                continue
            skill.pointers.append(parse_pointer(md, branch))
        out[branch] = skill
    return out


# --- pure edit helpers (used by evolve; kept pure so they are testable) -------


def add_trigger(content: str, phrase: str) -> str:
    """Return SKILL.md content with `phrase` appended to the Triggers list.

    Inserts after the last existing bullet so the surrounding prose, ordering and
    any trailing sections are preserved exactly.
    """
    if phrase in extract_triggers(content):
        return content

    lines = content.splitlines()
    in_section = False
    last_bullet = None
    heading_idx = None

    for i, line in enumerate(lines):
        if line.strip().lower() == TRIGGERS_HEADING.lower():
            in_section = True
            heading_idx = i
            continue
        if in_section:
            if _HEADING.match(line):
                break
            if _BULLET.match(line):
                last_bullet = i

    if last_bullet is not None:
        insert_at = last_bullet + 1
    elif heading_idx is not None:
        insert_at = heading_idx + 1
        lines.insert(insert_at, "")
        insert_at += 1
    else:
        # No Triggers section at all — create one at the end.
        trailing = "" if content.endswith("\n") else "\n"
        return content + f"{trailing}\n{TRIGGERS_HEADING}\n\n- {phrase}\n"

    lines.insert(insert_at, f"- {phrase}")
    result = "\n".join(lines)
    return result + "\n" if content.endswith("\n") else result


KNOWN_ISSUES_HEADING = "## Known issues"


def add_known_issue(content: str, note: str) -> str:
    """Append a bullet to the `## Known issues` section, creating it if absent.

    Used where the orchestrator has found a real problem it is not permitted to
    fix directly — a stale pointer file, an overloaded branch — so the finding is
    recorded in the one file it may write instead of being silently dropped.
    """
    lines = content.splitlines()
    heading_idx = None
    for i, line in enumerate(lines):
        if line.strip().lower() == KNOWN_ISSUES_HEADING.lower():
            heading_idx = i
            break

    if heading_idx is None:
        trailing = "" if content.endswith("\n") else "\n"
        return content + f"{trailing}\n{KNOWN_ISSUES_HEADING}\n\n- {note}\n"

    last_bullet = None
    for i in range(heading_idx + 1, len(lines)):
        if _HEADING.match(lines[i]):
            break
        if _BULLET.match(lines[i]):
            last_bullet = i
        if _BULLET.match(lines[i]) and lines[i].strip()[2:].strip() == note:
            return content  # already recorded

    insert_at = last_bullet + 1 if last_bullet is not None else heading_idx + 1
    if last_bullet is None:
        lines.insert(insert_at, "")
        insert_at += 1
    lines.insert(insert_at, f"- {note}")
    result = "\n".join(lines)
    return result + "\n" if content.endswith("\n") else result


def remove_trigger(content: str, phrase: str) -> str:
    """Return SKILL.md content with the bullet for `phrase` removed."""
    lines = content.splitlines()
    in_section = False
    out: list[str] = []

    for line in lines:
        if line.strip().lower() == TRIGGERS_HEADING.lower():
            in_section = True
            out.append(line)
            continue
        if in_section:
            if _HEADING.match(line):
                in_section = False
            else:
                match = _BULLET.match(line)
                if match and match.group(1).strip().strip("`").strip() == phrase:
                    continue
        out.append(line)

    result = "\n".join(out)
    return result + "\n" if content.endswith("\n") else result
