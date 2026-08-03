<div align="center">

# Price Action Backtest

### Webull historical bars → transparent, reproducible research reports

<p>
  <a href="https://github.com/nutdnuy/price-action-backtest-plugin"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.11 or newer"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-69F0AE?style=flat-square" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/Webull-read--only%20market%20data-03DAC6?style=flat-square" alt="Read-only Webull market data">
  <img src="https://img.shields.io/badge/AI%20Battle-event%20ready-FF5252?style=flat-square" alt="AI Battle event ready">
</p>

<p>
  <strong>Claude Code and Codex Agent-native backtesting for OHLCV data.</strong><br>
  Fetch historical bars from Webull, test a transparent price-action strategy,
  render a research dashboard, and audit the result before sharing it.
</p>

<p>
  <a href="#quick-start">Quick start</a> ·
  <a href="#webull-workflow">Webull workflow</a> ·
  <a href="#agent-workflow">Agent workflow</a> ·
  <a href="#safety-boundary">Safety boundary</a>
</p>

</div>

> [!IMPORTANT]
> This is a historical research tool. Webull integration is read-only market-data
> import: this project does not place orders, route trades, or predict future
> returns.

## What this is

`price-action-backtest-plugin` is a small, inspectable research workflow that
turns price bars into comparable evidence:

```text
Webull bars or OHLCV CSV
        ↓
normalize + validate
        ↓
indicators + signal
        ↓
next-bar backtest with fees and slippage
        ↓
metrics + equity + trades
        ↓
QuantSeras-style HTML report
        ↓
audit + limitations
```

It is designed for three audiences:

| Use case | What you get |
| --- | --- |
| **AI Battle demo** | A no-credential sample run that anyone can reproduce in minutes |
| **Webull research** | Read-only historical-bar import through the official Python SDK |
| **Agent handoff** | A Claude Code/Codex skill, prompts, acceptance test, and support boundary |

## Why it is useful

- **Reproducible** — every run keeps its configuration, input reference, trades,
  equity curve, metrics, report, and audit result together.
- **Leakage-aware** — signals are generated at the close and applied on the next
  bar; same-bar lookahead is not part of the V1 engine.
- **Cost-aware** — fee and slippage assumptions are explicit basis-point inputs.
- **Inspectable** — the core engine is ordinary Python, pandas, and Plotly; no
  hidden hosted service is required.
- **Agent-ready** — Claude Code and Codex can execute the same setup, run, report,
  and audit sequence.
- **Safe to share** — credentials, token directories, and private downloaded data
  are ignored and must stay outside the repository.

## At a glance

| Layer | V1 contract |
| --- | --- |
| **Input** | CSV with `date`, `open`, `high`, `low`, `close`; `volume` is optional |
| **Strategies** | SMA cross, EMA cross, RSI reversion, MACD trend |
| **Position model** | Single asset, long/cash, no leverage |
| **Timing** | Signal at close; position applied on the next bar |
| **Costs** | Fee and slippage in basis points |
| **Outputs** | `equity.csv`, `trades.csv`, `metrics.json`, `report.html`, audit JSON |
| **Data connector** | Webull OpenAPI historical market data only |
| **Python** | 3.11 or newer |

## Quick start

### Five-minute demo — no Webull credentials required

This path is ideal for the AI Battle handout. It uses the included sample OHLCV
file, so every participant can reproduce the workflow without an account or a
market-data subscription.

```bash
git clone https://github.com/nutdnuy/price-action-backtest-plugin.git
cd price-action-backtest-plugin

python3 -m venv .venv
.venv/bin/python -m pip install -e ".[runtime,dev]"
.venv/bin/python scripts/price_action_backtest.py setup-check --strict

.venv/bin/python scripts/price_action_backtest.py init-run \
  --name "SMA demo" \
  --data-path templates/sample-ohlcv.csv \
  --strategy sma_cross \
  --fast-window 5 \
  --slow-window 20 \
  --fee-bps 5 \
  --slippage-bps 2 \
  --output-root outputs

RUN_DIR=$(find outputs -maxdepth 1 -type d -name '*-sma-demo' | sort | tail -1)
.venv/bin/python scripts/price_action_backtest.py run --run-dir "$RUN_DIR"
.venv/bin/python scripts/price_action_backtest.py render-report --run-dir "$RUN_DIR"
.venv/bin/python scripts/price_action_backtest.py audit-output --run-dir "$RUN_DIR"
```

