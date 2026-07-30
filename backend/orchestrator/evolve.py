"""Self-review: find real friction in the log, propose one minimal skill edit.

Every pattern here is derived from logged events or verified against the
filesystem. Nothing is inferred from a model's opinion, and there is no code
path that produces a proposal when the evidence thresholds in AGENTIC_OS.md are
not met — `analyse()` returns an empty list and the caller reports that honestly.

Proposals carry a fingerprint. A proposal the user rejected is never offered
again in identical form, because its fingerprint is recorded in the rejection
event and checked on the next run.
"""
from __future__ import annotations

import difflib
import hashlib
import secrets
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.orchestrator import constitution, guardrails, skills as skills_mod, vault
from backend.orchestrator.events import (
    EVOLVE_APPLIED,
    EVOLVE_PROPOSED,
    EVOLVE_REJECTED,
    EVOLVE_REVERTED,
    Event,
    EventLog,
)
from backend.orchestrator.events import ROUTE
from backend.orchestrator.paths import repo_root
from backend.orchestrator.router import CORRECTED
from backend.orchestrator.skills import Skill

MISSING_TRIGGER = "missing_trigger"
OVERBROAD_TRIGGER = "overbroad_trigger"
STALE_POINTER = "stale_pointer"
OVERLOADED_SKILL = "overloaded_skill"

# Priority when several patterns qualify at once. Filesystem-verified evidence
# outranks statistical evidence; additive edits outrank destructive ones.
PATTERN_PRIORITY = {
    STALE_POINTER: 0,
    MISSING_TRIGGER: 1,
    OVERBROAD_TRIGGER: 2,
    OVERLOADED_SKILL: 3,
}

# Verified directly against the filesystem, so it needs no statistical support
# and is exempt from the log-volume gates. See AGENTIC_OS.md.
FILESYSTEM_VERIFIED = {STALE_POINTER}


@dataclass
class Finding:
    """One friction pattern found in real data."""

    pattern: str
    branch: str
    subject: str
    occurrences: int
    cited: list[Event] = field(default_factory=list)
    detail: str = ""

    @property
    def priority(self) -> tuple[int, int]:
        return (PATTERN_PRIORITY.get(self.pattern, 99), -self.occurrences)


@dataclass
class Proposal:
    id: str
    pattern: str
    branch: str
    target: Path
    old_content: str
    new_content: str
    reason: str
    cited: list[Event] = field(default_factory=list)
    caveat: str = ""

    @property
    def rel_target(self) -> str:
        try:
            return str(self.target.resolve().relative_to(repo_root().resolve()))
        except ValueError:
            return str(self.target)

    def fingerprint(self) -> str:
        """Identity of *this exact edit*, so a rejected edit is not re-offered."""
        digest = hashlib.sha256()
        digest.update(self.pattern.encode())
        digest.update(b"\x00")
        digest.update(self.rel_target.encode())
        digest.update(b"\x00")
        digest.update(self.new_content.encode())
        return digest.hexdigest()[:16]

    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.old_content.splitlines(keepends=True),
                self.new_content.splitlines(keepends=True),
                fromfile=f"a/{self.rel_target}",
                tofile=f"b/{self.rel_target}",
                n=3,
            )
        )

    def citations(self) -> list[str]:
        return [e.cite() for e in self.cited]


