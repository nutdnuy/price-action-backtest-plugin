# Backtest Init Run

These commands are the intended V1 workflow and become runnable after the
CLI/runtime tasks are implemented.

If the CSV path is missing, ask the user for the OHLCV CSV path before running
the command.

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
