---
branch: trading
name: Trading
---

# Trading

Markets, positions, strategy logic and backtests. This branch exists to prove
the orchestrator generalises across unrelated domains — it is deliberately thin.

Pointer files here point at the real trading system on this machine. Nothing in
this branch reimplements strategy logic, execution, or risk management; that
code already exists and lives elsewhere.

## Triggers

- market
- markets
- position
- positions
- backtest
- strategy
- ticker
- portfolio
- entry
- exit
- stop loss
- equity curve
- drawdown
- broker
- candles

## Pointers

- `stock-new.md` — the live SET100 swing trading system
- `pine-strategy.md` — TradingView Pine strategy and spec