class NotEnoughSignal(Exception):
    """Raised with an honest explanation instead of a fabricated proposal."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --- blocked fingerprints -----------------------------------------------------


def blocked_fingerprints(log: EventLog) -> dict[str, str]:
    """Fingerprints that must not be re-proposed, mapped to why.

    A rejected edit stays blocked. An applied edit stays blocked until reverted,
    at which point the underlying friction is allowed to resurface.
    """
    blocked: dict[str, str] = {}
    reverted: set[str] = set()

    for event in log.iter_events():
        fp = event.payload.get("fingerprint")
        if event.type == EVOLVE_REVERTED:
            reverted.add(str(event.payload.get("proposal_id", "")))
        if not fp:
            continue
        if event.type == EVOLVE_REJECTED:
            reason = event.payload.get("reason") or "no reason given"
            blocked[fp] = f"you rejected this exact edit ({reason})"
        elif event.type == EVOLVE_APPLIED:
            blocked[fp] = "this exact edit is already applied"

    for event in log.by_type(EVOLVE_APPLIED):
        pid = str(event.payload.get("proposal_id", ""))
        fp = event.payload.get("fingerprint")
        if pid in reverted and fp in blocked and blocked[fp].startswith("this exact edit is already"):
            del blocked[fp]

    return blocked


# --- pattern detection --------------------------------------------------------


def _route_events(log: EventLog) -> list[Event]:
    return [e for e in log.iter_events() if e.type == ROUTE]


def find_missing_triggers(route_events: list[Event], skills: dict[str, Skill]) -> list[Finding]:
    """An entity that repeatedly forced a mid-turn correction into a branch whose
    triggers never matched it."""
    counts: dict[tuple[str, str], list[Event]] = defaultdict(list)

    for event in route_events:
        if event.payload.get("outcome") != CORRECTED:
            continue
        for correction in event.payload.get("corrections", []) or []:
            branch = str(correction.get("added_branch", ""))
            entity = str(correction.get("entity", ""))
            if branch and entity:
                counts[(branch, entity)].append(event)

    findings = []
    for (branch, entity), cited in counts.items():
        skill = skills.get(branch)
        if not skill:
            continue
        existing = {t.lower() for t in skill.triggers}
        if entity.lower() in existing:
            continue
        findings.append(
            Finding(
                pattern=MISSING_TRIGGER,
                branch=branch,
                subject=entity,
                occurrences=len(cited),
                cited=cited,
                detail=(
                    f"'{entity}' routed to '{branch}' only after a mid-turn correction, "
                    f"{len(cited)} time(s). It is not in that skill's trigger list."
                ),
            )
        )
    return findings


def find_overbroad_triggers(route_events: list[Event], skills: dict[str, Skill]) -> list[Finding]:
    """A trigger phrase that keeps loading its branch for queries the branch
    turns out to have nothing to say about — and has never once been useful."""
    fired: dict[tuple[str, str], int] = defaultdict(int)
    wasted: dict[tuple[str, str], list[Event]] = defaultdict(list)
    useful: dict[tuple[str, str], int] = defaultdict(int)

    for event in route_events:
        payload = event.payload
        unused = set(payload.get("unused_branches", []) or [])
        resolved_branches = {
            str(r.get("branch")) for r in (payload.get("resolved_entities", []) or [])
        }
        for branch, triggers in (payload.get("matched_triggers", {}) or {}).items():
            for trigger in triggers or []:
                key = (str(branch), str(trigger))
                fired[key] += 1
                if branch in unused:
                    wasted[key].append(event)
                if branch in resolved_branches:
                    useful[key] += 1

    findings = []
    for key, events in wasted.items():
        branch, trigger = key
        # Only propose removing a phrase that has never contributed to a resolved
        # query. A phrase that is sometimes right is not overbroad, it is normal.
        if useful[key] > 0:
            continue
        skill = skills.get(branch)
        if not skill or trigger not in skill.triggers:
            continue
        findings.append(
            Finding(
                pattern=OVERBROAD_TRIGGER,
                branch=branch,
                subject=trigger,
                occurrences=len(events),
                cited=events,
                detail=(
                    f"trigger '{trigger}' loaded '{branch}' {fired[key]} time(s), "
                    f"contributed nothing on {len(events)} of them, and has never "
                    "been the reason a query resolved."
                ),
            )
        )
    return findings


def find_stale_pointers(skills: dict[str, Skill]) -> list[Finding]:
    """A pointer file whose `path:` no longer exists. Checked against the real
    filesystem at analysis time, not inferred from the log."""
    findings = []
    for branch, skill in skills.items():
        for pointer in skill.pointers:
            if not pointer.target:
                continue
            if pointer.target_exists():
                continue
            findings.append(
                Finding(
                    pattern=STALE_POINTER,
                    branch=branch,
                    subject=pointer.file.name,
                    occurrences=1,
                    cited=[],
                    detail=(
                        f"{branch}/{pointer.file.name} points at '{pointer.target}', "
                        "which does not exist on disk."
                    ),
                )
            )
    return findings


def find_overloaded_skills(route_events: list[Event], skills: dict[str, Skill]) -> list[Finding]:
    """A branch whose entities split into groups that never appear together."""
    co_occurrence: dict[str, list[set[str]]] = defaultdict(list)
    for event in route_events:
        per_branch: dict[str, set[str]] = defaultdict(set)
        for resolved in event.payload.get("resolved_entities", []) or []:
            per_branch[str(resolved.get("branch"))].add(str(resolved.get("entity")))
        for branch, entities in per_branch.items():
            co_occurrence[branch].append(entities)

    findings = []
    for branch, skill in skills.items():
        entities = sorted(skill.entities())
        if len(entities) < 4:
            continue

        parent = {e: e for e in entities}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for group in co_occurrence.get(branch, []):
            members = [e for e in group if e in parent]
            for other in members[1:]:
                union(members[0], other)

        clusters: dict[str, list[str]] = defaultdict(list)
        for entity in entities:
            clusters[find(entity)].append(entity)

        big = [c for c in clusters.values() if len(c) >= 2]
        if len(big) < 2:
            continue

        observed = len(co_occurrence.get(branch, []))
        findings.append(
            Finding(
                pattern=OVERLOADED_SKILL,
                branch=branch,
                subject=" | ".join(", ".join(sorted(c)) for c in big),
                occurrences=observed,
                cited=[],
                detail=(
                    f"branch '{branch}' covers {len(big)} entity groups that never "
                    f"co-occur across {observed} observed queries: "
                    + " | ".join("{" + ", ".join(sorted(c)) + "}" for c in big)
                ),
            )
        )
    return findings


def analyse(
    log: EventLog,
    skills: dict[str, Skill] | None = None,
    config: dict[str, Any] | None = None,
) -> tuple[list[Finding], list[str]]:
    """Return (actionable findings, notes about what was filtered and why)."""
    cfg = config or constitution.get()
    evolve_cfg = cfg.get("evolve", {})
    min_events = int(evolve_cfg.get("min_events", 12))
    min_occurrences = int(evolve_cfg.get("min_pattern_occurrences", 3))

    loaded = skills if skills is not None else skills_mod.load_skills()
    route_events = _route_events(log)
    notes: list[str] = []

    findings = find_stale_pointers(loaded)

    if len(route_events) < min_events:
        notes.append(
            f"{len(route_events)} routing event(s) logged; AGENTIC_OS.md requires "
            f"{min_events} before log-derived patterns are considered."
        )
    else:
        candidates = (
            find_missing_triggers(route_events, loaded)
            + find_overbroad_triggers(route_events, loaded)
            + find_overloaded_skills(route_events, loaded)
        )
        for finding in candidates:
            if finding.occurrences < min_occurrences:
                notes.append(
                    f"{finding.pattern} '{finding.subject}' seen {finding.occurrences}x "
                    f"— below the {min_occurrences}x threshold, not actionable yet."
                )
                continue
            findings.append(finding)

    findings.sort(key=lambda f: f.priority)
    return findings, notes


# --- proposal construction ----------------------------------------------------


def _new_proposal_id() -> str:
    return f"prop_{secrets.token_hex(4)}"


def build_proposal(finding: Finding, skills: dict[str, Skill]) -> Proposal | None:
    """Turn a finding into a concrete, minimal edit to one SKILL.md."""
    skill = skills.get(finding.branch)
    if not skill:
        return None

    old = skill.content
    caveat = ""

    if finding.pattern == MISSING_TRIGGER:
        new = skills_mod.add_trigger(old, finding.subject)
        reason = (
            f"Add '{finding.subject}' as a trigger for the '{finding.branch}' skill. "
            f"{finding.detail} Adding it lets trigger matching catch the query in "
            "phase 1, so no mid-turn correction is needed."
        )

    elif finding.pattern == OVERBROAD_TRIGGER:
        new = skills_mod.remove_trigger(old, finding.subject)
        reason = (
            f"Remove '{finding.subject}' from the '{finding.branch}' skill's triggers. "
            f"{finding.detail} Removing it stops the branch loading for queries it "
            "cannot answer."
        )

    elif finding.pattern == STALE_POINTER:
        note = (
            f"`{finding.subject}` points at a path that no longer exists "
            f"— verified missing on disk at analysis time."
        )
        new = skills_mod.add_known_issue(old, note)
        reason = (
            f"Flag the stale pointer in the '{finding.branch}' skill. {finding.detail} "
            "The pointer file itself is outside the orchestrator's write scope, so "
            "this records the problem in SKILL.md rather than silently editing it."
        )
        caveat = (
            f"The orchestrator cannot fix skills/{finding.branch}/{finding.subject} "
            "itself — pointer files are never writable. Correct the path by hand."
        )

    elif finding.pattern == OVERLOADED_SKILL:
        note = (
            f"Skill appears overloaded: {finding.detail} Consider splitting into "
            "separate branches."
        )
        new = skills_mod.add_known_issue(old, note)
        reason = (
            f"Record that the '{finding.branch}' skill covers unrelated entity groups. "
            f"{finding.detail}"
        )
        caveat = (
            "A real split means creating a new branch directory and moving pointer "
            "files. Both are outside the orchestrator's write scope, so this proposal "
            "only records the finding."
        )

    else:
        return None

    if new == old:
        return None

    return Proposal(
        id=_new_proposal_id(),
        pattern=finding.pattern,
        branch=finding.branch,
        target=skill.file,
        old_content=old,
        new_content=new,
        reason=reason,
        cited=finding.cited,
        caveat=caveat,
    )


def next_proposal(
    log: EventLog,
    skills: dict[str, Skill] | None = None,
    config: dict[str, Any] | None = None,
) -> Proposal:
    """The single best proposal, or raise NotEnoughSignal with a real explanation."""
    loaded = skills if skills is not None else skills_mod.load_skills()
    findings, notes = analyse(log, loaded, config)

    if not findings:
        reason = "no friction pattern in the log reached its evidence threshold."
        if notes:
            reason += " " + " ".join(notes)
        raise NotEnoughSignal(reason)

    blocked = blocked_fingerprints(log)
    skipped: list[str] = []

    for finding in findings:
        proposal = build_proposal(finding, loaded)
        if proposal is None:
            continue
        fp = proposal.fingerprint()
        if fp in blocked:
            skipped.append(f"{finding.pattern} '{finding.subject}' — {blocked[fp]}")
            continue
        return proposal

    reason = "every actionable finding is already applied or was previously rejected."
    if skipped:
        reason += " Skipped: " + "; ".join(skipped) + "."
    raise NotEnoughSignal(reason)


# --- apply / reject / revert --------------------------------------------------


def _previous_evolution_note(root: Path | None = None) -> str | None:
    notes = [n for n in vault.read_notes(root) if n.meta.get("kind") == "self-edit"]
    notes.sort(key=lambda n: str(n.meta.get("date", "")))
    return notes[-1].name if notes else None


def _note_body(proposal: Proposal, applied: bool = True) -> str:
    citations = proposal.citations()
    cite_block = (
        "\n".join(f"- `{c}`" for c in citations)
        if citations
        else "- _none — this finding is verified against the filesystem, not the log_"
    )

    caveat_block = f"\n## Caveat\n\n{proposal.caveat}\n" if proposal.caveat else ""

    return f"""# Skill edit: {proposal.pattern} in `{proposal.branch}`

