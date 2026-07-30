---
pointer: kaida
path: /home/hxshino/projects/kaida
entities: [kaida, keyboard, keycap, kicad, pcb, cyberdeck]
---

# kaida

Custom mechanical keyboard: layout, PCB, and build journal. Hardware rather than
software, so the useful context here is design decisions, not code.

## Layout

- `kaida/kaida.kicad_pcb`, `.kicad_sch`, `.kicad_pro`, `.kicad_prl` — KiCad project
- `kaida-layout-via.json` — VIA layout definition
- `JOURNAL.md` — running build log, dated entries with time spent
- `kbplacer.log` — output from kbplacer switch placement

## Design decisions already settled

Recorded in `JOURNAL.md`, so do not re-litigate them without reading it:

- TKL-ish arrangement, dedicated arrow cluster, lone `Del` up top — not a 96%
- F-row split into groups of 4 with `0.25u` gaps, matching ANSI spacing so stock
  keycap sets line up
- Stacked arrow cluster rather than inverted-T, nested with negative `y` offsets
- Standard ANSI stagger: `1.75u` Caps, `2.25u` Enter, `2.25u`/`1.75u` Shifts,
  `2u` Backspace — kept compatible with aftermarket keycap kits
- Bottom row `1.25u` mods, `6.25u` spacebar, `a: 7`/`a: 4` alignment flags

Open: whether the mods are sculpted or uniform (`sm: cherry` is a placeholder),
PCB footprint spacing, and plate material.
