# Price Action Backtest Workflow

## Input Contract

- Input data must be an OHLCV CSV.
- Required columns are case-insensitive: date, open, high, low, close, volume.
- Dates must be parsed into a single date column and sorted ascending before
  indicator calculation or backtesting.
- Duplicate dates are rejected.
- Rows with invalid dates or missing required OHLCV values must be rejected or
  surfaced as audit failures.
- Price and volume columns must be numeric after parsing.

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
