"""NEXUS orchestrator — skill routing with an append-only accountability log.

Modules:
    paths       filesystem layout, repo-root discovery
    events      append-only event log (memory/events.jsonl)
    skills      SKILL.md / pointer-file parsing
    router      trigger match, entity resolution, derived outcome signal
    guardrails  code-enforced write scope for self-modification
    vault       markdown vault notes with YAML frontmatter
    evolve      friction analysis, proposals, apply/revert
    replay      re-emit logged events through the live render path
"""
