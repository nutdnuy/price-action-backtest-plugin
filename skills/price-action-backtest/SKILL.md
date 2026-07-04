---
name: price-action-backtest
description: Use for price-based technical analysis, OHLCV CSV backtests, indicator calculation, signal validation, leakage checks, and QuantSeras-style visualization reports.
---

# Price Action Backtest

Use this skill when working with price-based technical analysis, OHLCV CSV
backtests, indicator calculation, signal validation, leakage checks, and
QuantSeras-style visualization reports.

Default user-facing language is Thai. Write reusable artifacts, schemas,
technical docs, and code comments in English.

## Read First

- Read `references/workflow.md` before setting up or interpreting a run.
- Read `references/limitations.md` before presenting results or audit findings.
- Treat all outputs as research artifacts and not trading instructions.
- Check for lookahead leakage before accepting any signal or report.
- Do not connect to brokers, place orders, or imply that historical results
  predict future returns.

## Core Workflow

1. Confirm the input is an OHLCV CSV with case-insensitive columns for date,
   open, high, low, close, and volume.
2. Sort dates ascending and reject duplicate dates.
3. Initialize a run folder with a selected V1 strategy, parameter set, fee, and
   slippage assumptions.
4. Run the backtest using signal-at-close timing and next-period position
   application.
5. Render the visualization report with price markers, equity, drawdown,
   monthly heatmap, metrics, trade preview, and limitations.
6. Audit the output for input quality, lookahead risk, missing report artifacts,
   and limitations language.

## CLI Commands

Setup check:

```bash
python3 scripts/price_action_backtest.py setup-check --strict
```

Initialize a run:

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

Run the backtest:

```bash
python3 scripts/price_action_backtest.py run --run-dir "$RUN_DIR"
```

Render the report:

```bash
python3 scripts/price_action_backtest.py render-report --run-dir "$RUN_DIR"
```

Audit the output:

```bash
python3 scripts/price_action_backtest.py audit-output --run-dir "$RUN_DIR"
```

## Supported V1 Strategies

- `sma_cross`
- `ema_cross`
- `rsi_reversion`
- `macd_trend`

## Safety Rules

- Results are historical research artifacts, not trading instructions.
- Do not present a backtest as a prediction, guarantee, or personalized
  investment recommendation.
- Always state the sample period, cost assumptions, and validation limits.
- Flag lookahead, data leakage, duplicate dates, unsorted dates, and missing
  OHLCV columns as audit issues.
- Shift signals one bar and apply them only on the next bar before returns are
  calculated to avoid lookahead.
- Do not connect to brokers, place orders, route orders, or execute trades.
- Keep V1 behavior long/cash only with no leverage.
- Treat no-trade outputs as valid diagnostic information, not a failure to hide.

## Output Shape

A complete run should produce:

- A run directory containing configuration, normalized input metadata, backtest
  outputs, report assets, and audit output.
- Backtest data with positions, returns, equity curve starting at 1.0,
  drawdown, trades, fees, and slippage.
- A report with price markers, equity curve, drawdown chart, monthly heatmap,
  metrics, trade preview, and limitations.
- An audit summary that identifies pass/fail checks and any warnings requiring
  review before sharing results.
