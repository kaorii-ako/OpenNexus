---
pointer: stock-new
path: /home/hxshino/projects/Stock-new
entities: [stock-new, set100, swing, qullamaggie, rs ranking, atr]
---

# Stock-new — SET100 swing trading system

The actual trading bot. Blends Qullamaggie breakout / episodic-pivot momentum,
volatility-based risk management, and quant momentum principles (RS ranking,
sector rotation, regime filtering).

**Do not reimplement any of this here.** This file is a pointer so the
orchestrator knows where the system lives and what shape it has.

## Layout

| Path | What |
|------|------|
| `main.py`, `run_strategy.py` | entrypoints |
| `strategies/swing_strategy.py` | the strategy |
| `strategies/backtest_engine.py` | backtester |
| `strategies/paper_trading.py` | paper mode |
| `strategies/visualization.py`, `visualize_results.py` | charting |
| `strategies/pine/` | Pine ports |
| `execution/live_trading.py` | live execution |
| `execution/broker.py` | broker interface |
| `execution/tv_webhook_bridge.py` | TradingView webhook bridge |
| `execution/discord_notifier.py` | Discord alerts |
| `config/strategy_config.yaml` | main config |
| `config/strategy_config_10min.yaml` | 10-minute variant |
| `config/strategy_config_flat_spike.yaml` | flat-spike variant |
| `config/set100_symbols.txt` | universe |
| `backtest_results/` | equity curve, trades, charts, candle parquet |
| `state.json` | live state |
| `logs/` | run logs |

## Strategy shape

- Three setups: consolidation breakout, episodic pivot / gap, pullback to EMA10
- Screening: RS percentile ≥ 70, EMA alignment, volume and liquidity filters
- Risk: ATR-based stops — 2.0× initial, 2.5× trailing, 1% risk per trade
- Portfolio: max 10 positions, 30% sector cap, 15% single-position cap
- Partial exits: 33% at 1R, 33% at 2R, 34% runner at 3R+
- Regime filter: index > EMA50, positive slope, >50% breadth, VIX < 30

## Caution

`api_key.txt` sits in that repo root. Do not read, echo, or copy it.
