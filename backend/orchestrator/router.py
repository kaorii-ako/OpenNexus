"""Skill routing with a derived outcome signal.

Three phases, as specified in AGENTIC_OS.md:

  1. trigger match      — which branches claim this query
  2. entity resolution  — which branches the query actually needs
  3. outcome signal     — what mechanically happened, described honestly

The outcome is never a model judgement and never a confidence score. It is a
comparison of two sets: what the triggers selected, and what resolution needed.
If those sets differ, that difference is the signal, and it is the only signal
`nexus evolve` is allowed to learn from.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from backend.orchestrator import constitution
from backend.orchestrator.events import ROUTE, Event, EventLog, new_run_id
from backend.orchestrator.skills import Pointer, Skill, load_skills

CLEAN = "clean"
CORRECTED = "corrected"
UNUSED = "unused"


@lru_cache(maxsize=512)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Word-boundary, case-insensitive match for a trigger or entity.

    \\b does not fire next to non-word characters, so phrases like `stock-new`
    are anchored with lookarounds instead — otherwise a trailing `-new` would
    never match at a word boundary.
    """
    escaped = re.escape(phrase.strip())
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def _matches(query: str, phrase: str, min_len: int) -> bool:
    phrase = phrase.strip()
    if len(phrase) < min_len:
        return False
    return bool(_phrase_pattern(phrase).search(query))


@dataclass
class Correction:
    """A branch that trigger matching missed and resolution had to add."""

    entity: str
    added_branch: str
    pointer: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity": self.entity,
            "added_branch": self.added_branch,
            "pointer": self.pointer,
            "reason": self.reason,
        }


@dataclass
class ResolvedEntity:
    entity: str
    branch: str
    pointer: str

    def to_dict(self) -> dict[str, Any]:
        return {"entity": self.entity, "branch": self.branch, "pointer": self.pointer}


@dataclass
class RoutingDecision:
    query: str
    selected_branches: list[str] = field(default_factory=list)
    loaded_branches: list[str] = field(default_factory=list)
    matched_triggers: dict[str, list[str]] = field(default_factory=dict)
    resolved_entities: list[ResolvedEntity] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    unused_branches: list[str] = field(default_factory=list)
    outcome: str = CLEAN
    event_id: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "selected_branches": self.selected_branches,
            "loaded_branches": self.loaded_branches,
            "matched_triggers": self.matched_triggers,
            "resolved_entities": [e.to_dict() for e in self.resolved_entities],
            "corrections": [c.to_dict() for c in self.corrections],
            "unused_branches": self.unused_branches,
            "outcome": self.outcome,
        }

    @property
    def was_corrected(self) -> bool:
        return bool(self.corrections)


class Router:
    def __init__(self, skills: dict[str, Skill] | None = None, config: dict | None = None):
        self.config = config or constitution.get()
        self.skills = skills if skills is not None else load_skills()
        routing = self.config.get("routing", {})
        self.always_load: list[str] = list(routing.get("always_load", []))
        self.min_trigger_len: int = int(routing.get("min_trigger_len", 3))

    # --- phases --------------------------------------------------------------

    def _phase1_triggers(self, query: str) -> tuple[list[str], dict[str, list[str]]]:
        """Which branches claim this query, and which phrases made them claim it."""
        matched: dict[str, list[str]] = {}
        for branch, skill in self.skills.items():
            hits = [t for t in skill.triggers if _matches(query, t, self.min_trigger_len)]
            if hits:
                matched[branch] = hits

        selected = sorted(set(matched) | {b for b in self.always_load if b in self.skills})
        return selected, matched

    def _phase2_entities(self, query: str) -> list[ResolvedEntity]:
        """Which concrete projects the query actually names, across all branches."""
        resolved: list[ResolvedEntity] = []
        seen: set[tuple[str, str]] = set()
        for branch, skill in self.skills.items():
            for entity, pointer in skill.entities().items():
                if not _matches(query, entity, self.min_trigger_len):
                    continue
                key = (branch, entity)
                if key in seen:
                    continue
                seen.add(key)
                resolved.append(
                    ResolvedEntity(entity=entity, branch=branch, pointer=pointer.file.name)
                )
        return resolved

    def route(self, query: str) -> RoutingDecision:
        """Route without logging. `Orchestrator.handle` is the logging entry point."""
        selected, matched = self._phase1_triggers(query)
        resolved = self._phase2_entities(query)

        decision = RoutingDecision(
            query=query,
            selected_branches=selected,
            matched_triggers=matched,
            resolved_entities=resolved,
        )

        entity_branches = {e.branch for e in resolved}

        if not entity_branches:
            # A general query that names no specific project. Triggers did their
            # job; there is nothing to correct and nothing to call unused.
            decision.loaded_branches = selected
            decision.outcome = CLEAN
            return decision

        missing = entity_branches - set(selected)
        for entity in resolved:
            if entity.branch in missing:
                decision.corrections.append(
                    Correction(
                        entity=entity.entity,
                        added_branch=entity.branch,
                        pointer=entity.pointer,
                        reason=(
                            f"query names '{entity.entity}', which belongs to branch "
                            f"'{entity.branch}', but no trigger in "
                            f"skills/{entity.branch}/SKILL.md matched the query"
                        ),
                    )
                )

        decision.loaded_branches = sorted(set(selected) | entity_branches)

        always = set(self.always_load)
        decision.unused_branches = sorted(
            b for b in selected if b not in entity_branches and b not in always
        )

        if decision.corrections:
            decision.outcome = CORRECTED
        elif decision.unused_branches:
            decision.outcome = UNUSED
        else:
            decision.outcome = CLEAN

        return decision

    # --- context -------------------------------------------------------------

    def context_for(self, decision: RoutingDecision) -> str:
        """The actual skill content the loaded branches contribute.

        This is what makes routing do real work rather than just bookkeeping —
        the text returned here is injected into the model prompt by `ask`/`chat`.
        """
        blocks: list[str] = []
        resolved_pointers = {(e.branch, e.pointer) for e in decision.resolved_entities}

        for branch in decision.loaded_branches:
            skill = self.skills.get(branch)
            if not skill:
                continue
            blocks.append(f"### skill: {branch}\n\n{skill.content.strip()}")
            for ptr in skill.pointers:
                if (branch, ptr.file.name) in resolved_pointers:
                    blocks.append(
                        f"### pointer: {branch}/{ptr.file.name}\n\n"
                        f"{ptr.file.read_text(encoding='utf-8').strip()}"
                    )
        return "\n\n---\n\n".join(blocks)

    def pointers_for(self, decision: RoutingDecision) -> list[Pointer]:
        out: list[Pointer] = []
        wanted = {(e.branch, e.pointer) for e in decision.resolved_entities}
        for branch, ptr_name in sorted(wanted):
            skill = self.skills.get(branch)
            if not skill:
                continue
            for ptr in skill.pointers:
                if ptr.file.name == ptr_name:
                    out.append(ptr)
        return out


class Orchestrator:
    """Routes a query and records the decision. The only place ROUTE events are written."""

    def __init__(self, log: EventLog | None = None, router: Router | None = None):
        self.log = log or EventLog()
        self.router = router or Router()
        self.run_id = new_run_id()

    def handle(self, query: str) -> tuple[RoutingDecision, Event]:
        decision = self.router.route(query)
        event = self.log.append(ROUTE, decision.to_payload(), run_id=self.run_id)
        decision.event_id = event.id
        return decision, event

    def context_for(self, decision: RoutingDecision) -> str:
        return self.router.context_for(decision)
