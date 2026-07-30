---
pointer: flarebisect
path: /home/hxshino/projects/FlareBisect
entities: [flarebisect, flaky, bisect, flake-rate]
---

# FlareBisect

Finds the commit that made a test flaky, rather than the commit that broke it.
Bisects on flake-rate drift instead of pass/fail, then explains the culprit.

Published on PyPI as `flarebisect`. MIT. CI via GitHub Actions.

## Layout

- `src/` — package source
- `tests/` — test suite
- `demo/` — worked example
- `scripts/` — dev tooling
- `pyproject.toml`, `CHANGELOG.md`

## Why it exists

`git bisect` treats each run as a clean pass/fail signal, so it gives
confidently wrong answers when the test being bisected on is itself flaky.
FlareBisect samples repeatedly per commit and bisects on the change in flake
rate.
