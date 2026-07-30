"""Tests for the orchestrator: event log, routing, guardrails, evolve, replay.

These target the properties the system claims about itself — append-only,
derived-not-invented outcomes, enforced write scope, byte-exact revert, honest
refusal when there is no signal — because those claims are the whole point.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.orchestrator import constitution, evolve, guardrails, render, replay, skills, vault
from backend.orchestrator.events import (
    EVOLVE_APPLIED,
    EVOLVE_REJECTED,
    ROUTE,
    EventLog,
    new_run_id,
)
from backend.orchestrator.router import CLEAN, CORRECTED, UNUSED, Orchestrator, Router

AGENTIC_OS = """\
# AGENTIC_OS

```toml
[routing]
branches = ["dev", "trading", "shared"]
always_load = ["shared"]
match = "word_boundary_ci"
min_trigger_len = 2

[evolve]
min_events = 6
min_pattern_occurrences = 2
max_proposals_per_run = 1

[guardrails]
writable_globs = ["skills/*/SKILL.md"]
never_writable = ["AGENTIC_OS.md", "backend/orchestrator/*.py", "skills/*/[!S]*.md"]
```
"""

DEV_SKILL = """\
---
branch: dev
name: Development
---

# Dev

## Triggers

- repo
- build
- CI
"""

TRADING_SKILL = """\
---
branch: trading
name: Trading
---

# Trading

## Triggers

- backtest
- position
"""

SHARED_SKILL = """\
---
branch: shared
name: Shared
---

# Shared

## Triggers

