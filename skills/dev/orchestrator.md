---
pointer: orchestrator
path: /home/hxshino/projects/OpenNexus
entities: [opennexus, nexus, agentic_os, hud, events.jsonl, evolve, replay]
---

# OpenNexus

This project. A personal AI command centre published to PyPI as `opennexus-ai`,
CLI entrypoint `nexus`.

## Where things are

| Area | Path |
|------|------|
| Routing rules (immutable to the orchestrator) | `AGENTIC_OS.md` |
| Orchestrator | `backend/orchestrator/` |
| Event log | `memory/events.jsonl` |
| Skills | `skills/` |
| Vault | `vault/` |
| HUD | `hud/` |
| Existing assistant (RAG, digest, connectors) | `backend/` |
| CLI | `cli/main.py` |

## Orchestrator modules

- `paths.py` — repo-root discovery, filesystem layout
- `constitution.py` — parses the config block out of `AGENTIC_OS.md`
- `events.py` — append-only JSONL log, integrity verification
- `skills.py` — SKILL.md and pointer parsing, pure edit helpers
- `router.py` — three-phase routing, derived outcome signal
- `guardrails.py` — deny-by-default write scope
- `evolve.py` — friction detection, proposals, apply/revert
- `replay.py` — event selection and pacing
- `render.py` — the single render path shared by live output and replay
- `vault.py` — markdown notes, link graph

## Things worth remembering

- The event log is append-only and `nexus events --verify` will detect a
  hand-edit as a `seq` mismatch.
- The orchestrator can only write `skills/*/SKILL.md`. This is enforced in
  `guardrails.py`, not by prompt instruction.
- Live output and `nexus replay` both render through `render.render_line`.
  There is deliberately no second formatter.

## Pre-existing subsystems (unchanged by the orchestrator work)

ChromaDB RAG over Notion, morning digest, connectors for Gmail / Calendar /
Classroom / GitHub / Discord / RSS / Weather, React frontend at `frontend/`,
FastAPI at `backend/api/`. Note that `backend/core/memory.py` is the *vector*
store — unrelated to `memory/events.jsonl`.