Open the generated `report.html` inside the printed run directory. The
`outputs/` folder is gitignored, so local experiments do not pollute the repo.

### Try another strategy

Change `--strategy` to one of:

```text
sma_cross       fast SMA above slow SMA
ema_cross       fast EMA above slow EMA
rsi_reversion   enter on low RSI, exit on recovery
macd_trend      MACD above its signal line
```

## Webull workflow

The Webull path uses the official Webull Python SDK to fetch read-only historical
bars, normalize them into the same OHLCV contract, and hand them to the normal
backtest engine. The connector does not call trading or order endpoints.

### 1. Install the optional Webull dependency

```bash
.venv/bin/python -m pip install -e ".[runtime,webull]"
```

### 2. Add credentials locally

Create a local `.env` file or export these variables in your shell:

```dotenv
WEBULL_ENV=uat
WEBULL_REGION=us
WEBULL_APP_KEY=replace_with_your_app_key
WEBULL_APP_SECRET=replace_with_your_app_secret
WEBULL_TOKEN_DIR=.webull-token
```

Never paste real values into a README, issue, notebook, screenshot, commit, or
shared event chat. `.env` and `.webull-token/` are gitignored by default.

### 3. Fetch historical bars

```bash
.venv/bin/python scripts/price_action_backtest.py webull-fetch-bars \
  --symbol AAPL \
  --timespan D \
  --count 500 \
  --output data/private/webull-aapl-d.csv
```

### 4. Run the normal backtest pipeline

```bash
.venv/bin/python scripts/price_action_backtest.py init-run \
  --name "AAPL Webull SMA" \
  --data-path data/private/webull-aapl-d.csv \
  --strategy sma_cross \
  --fast-window 20 \
  --slow-window 50 \
  --fee-bps 5 \
  --slippage-bps 2 \
  --output-root outputs

RUN_DIR=$(find outputs -maxdepth 1 -type d -name '*-aapl-webull-sma' | sort | tail -1)
.venv/bin/python scripts/price_action_backtest.py run --run-dir "$RUN_DIR"
.venv/bin/python scripts/price_action_backtest.py render-report --run-dir "$RUN_DIR"
.venv/bin/python scripts/price_action_backtest.py audit-output --run-dir "$RUN_DIR"
```

### Webull data notes

- The app key and app secret must match the selected `WEBULL_ENV` endpoint.
- US stock/ETF historical data may require an active Webull OpenAPI market-data
  subscription and approved permissions.
- Shared UAT credentials may be restricted to AAPL. Production credentials may
  be required for other symbols or ETFs.
- Daily bars and higher intervals are forward-adjusted according to Webull API
  documentation; minute bars are unadjusted.
- The connector stores only the local CSV you request; it never publishes raw
  credentials or private data.

See the [Webull fetch command](commands/backtest-webull-fetch.md) for the focused
connector instructions.

## Agent workflow

### Install in Codex

```text
codex plugin marketplace add nutdnuy/price-action-backtest-plugin
```

Then install `price-action-backtest-plugin` from the Codex plugin UI.

### Install in Claude Code

```text
/plugin marketplace add https://github.com/nutdnuy/price-action-backtest-plugin
/plugin install price-action-backtest-plugin
```

### Useful agent prompts

```text
Use price-action-backtest-plugin to run the sample SMA backtest. Perform a
strict setup check, run the backtest, render the HTML report, audit the output,
and summarize the metrics and limitations. Do not use trading APIs.
```

```text
Use price-action-backtest-plugin to fetch read-only Webull historical bars for
AAPL with timespan D and count 500 into data/private/webull-aapl-d.csv. Then
run an SMA 20/50 backtest with fee_bps=5 and slippage_bps=2, render the report,
audit the artifacts, and explain the data-source limitations. Do not place or
preview orders.
```

### Customer or participant handoff

The `customer-handoff/` folder is a ready-made handoff kit for another owner or
agent. It includes:

- an owner brief and adaptation questions;
- a local installation checklist;
- a no-credential acceptance test;
- a clear support boundary; and
- the `/backtest-handoff-to-customer` workflow prompt.

Start here:

```text
Use this repository as a price-action backtest customer handoff kit. Read
customer-handoff/OWNER_BRIEF.md first, then ask me the adaptation questions one
at a time. Treat the output as historical research, not a trading instruction.
```

## What a run produces

