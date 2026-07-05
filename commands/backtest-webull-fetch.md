# Backtest Webull Fetch

This command is part of the intended V1 workflow when the source data should
come from Webull historical bars instead of a pre-existing CSV.

Use this command only for read-only Webull Market Data API historical bars.
It fetches bars into a local OHLCV CSV, then the normal backtest workflow can
use that CSV via `init-run --data-path`.

Install the optional Webull SDK dependency first:

```bash
python3 -m pip install -e ".[runtime,webull]"
```

Set credentials in a local `.env` file or shell environment. Do not commit real
Webull keys, secrets, tokens, account IDs, or downloaded market data.

```bash
WEBULL_ENV=uat
WEBULL_REGION=us
WEBULL_APP_KEY=replace_with_your_app_key
WEBULL_APP_SECRET=replace_with_your_app_secret
WEBULL_TOKEN_DIR=.webull-token
```

Fetch daily bars:

```bash
python3 scripts/price_action_backtest.py webull-fetch-bars \
  --symbol AAPL \
  --timespan D \
  --count 500 \
  --output data/private/webull-aapl-d.csv
```

Then initialize a normal backtest:

```bash
python3 scripts/price_action_backtest.py init-run \
  --name "AAPL Webull SMA" \
  --data-path data/private/webull-aapl-d.csv \
  --strategy sma_cross \
  --fast-window 20 \
  --slow-window 50 \
  --fee-bps 5 \
  --slippage-bps 2 \
  --output-root outputs
```

Notes:

- The command uses the official Webull Python SDK.
- It is read-only and does not call trading/order APIs.
- US stock/ETF historical market data may require an active OpenAPI market data
  subscription in Webull.
- Daily bars and above are forward-adjusted per Webull's API documentation;
  minute bars are unadjusted.
