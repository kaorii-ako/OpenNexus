---
pointer: pine-strategy
path: /home/hxshino/projects/tradingview
entities: [pine, tradingview, momentum breakout, freqtrade, tradingos]
---

# TradingView / Pine

Pine Script strategy work and its written spec, separate from the Python system
in `stock-new.md`.

## Layout

- `momentum_breakout_strategy.pine` — the strategy
- `momentum_breakout_spec.md` — the spec it implements
- `freqtrade/` — Freqtrade experiments
- `tradingos/` — related work
- `AGENTS.md`, `CLAUDE.md` — that repo's own agent instructions
- `to resume.txt` — parked notes

## Relationship to Stock-new

`Stock-new/strategies/pine/` holds Pine ports of the Python strategy. This repo
is where Pine-first work happens. When a query is about Pine syntax or
TradingView alerts, this is the pointer; when it is about live execution or the
backtester, `stock-new.md` is.
