# price-action-backtest-plugin

Claude Code and Codex Agent-native plugin for technical-analysis backtesting
from OHLCV price data, with QuantSeras-style visualization reports.

The workflow:

```text
OHLCV CSV -> indicators -> signal -> backtest -> metrics -> report -> audit
```

This plugin does not connect to brokers, does not place orders, and does not
claim that historical results predict future returns.

## Install In Codex

```bash
codex plugin marketplace add nutdnuy/price-action-backtest-plugin
```

Then install `price-action-backtest-plugin` from the Codex plugin UI.

## Install In Claude Code

```text
/plugin marketplace add https://github.com/nutdnuy/price-action-backtest-plugin
/plugin install price-action-backtest-plugin
```

## Runtime Setup

```bash
python3 -m pip install -e ".[runtime,dev]"
python3 scripts/price_action_backtest.py setup-check --strict
```

## Quick Start

```bash
python3 scripts/price_action_backtest.py init-run \
  --name "SMA demo" \
  --data-path templates/sample-ohlcv.csv \
  --strategy sma_cross \
  --fast-window 5 \
  --slow-window 20 \
  --fee-bps 5 \
  --slippage-bps 2 \
  --output-root outputs
```

```bash
RUN_DIR=$(find outputs -maxdepth 1 -type d -name '*-sma-demo' | sort | tail -1)
python3 scripts/price_action_backtest.py run --run-dir "$RUN_DIR"
python3 scripts/price_action_backtest.py render-report --run-dir "$RUN_DIR"
python3 scripts/price_action_backtest.py audit-output --run-dir "$RUN_DIR"
```

## Supported V1 Strategies

- `sma_cross` — long/cash strategy that is long when the fast simple moving
  average is above the slow simple moving average.
- `ema_cross` — long/cash strategy that is long when the fast exponential moving
  average is above the slow exponential moving average.
- `rsi_reversion` — long/cash mean-reversion strategy that enters on low RSI and
  exits when RSI recovers above the exit threshold.
- `macd_trend` — long/cash trend strategy that is long when MACD is above its
  signal line.

All V1 strategies are single-asset, long/cash only, with one-bar signal shifting
to avoid same-bar lookahead.

## Visualization Theme

Reports use a QuantSeras-style dark research dashboard:

- Backgrounds use near-black surfaces (`#121212`, `#1D1D1D`, `#212121`).
- Strategy highlights use neon green (`#69F0AE`, `#00E676`).
- Benchmark and secondary accents use cyan (`#03DAC6`).
- Losses and drawdowns use red (`#FF5252`).
- Report sections include price markers, strategy equity vs buy-and-hold,
  drawdown, monthly returns heatmap, summary metrics, trade preview, and
  limitations language.

## Limitations

- Historical backtests do not guarantee future performance.
- V1 supports single-asset long/cash backtests only.
- Costs and slippage are simple basis-point assumptions.
- Results depend on data quality, survivorship, corporate actions, and sample period.
- Reports are research artifacts, not trading instructions.
