# AGENTIC_OS

Core routing rules for the NEXUS orchestrator.

This file is the constitution. It defines **how** routing decides, **what** counts
as friction, and **what the orchestrator is allowed to modify**. The orchestrator
reads this file on every turn and can never write to it — that restriction is
enforced in `backend/orchestrator/guardrails.py`, not by convention.

The split of responsibility is deliberate:

| File | Holds | Mutable by orchestrator |
|------|-------|-------------------------|
| `AGENTIC_OS.md` (this file) | routing policy, thresholds, write scope | **no** |
| `skills/<branch>/SKILL.md` | the trigger phrases for that branch | **yes** |
| `skills/<branch>/*.md` (pointers) | context pointers to real projects | **no** |
| `backend/orchestrator/*.py` | the evolution logic itself | **no** |

So the system can learn *which words route where* without ever being able to
rewrite *how routing works* or *what it may touch*.

---

## Routing algorithm

A query is routed in three phases. All three are recorded in the event log.

**Phase 1 — trigger match.** Each branch's `SKILL.md` declares trigger phrases.
The query is matched against every branch's triggers using the `match` policy
below. Branches with at least one hit are the *selected* branches. Branches
listed in `always_load` are selected unconditionally.

**Phase 2 — entity resolution.** Each pointer file in a selected branch declares
`entities` in its frontmatter (project names, tickers, tool names). The router
extracts which entities the query actually references. If the query references an
entity that lives in a branch that Phase 1 did **not** select, the router must
load that branch mid-turn to answer. That is a **correction**.

**Phase 3 — outcome signal.** Derived, never invented:

- `clean` — Phase 1 selected exactly the branches Phase 2 needed.
- `corrected` — Phase 2 forced a branch load that Phase 1 missed. The event
  records which entity caused it and which branch had to be added.
- `unused` — a branch was selected by trigger match but contributed no entity to
  the resolution. Its trigger fired on a query it had nothing to say about.

There is no confidence score. There is no model-judged quality rating. The signal
is a description of what mechanically happened during the turn, and nothing else.

---

## Friction patterns

`nexus evolve` may only propose an edit when one of these patterns is present in
real logged events, at or above `min_pattern_occurrences`:

- **`missing_trigger`** — the same entity repeatedly caused a `corrected` outcome
  into branch B, and the term that caused it is absent from B's `SKILL.md`
  triggers. Proposal: add that trigger phrase to B.
- **`overbroad_trigger`** — a specific trigger phrase in branch B repeatedly
  produced an `unused` outcome for B. Proposal: remove or narrow that phrase.
- **`stale_pointer`** — a pointer file's `path:` frontmatter no longer exists on
  disk. Proposal: flag it in the owning `SKILL.md`.
- **`overloaded_skill`** — one branch's triggers resolve to two disjoint entity
  clusters with no co-occurrence across the whole log. Proposal: record the split
  boundary in `SKILL.md`.

**One exemption, stated explicitly so the code and this document cannot differ.**
`stale_pointer` is exempt from both `min_events` and `min_pattern_occurrences`.
It is the only pattern verified directly against the filesystem rather than
inferred from logged behaviour: the path is either there or it is not, and one
observation of its absence is complete evidence. Every other pattern is
statistical and fully gated. This exemption is implemented in
`evolve.FILESYSTEM_VERIFIED`.

Two of these patterns describe problems the orchestrator is deliberately unable
to fix. A stale pointer lives in a pointer file, and splitting a skill means
creating a directory and moving pointer files — all outside the write scope
below. In those cases the proposal records the finding in `SKILL.md` and says
plainly that a human has to do the rest. The system reporting a problem it
cannot touch is the guardrail working, not a gap in it.

If no pattern reaches threshold, `nexus evolve` reports **not enough signal yet**
and exits without proposing. Producing a plausible-sounding improvement in the
absence of evidence is a failure of the system, not a feature of it.

---

## Machine-read configuration

Everything below is parsed by `backend/orchestrator/router.py` and
`guardrails.py`. The prose above describes it; this block *is* it. They cannot
drift, because there is only one copy.

```toml
[routing]
branches = ["dev", "trading", "shared"]
always_load = ["shared"]
match = "word_boundary_ci"
# Matching is word-boundary anchored, so short triggers are safe: "CI" and "PR"
# are real trigger phrases and must not be silently discarded. This floor exists
# only to stop a single character becoming a trigger.
min_trigger_len = 2

[evolve]
# Below min_events total routing events, evolve refuses to propose at all.
min_events = 12
# A friction pattern must recur at least this many times to be actionable.
min_pattern_occurrences = 3
# Exactly one proposal per run. Never batch edits.
max_proposals_per_run = 1

[guardrails]
# Deny-by-default. A write is permitted only if the resolved real path matches
# one of these globs, relative to the repo root. Everything else is refused,
# including this file.
writable_globs = ["skills/*/SKILL.md"]

# Checked first and always refused, even if some future glob would match.
# Defence in depth against an allowlist edit widening scope by accident.
never_writable = [
  "AGENTIC_OS.md",
  "backend/orchestrator/*.py",
  "skills/*/[!S]*.md",
]
```

---

## Invariants

1. `memory/events.jsonl` is append-only. Nothing in this codebase opens it for
   truncation or rewriting. Events are never backfilled, edited, or synthesised.
2. Live routing and `nexus replay` read and render the identical event schema
   through the identical code path. There is no separate recorded demo, because
   there is no separate recording — there is only the log, and the ability to
   look at it.
3. No code path in this system behaves differently based on whether it is being
   observed. There is no demo mode, presentation mode, or rehearsal flag.
4. Every applied evolution stores the complete pre-edit file content in its vault
   note, so `nexus evolve --revert <id>` is always possible.
