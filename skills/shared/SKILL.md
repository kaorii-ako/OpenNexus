---
branch: shared
name: Shared
---

# Shared

Conventions used by every domain and by the orchestrator itself.

This branch is listed in `always_load` in `AGENTIC_OS.md`, so it loads on every
query regardless of triggers. That is why its trigger list is short: triggers
here would be redundant, and a branch that is always loaded can never be counted
as `unused`.

## Triggers

- convention
- frontmatter
- vault

## Pointers

- `vault-writer.md` — how notes are written to `vault/`
