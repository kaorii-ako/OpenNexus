# Vault

Plain markdown, git-tracked, no database. Opens directly as an
[Obsidian](https://obsidian.md) vault — point Obsidian at this folder.

## Layout

```
vault/
├── README.md      # this file
├── evolution/     # orchestrator self-edits, written by `nexus evolve`
├── dev/           # dev domain work
└── trading/       # trading domain work
```

## Frontmatter

Every note carries YAML frontmatter:

```yaml
---
date: 2026-07-27
domain: dev
tags: [routing, skills]
links: [some-other-note]
---
```

- **`date`** — UTC, `YYYY-MM-DD`
- **`domain`** — `dev`, `trading`, or `orchestrator`
- **`tags`** — inline list
- **`links`** — outbound edges, referenced by note slug (the filename without
  `.md`). This is what draws the graph in the HUD.

Inline `[[wikilinks]]` in the body are picked up too, so notes you write by hand
in Obsidian appear in the graph alongside generated ones.

## What lives here

Exactly two kinds of note are written by code:

1. **Domain work** — outputs from dev and trading queries.
2. **Orchestrator self-edits** — one note per applied `nexus evolve` edit, in
   `evolution/`.

Nothing else is generated. Notes you write yourself are of course welcome and
will show up in the graph.

## Self-edit notes

A note in `evolution/` records one applied skill edit. It contains:

- what changed and why, in plain English
- the exact `memory/events.jsonl` entries that motivated it, cited by event id
  **and** line number, so the reasoning can be checked against the log
- the unified diff
- the **complete pre-edit file content**, embedded between
  `<!-- nexus:pre-edit-content:start -->` markers

That last part is why the note is not a summary: `nexus evolve --revert <id>`
reads it back and restores the file byte for byte. If the note is missing or its
pre-edit block is absent, revert refuses rather than guessing — it will tell you
nothing was changed.

## Reading the graph

```bash
nexus hud          # serve the HUD at localhost:8420
```

Node size is link degree. Dangling edges — a `links:` entry pointing at a note
that does not exist — are drawn explicitly rather than dropped, so a broken link
is visible instead of silently disappearing.