- convention
"""


def _pointer(name: str, target: str, entities: list[str]) -> str:
    return (
        f"---\npointer: {name}\npath: {target}\n"
        f"entities: [{', '.join(entities)}]\n---\n\n# {name}\n\nPointer body.\n"
    )


@pytest.fixture
def root(tmp_path, monkeypatch):
    """A complete, isolated NEXUS root."""
    monkeypatch.setenv("NEXUS_ROOT", str(tmp_path))
    constitution._cached.cache_clear()

    (tmp_path / "AGENTIC_OS.md").write_text(AGENTIC_OS)
    (tmp_path / "memory").mkdir()
    (tmp_path / "vault").mkdir()
    (tmp_path / "backend" / "orchestrator").mkdir(parents=True)
    (tmp_path / "backend" / "orchestrator" / "evolve.py").write_text("# real module lives elsewhere\n")

    for branch, content in (("dev", DEV_SKILL), ("trading", TRADING_SKILL), ("shared", SHARED_SKILL)):
        d = tmp_path / "skills" / branch
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(content)

    real_target = tmp_path / "projects" / "thing"
    real_target.mkdir(parents=True)

    (tmp_path / "skills" / "dev" / "flarebisect.md").write_text(
        _pointer("flarebisect", str(real_target), ["flarebisect", "flaky"])
    )
    (tmp_path / "skills" / "trading" / "stock-new.md").write_text(
        _pointer("stock-new", str(real_target), ["stock-new", "set100"])
    )

    yield tmp_path
    constitution._cached.cache_clear()


@pytest.fixture
def log(root):
    return EventLog()


# --- event log ----------------------------------------------------------------


def test_append_assigns_sequential_seq(log):
    for i in range(3):
        event = log.append(ROUTE, {"query": f"q{i}", "outcome": CLEAN}, new_run_id())
        assert event.seq == i + 1
    assert log.count() == 3


def test_log_is_append_only_across_writes(log):
    log.append(ROUTE, {"query": "first", "outcome": CLEAN}, new_run_id())
    log.append(ROUTE, {"query": "second", "outcome": CLEAN}, new_run_id())
    lines = log.path.read_text().strip().splitlines()
    assert len(lines) == 2
    # The first record is untouched by the second write.
    assert json.loads(lines[0])["payload"]["query"] == "first"


def test_verify_detects_deleted_line(log):
    for i in range(4):
        log.append(ROUTE, {"query": f"q{i}", "outcome": CLEAN}, new_run_id())
    assert log.verify() == []

    lines = log.path.read_text().splitlines()
    del lines[1]
    log.path.write_text("\n".join(lines) + "\n")

    problems = log.verify()
    assert problems
    assert any("seq mismatch" in p for p in problems)


def test_verify_detects_edited_content(log):
    log.append(ROUTE, {"query": "original", "outcome": CLEAN}, new_run_id())
    log.path.write_text(log.path.read_text().replace('"seq": 1', '"seq": 9'))
    assert any("seq mismatch" in p for p in log.verify())


def test_unknown_event_type_refused(log):
    with pytest.raises(ValueError):
        log.append("totally_made_up", {}, new_run_id())


def test_cite_includes_id_and_line_number(log):
    event = log.append(ROUTE, {"query": "q", "outcome": CLEAN}, new_run_id())
    assert event.id in event.cite()
    assert "events.jsonl:1" in event.cite()


# --- routing ------------------------------------------------------------------


def test_trigger_match_selects_branch(root):
    decision = Router().route("check the repo")
    assert "dev" in decision.selected_branches
    assert decision.matched_triggers["dev"] == ["repo"]


def test_always_load_branch_is_always_selected(root):
    decision = Router().route("something with no triggers at all")
    assert "shared" in decision.selected_branches


def test_short_trigger_still_matches(root):
    """`CI` is two characters and must not be silently discarded."""
    decision = Router().route("the CI is red")
    assert "dev" in decision.selected_branches
    assert decision.outcome == CLEAN


def test_word_boundary_prevents_substring_match(root):
    """`repo` must not fire on `repossessed`."""
    decision = Router().route("the car was repossessed")
    assert "dev" not in decision.matched_triggers


def test_hyphenated_entity_matches(root):
    decision = Router().route("look at stock-new")
    assert any(e.entity == "stock-new" for e in decision.resolved_entities)


def test_outcome_corrected_when_entity_outside_selected_branches(root):
    decision = Router().route("what is in set100")
    assert decision.outcome == CORRECTED
    assert decision.corrections[0].added_branch == "trading"
    assert decision.corrections[0].entity == "set100"
    assert "trading" in decision.loaded_branches


def test_outcome_clean_when_triggers_match_needs(root):
    decision = Router().route("run the backtest on set100")
    assert decision.outcome == CLEAN
    assert not decision.corrections


def test_outcome_unused_when_branch_contributes_nothing(root):
    """`build` loads dev and `backtest` loads trading; only trading resolves an
    entity, so dev fired for a query it had nothing to say about."""
    decision = Router().route("build the backtest for set100")
    assert decision.outcome == UNUSED
    assert decision.unused_branches == ["dev"]
    assert not decision.corrections


def test_corrected_outranks_unused(root):
    """Both conditions can hold at once; AGENTIC_OS.md gives correction priority,
    but the unused branch is still recorded rather than discarded."""
    decision = Router().route("build the set100 report")
    assert decision.outcome == CORRECTED
    assert decision.corrections
    assert "dev" in decision.unused_branches


def test_general_query_is_clean_not_unused(root):
    """A query naming no project is not evidence any branch misfired."""
    decision = Router().route("what repo should I work on")
    assert decision.outcome == CLEAN
    assert decision.unused_branches == []


def test_always_load_branch_never_counted_unused(root):
    decision = Router().route("look at set100")
    assert "shared" not in decision.unused_branches


def test_no_confidence_score_in_payload(root, log):
    """The event schema must not carry an invented quality number."""
    _, event = Orchestrator(log=log).handle("check the repo")
    serialised = json.dumps(event.to_dict())
    for banned in ("confidence", "score", "certainty", "probability"):
        assert banned not in serialised.lower()


def test_handle_writes_exactly_one_event(root, log):
    Orchestrator(log=log).handle("check the repo")
    assert log.count() == 1
    assert log.read_all()[0].type == ROUTE


# --- guardrails ---------------------------------------------------------------


def test_skill_md_is_writable(root):
    assert guardrails.is_writable(root / "skills" / "dev" / "SKILL.md")


@pytest.mark.parametrize(
    "relative",
    [
        "AGENTIC_OS.md",
        "skills/dev/flarebisect.md",
        "skills/trading/stock-new.md",
        "backend/orchestrator/evolve.py",
        "memory/events.jsonl",
        "vault/note.md",
    ],
)
def test_protected_paths_are_refused(root, relative):
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check(root / relative)


def test_traversal_outside_root_refused(root):
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check(root / ".." / ".." / "etc" / "passwd")


def test_traversal_back_to_protected_file_refused(root):
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check(root / "skills" / ".." / "AGENTIC_OS.md")


def test_symlink_cannot_widen_scope(root):
    """A SKILL.md symlinked at AGENTIC_OS.md must not become writable."""
    link = root / "skills" / "evil"
    link.mkdir()
    (link / "SKILL.md").symlink_to(root / "AGENTIC_OS.md")
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check(link / "SKILL.md")


def test_nested_path_does_not_satisfy_single_star_glob(root):
    """`skills/*/SKILL.md` must not match `skills/a/b/SKILL.md`."""
    deep = root / "skills" / "a" / "b"
    deep.mkdir(parents=True)
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.check(deep / "SKILL.md")


def test_write_helper_enforces_scope(root):
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.write(root / "AGENTIC_OS.md", "rewritten")
    assert "```toml" in (root / "AGENTIC_OS.md").read_text()


# --- skill editing ------------------------------------------------------------


def test_add_trigger_appends_to_list():
    updated = skills.add_trigger(DEV_SKILL, "deploy")
    assert "- deploy" in updated
    assert skills.extract_triggers(updated) == ["repo", "build", "CI", "deploy"]


def test_add_trigger_is_idempotent():
    assert skills.add_trigger(DEV_SKILL, "repo") == DEV_SKILL


def test_add_trigger_preserves_frontmatter_and_body():
    updated = skills.add_trigger(DEV_SKILL, "deploy")
    assert updated.startswith("---\nbranch: dev")
    assert "# Dev" in updated


def test_remove_trigger():
    updated = skills.remove_trigger(DEV_SKILL, "build")
    assert skills.extract_triggers(updated) == ["repo", "CI"]


def test_add_known_issue_creates_section():
    updated = skills.add_known_issue(DEV_SKILL, "something is wrong")
    assert "## Known issues" in updated
    assert "- something is wrong" in updated


# --- evolve -------------------------------------------------------------------


def _log_correction(log, entity: str, branch: str, query: str = "q"):
    return log.append(
        ROUTE,
        {
            "query": query,
            "outcome": CORRECTED,
            "selected_branches": ["shared"],
            "loaded_branches": ["shared", branch],
            "matched_triggers": {},
            "resolved_entities": [{"entity": entity, "branch": branch, "pointer": "p.md"}],
            "corrections": [
                {"entity": entity, "added_branch": branch, "pointer": "p.md", "reason": "r"}
            ],
            "unused_branches": [],
        },
        new_run_id(),
    )


def test_not_enough_signal_when_log_is_empty(root, log):
    with pytest.raises(evolve.NotEnoughSignal):
        evolve.next_proposal(log)


def test_not_enough_signal_below_min_events(root, log):
    _log_correction(log, "set100", "trading")
    _log_correction(log, "set100", "trading")
    with pytest.raises(evolve.NotEnoughSignal) as exc:
        evolve.next_proposal(log)
    assert "min_events" in str(exc.value) or "requires" in str(exc.value)


def test_below_occurrence_threshold_is_not_actionable(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    _log_correction(log, "set100", "trading")  # only once
    findings, notes = evolve.analyse(log)
    assert not [f for f in findings if f.pattern == evolve.MISSING_TRIGGER]
    assert any("threshold" in n for n in notes)


def test_missing_trigger_proposal_built_from_real_events(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")

    proposal = evolve.next_proposal(log)
    assert proposal.pattern == evolve.MISSING_TRIGGER
    assert proposal.rel_target == "skills/trading/SKILL.md"
    assert "- set100" in proposal.new_content
    assert len(proposal.cited) == 2
    assert all("events.jsonl:" in c for c in proposal.citations())


def test_proposal_only_targets_skill_md(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")
    proposal = evolve.next_proposal(log)
    assert guardrails.is_writable(proposal.target)


def test_stale_pointer_detected_against_filesystem(root, log):
    (root / "skills" / "dev" / "gone.md").write_text(
        _pointer("gone", str(root / "does" / "not" / "exist"), ["gone"])
    )
    findings, _ = evolve.analyse(log)
    stale = [f for f in findings if f.pattern == evolve.STALE_POINTER]
    assert len(stale) == 1
    assert stale[0].subject == "gone.md"


def test_stale_pointer_exempt_from_event_thresholds(root, log):
    """Filesystem-verified evidence needs no log volume — and the empty log
    must not suppress it."""
    (root / "skills" / "dev" / "gone.md").write_text(
        _pointer("gone", str(root / "nope"), ["gone"])
    )
    proposal = evolve.next_proposal(log)
    assert proposal.pattern == evolve.STALE_POINTER
    assert proposal.cited == []
    assert proposal.caveat  # says plainly it cannot fix the pointer itself


def test_apply_writes_file_and_vault_note(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")

    proposal = evolve.next_proposal(log)
    original = proposal.old_content
    written, note_path, event = evolve.apply(proposal, log, new_run_id())

    assert "- set100" in written.read_text()
    assert note_path.exists()
    assert event.type == EVOLVE_APPLIED

    note = vault.read_note(note_path)
    assert note.meta["kind"] == "self-edit"
    assert note.pre_edit_content().rstrip() == original.rstrip()
    for cited in proposal.cited:
        assert cited.id in note.body


def test_revert_restores_byte_for_byte(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")

    proposal = evolve.next_proposal(log)
    target = proposal.target
    before = target.read_text()

    evolve.apply(proposal, log, new_run_id())
    assert target.read_text() != before

    evolve.revert(proposal.id, log, new_run_id())
    assert target.read_text() == before


def test_double_revert_refused(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")
    proposal = evolve.next_proposal(log)
    evolve.apply(proposal, log, new_run_id())
    evolve.revert(proposal.id, log, new_run_id())
    with pytest.raises(evolve.RevertError):
        evolve.revert(proposal.id, log, new_run_id())


def test_revert_unknown_id_refused(root, log):
    with pytest.raises(evolve.RevertError):
        evolve.revert("prop_deadbeef", log, new_run_id())


def test_revert_without_note_refuses_and_changes_nothing(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")
    proposal = evolve.next_proposal(log)
    _, note_path, _ = evolve.apply(proposal, log, new_run_id())
    after_apply = proposal.target.read_text()

    note_path.unlink()

    with pytest.raises(evolve.RevertError):
        evolve.revert(proposal.id, log, new_run_id())
    assert proposal.target.read_text() == after_apply


def test_rejected_edit_is_not_proposed_again(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")

    proposal = evolve.next_proposal(log)
    evolve.reject(proposal, log, new_run_id(), "too broad")

    blocked = evolve.blocked_fingerprints(log)
    assert proposal.fingerprint() in blocked
    assert "too broad" in blocked[proposal.fingerprint()]

    with pytest.raises(evolve.NotEnoughSignal):
        evolve.next_proposal(log)


def test_applied_edit_is_not_proposed_again(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")
    proposal = evolve.next_proposal(log)
    evolve.apply(proposal, log, new_run_id())
    with pytest.raises(evolve.NotEnoughSignal):
        evolve.next_proposal(log)


def test_fingerprint_is_stable_and_edit_specific(root, log):
    for _ in range(6):
        log.append(ROUTE, {"query": "q", "outcome": CLEAN, "resolved_entities": []}, new_run_id())
    for _ in range(2):
        _log_correction(log, "set100", "trading")
    first = evolve.next_proposal(log)
    second = evolve.next_proposal(log)
    assert first.id != second.id           # ids are per-proposal
    assert first.fingerprint() == second.fingerprint()  # the edit is the same


def test_overbroad_trigger_needs_zero_useful_fires(root, log):
    """A trigger that is sometimes right is normal, not overbroad."""
    for _ in range(6):
        log.append(
            ROUTE,
            {
                "query": "q", "outcome": UNUSED,
                "matched_triggers": {"dev": ["build"]},
                "unused_branches": ["dev"],
                "resolved_entities": [{"entity": "set100", "branch": "trading", "pointer": "p.md"}],
            },
            new_run_id(),
        )
    findings, _ = evolve.analyse(log)
    assert any(f.pattern == evolve.OVERBROAD_TRIGGER and f.subject == "build" for f in findings)

    # One useful fire disqualifies it.
    log.append(
        ROUTE,
        {
            "query": "q", "outcome": CLEAN,
            "matched_triggers": {"dev": ["build"]},
            "unused_branches": [],
            "resolved_entities": [{"entity": "flaky", "branch": "dev", "pointer": "p.md"}],
        },
        new_run_id(),
    )
    findings, _ = evolve.analyse(log)
    assert not any(f.pattern == evolve.OVERBROAD_TRIGGER for f in findings)


# --- vault --------------------------------------------------------------------


def test_note_roundtrip(root):
    path = vault.write_note("a-note", "# Title\n\nbody", domain="dev", tags=["x"], links=["b-note"])
    note = vault.read_note(path)
    assert note.meta["domain"] == "dev"
    assert note.title == "Title"
    assert note.links() == ["b-note"]


def test_wikilinks_collected_alongside_frontmatter(root):
    path = vault.write_note("a", "# A\n\nsee [[b]] and [[c]]", domain="dev", links=["d"])
    assert set(vault.read_note(path).links()) == {"b", "c", "d"}


def test_graph_marks_dangling_edges(root):
    vault.write_note("a", "# A", domain="dev", links=["nonexistent"])
    graph = vault.graph()
    assert len(graph["nodes"]) == 1
    assert graph["edges"][0]["resolved"] is False


def test_pre_edit_block_survives_nested_fences(root):
    tricky = "# Skill\n\n```markdown\nnested fence\n```\n\n## Triggers\n\n- x\n"
    body = "# note\n\n" + vault.embed_pre_edit(tricky)
    path = vault.write_note("edit", body, domain="orchestrator")
    assert vault.read_note(path).pre_edit_content().rstrip() == tricky.rstrip()


def test_readme_excluded_from_notes(root):
    (root / "vault" / "README.md").write_text("# Readme")
    vault.write_note("real", "# Real", domain="dev")
    assert [n.name for n in vault.read_notes()] == ["real"]


# --- replay -------------------------------------------------------------------


def test_replay_uses_same_render_path_as_live(root, log):
    """The bytes a replayed event renders to must equal the live ones."""
    _, event = Orchestrator(log=log).handle("check the repo")
    live = render.render_line(event).plain
    replayed = render.render_line(log.read_all()[0]).plain
    assert live == replayed


def test_replay_selection_by_run(root, log):
    orch_a = Orchestrator(log=log)
    orch_a.handle("check the repo")
    orch_b = Orchestrator(log=log)
    orch_b.handle("run the backtest")

    selection = replay.select(log, run=orch_a.run_id)
    assert len(selection.events) == 1
    assert selection.events[0].payload["query"] == "check the repo"


def test_replay_unknown_run_refuses(root, log):
    log.append(ROUTE, {"query": "q", "outcome": CLEAN}, new_run_id())
    with pytest.raises(replay.SelectionError):
        replay.select(log, run="run_does_not_exist")


def test_replay_empty_log_refuses(root, log):
    with pytest.raises(replay.SelectionError):
        replay.select(log)


def test_replay_since_filters(root, log):
    log.append(ROUTE, {"query": "old", "outcome": CLEAN}, new_run_id())
    selection = replay.select(log, since="1h")
    assert len(selection.events) == 1
    with pytest.raises(replay.SelectionError):
        replay.select(log, since=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())


def test_parse_since_relative_and_iso():
    assert replay.parse_since("2h") < datetime.now(timezone.utc)
    assert replay.parse_since("2026-01-01").year == 2026
    with pytest.raises(replay.SelectionError):
        replay.parse_since("not a time")


def test_replay_emits_every_event_without_sleeping(root, log):
    for i in range(4):
        log.append(ROUTE, {"query": f"q{i}", "outcome": CLEAN}, new_run_id())
    selection = replay.select(log)
    seen = []
    count = replay.run(selection, emit=seen.append, mode=replay.FIXED, sleep=lambda _: None)
    assert count == 4
    assert [e.payload["query"] for e in seen] == ["q0", "q1", "q2", "q3"]


def test_replay_caps_long_gaps(root, log):
    from backend.orchestrator.events import Event

    old = Event(id="a", seq=1, ts="2020-01-01T00:00:00+00:00", run_id="r", type=ROUTE, payload={})
    new = Event(id="b", seq=2, ts="2026-01-01T00:00:00+00:00", run_id="r", type=ROUTE, payload={})
    delays = [d for _, d in replay.pace([old, new], mode=replay.ORIGINAL)]
    assert delays[1] <= replay.MAX_GAP_SECONDS


# --- constitution -------------------------------------------------------------


def test_missing_agentic_os_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_ROOT", str(tmp_path))
    constitution._cached.cache_clear()
    with pytest.raises(constitution.ConstitutionError):
        constitution.load()


def test_agentic_os_without_toml_block_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_ROOT", str(tmp_path))
    constitution._cached.cache_clear()
    (tmp_path / "AGENTIC_OS.md").write_text("# just prose, no config")
    with pytest.raises(constitution.ConstitutionError):
        constitution.load()


def test_shipped_agentic_os_parses():
    """The real AGENTIC_OS.md in this repo must be valid."""
    repo_file = Path(__file__).resolve().parent.parent / "AGENTIC_OS.md"
    config = constitution.load(repo_file)
    assert config["guardrails"]["writable_globs"] == ["skills/*/SKILL.md"]
    assert "AGENTIC_OS.md" in config["guardrails"]["never_writable"]


def test_shipped_skills_are_wellformed():
    """Every shipped SKILL.md parses and every pointer declares a real path."""
    repo = Path(__file__).resolve().parent.parent
    loaded = skills.load_skills(repo / "skills")
    assert set(loaded) == {"dev", "trading", "shared"}
    for branch, skill in loaded.items():
        assert skill.triggers, f"{branch} has no triggers"
        for pointer in skill.pointers:
            assert pointer.target, f"{branch}/{pointer.file.name} declares no path"
            assert pointer.entities, f"{branch}/{pointer.file.name} declares no entities"