```text
outputs/<run-id>/
├── config.json       # strategy, windows, costs, and creation time
├── equity.csv        # returns, position, turnover, costs, equity, drawdown
├── trades.csv        # entry/exit changes and transaction costs
├── metrics.json      # return, volatility, Sharpe, drawdown, trades, costs
├── report.html       # standalone QuantSeras-style research dashboard
└── audit.json        # generated audit summary when captured by the caller
```

The audit command checks the required artifacts, cost assumptions, no-trade
results, and extreme drawdown warnings. A warning is a reason to investigate,
not something to hide.

## Explainable target-price MVP

After importing Webull historical bars, the optional target-price command creates
a deterministic explanation artifact from historical OHLCV structure:

```bash
.venv/bin/python scripts/price_action_backtest.py explain-target \
  --symbol AAPL \
  --data-path data/private/webull-aapl-d.csv \
  --lookback 120 \
  --horizon-days 126 \
  --output outputs/aapl-target/target_explanation.json

.venv/bin/python scripts/price_action_backtest.py render-target-report \
  --payload-path outputs/aapl-target/target_explanation.json \
  --output outputs/aapl-target/target_report.html
```

It uses a recent price channel, trend return, volatility, and drawdown to create
heuristic P10/P25/P50/P75/P90 bands. This is an explainable research artifact,
not a price forecast, investment advice, or trading instruction.

## Research contract

The V1 engine deliberately stays small and explicit:

1. Validate required OHLC data, dates, ordering, duplicates, and numeric values.
2. Calculate indicators from the available historical rows.
3. Generate a binary long/cash signal.
4. Shift the signal by one bar before applying the position.
5. Charge the configured fee and slippage when turnover occurs.
6. Produce comparable equity, trades, metrics, and report artifacts.
7. Audit the result and preserve limitations alongside the output.

This is a foundation for research conversations, not a claim that a strategy is
profitable or ready for production execution.

## Visualization

Reports use a dark QuantSeras-style research dashboard:

| Role | Visual treatment |
| --- | --- |
| **Surface** | Near-black analytical panels |
| **Strategy** | Neon green highlight |
| **Benchmark** | Cyan secondary accent |
| **Risk** | Red drawdown and warning states |
| **Evidence** | Equity curve, price markers, trades, monthly returns, metrics, and limitations |

The report is designed to make the result easy to inspect—not to make a weak
backtest look persuasive.

## Safety boundary

### Included

- Historical OHLCV import and validation
- Read-only Webull historical-bar import
- Transparent single-asset price-action backtests
- Explicit fee and slippage assumptions
- Lookahead-aware signal timing
- HTML reports and output audits
- Agent handoff and acceptance-test guidance

### Not included

- Account, position, order, or execution APIs
- Live trading or paper-trading automation
- Portfolio construction or leverage
- Guaranteed returns or investment recommendations
- Market-data subscriptions or Webull credentials
- Unlimited custom strategy consulting

> [!WARNING]
> Never commit real Webull app keys, app secrets, tokens, account IDs, `.env`
> files, or downloaded private market data. Use your own approved credentials
> locally and keep all research results labelled as historical evidence.

## Limitations

- Historical backtests do not guarantee future performance.
- V1 is single-asset, long/cash, and unlevered.
- Fees and slippage are simple basis-point assumptions, not a full execution model.
- Results depend on data quality, corporate actions, survivorship, liquidity, and
  the selected sample period.
- Webull historical-bar support is market-data import only; it is not live trading.
- The target-price MVP is a heuristic explanation, not a predictive model.

## Development

Use the repository virtual environment so validation runs on the intended Python
runtime:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[runtime,dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check .
```

Optional plugin validation:

```bash
.venv/bin/python -m pip install PyYAML
.venv/bin/python /Users/nuthdanai/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

The test suite uses fake Webull clients for connector checks; it does not need to
call live Webull. Install the `webull` extra only when you need a real historical
data import.

## Repository map

```text
price-action-backtest-plugin/
├── commands/                 # Agent-facing setup, run, report, audit prompts
├── customer-handoff/         # Participant/customer installation kit
├── scripts/                  # Stable command-line entry point
├── skills/                   # Claude Code/Codex skill definition
├── src/price_action_backtest/ # Data, indicators, signals, engine, reports, audit
├── templates/                # Credential-free sample OHLCV input
└── tests/                    # Offline unit and contract tests
```

## License

Released under the [MIT License](LICENSE).

Historical results are research artifacts. The human researcher remains
responsible for interpreting assumptions, checking evidence, and making any
investment decision.
