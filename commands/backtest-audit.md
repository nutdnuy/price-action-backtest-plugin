# Backtest Audit

Find the latest `*-sma-demo` run directory and audit the output:

```bash
RUN_DIR=$(find outputs -maxdepth 1 -type d -name '*-sma-demo' | sort | tail -1)
python3 scripts/price_action_backtest.py audit-output --run-dir "$RUN_DIR"
```
