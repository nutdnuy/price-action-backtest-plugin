# Price Action Backtest Workflow

## Input Contract

- Optional Webull input flow fetches read-only historical bars from the Webull
  Market Data API into a local OHLCV CSV under a gitignored folder such as
  `data/private/`.
- Input data must be a price CSV with OHLC columns. Volume may be included as
  optional OHLCV data.
- Required columns are case-insensitive: date, open, high, low, close.
- Optional columns are case-insensitive: volume.
- Dates must be parsed into a single date column and sorted ascending before
  indicator calculation or backtesting.
- Duplicate dates are rejected.
- Rows with invalid dates or missing required date/OHLC values must be rejected or
  surfaced as audit failures.
- Required price columns must be numeric after parsing; volume must be numeric
  if present.
- Webull daily bars and higher intervals are forward-adjusted according to
  Webull's API documentation; minute bars are unadjusted. Note the interval and
  source when presenting results.
- Do not commit real Webull credentials, token directories, or downloaded
  private market data.

## Backtest Contract

- V1 supports a single asset in long/cash only.
- V1 does not support shorting, leverage, margin, options, futures, or broker
  execution.
- Signals are computed using data available at close `t`.
- Signal timing is explicit: `position[t+1] = signal[t]`.
- A signal at close t applies only to the next bar's return.
- Position changes occur only when the target position differs from the current
  position.
- Fee and slippage are charged on position change.
- Fee and slippage are simple basis-point assumptions, not exchange-accurate
  execution simulations.
- Equity starts at 1.0.
- Strategy metrics must be derived from the backtest equity and return series,
  not from future data.
- The implementation must avoid lookahead leakage in indicator, signal, return,
  and position alignment.

## Report Contract

- The report includes price markers for entries and exits.
- The report includes an equity curve.
- The report includes a drawdown chart.
- The report includes a monthly heatmap.
- The report includes summary metrics.
- The report includes a trade preview.
- The report includes limitations.
- Reports are research artifacts and not trading instructions.
