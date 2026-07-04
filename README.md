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

## Limitations

- Historical backtests do not guarantee future performance.
- V1 supports single-asset long/cash backtests only.
- Costs and slippage are simple basis-point assumptions.
- Results depend on data quality, survivorship, corporate actions, and sample period.
- Reports are research artifacts, not trading instructions.