**Proposal** `{proposal.id}` · **target** `{proposal.rel_target}` · \
**status** {"applied" if applied else "proposed"}

## Why

{proposal.reason}

## Motivating events

These are the exact entries in `memory/events.jsonl` that produced this edit.
Each is cited by event id and line number, so the reasoning can be checked
against the log rather than taken on trust.

{cite_block}

## Diff

```diff
{proposal.diff().rstrip()}
```
{caveat_block}
## Reverting

```bash
nexus evolve --revert {proposal.id}
```

The complete pre-edit content of `{proposal.rel_target}` is stored below. Revert
restores exactly this, byte for byte.

{vault.embed_pre_edit(proposal.old_content)}
"""


def apply(proposal: Proposal, log: EventLog, run_id: str) -> tuple[Path, Path, Event]:
    """Apply an approved proposal. Returns (edited file, vault note, event).

    The write goes through `guardrails.write`, which refuses anything outside
    `skills/*/SKILL.md` regardless of what the proposal claims to target.
    """
    written = guardrails.write(proposal.target, proposal.new_content)

    previous = _previous_evolution_note()
    note_path = vault.write_note(
        slug=f"evolve-{proposal.id}",
        body=_note_body(proposal, applied=True),
        domain="orchestrator",
        tags=["evolution", proposal.pattern, proposal.branch],
        links=[previous] if previous else [],
        subdir="evolution",
        extra={
            "kind": "self-edit",
            "proposal": proposal.id,
            "pattern": proposal.pattern,
            "target": proposal.rel_target,
        },
    )

    event = log.append(
        EVOLVE_APPLIED,
        {
            "proposal_id": proposal.id,
            "fingerprint": proposal.fingerprint(),
            "pattern": proposal.pattern,
            "branch": proposal.branch,
            "target": proposal.rel_target,
            "note": str(note_path.relative_to(repo_root())),
            "cited_events": [e.id for e in proposal.cited],
        },
        run_id=run_id,
    )
    return written, note_path, event


def reject(proposal: Proposal, log: EventLog, run_id: str, reason: str = "") -> Event:
    """Record a rejection so the identical edit is never offered again."""
    return log.append(
        EVOLVE_REJECTED,
        {
            "proposal_id": proposal.id,
            "fingerprint": proposal.fingerprint(),
            "pattern": proposal.pattern,
            "branch": proposal.branch,
            "target": proposal.rel_target,
            "reason": reason.strip(),
            "cited_events": [e.id for e in proposal.cited],
        },
        run_id=run_id,
    )


def record_proposal(proposal: Proposal, log: EventLog, run_id: str) -> Event:
    return log.append(
        EVOLVE_PROPOSED,
        {
            "proposal_id": proposal.id,
            "fingerprint": proposal.fingerprint(),
            "pattern": proposal.pattern,
            "branch": proposal.branch,
            "target": proposal.rel_target,
            "reason": proposal.reason,
            "cited_events": [e.id for e in proposal.cited],
        },
        run_id=run_id,
    )


class RevertError(RuntimeError):
    pass


def revert(proposal_id: str, log: EventLog, run_id: str) -> tuple[Path, Path, Event]:
    """Restore a file to its pre-edit content from the vault note."""
    applied = [
        e for e in log.by_type(EVOLVE_APPLIED) if e.payload.get("proposal_id") == proposal_id
    ]
    if not applied:
        raise RevertError(
            f"no applied edit with id {proposal_id!r} in the log. "
            "Run `nexus evolve --history` to list applied edits."
        )
    event = applied[-1]

    already = [
        e for e in log.by_type(EVOLVE_REVERTED) if e.payload.get("proposal_id") == proposal_id
    ]
    if already:
        raise RevertError(f"{proposal_id} was already reverted at {already[-1].ts}.")

    note = vault.find_note(f"evolve-{proposal_id}")
    if note is None:
        raise RevertError(
            f"vault note evolve-{proposal_id}.md is missing, so the pre-edit content "
            "is unavailable. Nothing was changed."
        )

    original = note.pre_edit_content()
    if original is None:
        raise RevertError(
            f"vault note {note.path} contains no pre-edit content block. "
            "Nothing was changed."
        )

    target = repo_root() / str(event.payload.get("target", ""))
    restored = guardrails.write(target, original if original.endswith("\n") else original + "\n")

    revert_event = log.append(
        EVOLVE_REVERTED,
        {
            "proposal_id": proposal_id,
            "fingerprint": event.payload.get("fingerprint"),
            "pattern": event.payload.get("pattern"),
            "branch": event.payload.get("branch"),
            "target": event.payload.get("target"),
            "note": str(note.path.relative_to(repo_root())),
        },
        run_id=run_id,
    )
    return restored, note.path, revert_event
