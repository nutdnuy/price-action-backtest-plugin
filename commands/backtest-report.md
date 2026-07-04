# Backtest Report

Find the latest `*-sma-demo` run directory and render the report:

```bash
RUN_DIR=$(find outputs -maxdepth 1 -type d -name '*-sma-demo' | sort | tail -1)
python3 scripts/price_action_backtest.py render-report --run-dir "$RUN_DIR"
```
