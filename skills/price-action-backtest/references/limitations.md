# Price Action Backtest Limitations

## Required Caveats

- Historical performance does not guarantee future performance.
- Results depend on data quality, sample period, survivorship bias, corporate
  actions, missing rows, stale prices, timezone handling, and vendor
  adjustments.
- Costs, taxes, liquidity, borrow constraints, market impact, spreads, and
  execution latency are simplified or omitted unless explicitly modeled.
- Parameter choices can be overfit to the sample period.
- Out-of-sample validation, walk-forward validation, robustness checks, and
  sensitivity analysis are required before relying on a strategy research
  result.
- No-trade runs are valid diagnostics and should be reported plainly.
- Outputs provide no personalized investment advice.
- Reports are research artifacts and not trading instructions.

## Minimum Audit Checks

- Required date/OHLC columns exist with case-insensitive matching; volume is
  optional.
- Dates parse successfully, sort ascending, and contain no duplicates.
- Numeric OHLC fields parse successfully; volume parses successfully if present.
- Positions/signals are shifted so `position[t+1] = signal[t]` before returns
  are applied; signal at close t applies only to the next bar's return.
- Position values remain long/cash only.
- Leverage is not used.
- Fees and slippage are applied on position changes.
- Equity starts at 1.0.
- Report artifacts include price markers, equity, drawdown, monthly heatmap,
  metrics, trade preview, and limitations.
- Output language includes historical-performance caveats and avoids
  personalized investment advice.
- Lookahead and data leakage risks are checked and surfaced.
