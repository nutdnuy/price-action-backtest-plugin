# Webull Explainable Target Price Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only Webull-to-explainable-target-price MVP that turns OHLCV bars into price structure features, probability bands, an explainable target JSON artifact, and a standalone HTML report.

**Architecture:** Keep the existing Webull import and backtest workflow intact. Add a small, deterministic research layer that reads normalized OHLCV CSVs, computes transparent price-structure features, derives heuristic forward price bands, writes `target_explanation.json`, and renders a QuantSeras-style HTML report. Webull stays read-only through the existing `webull-fetch-bars` command; this feature consumes the CSV output and never calls order or trading APIs.

**Tech Stack:** Python 3.11, pandas, numpy, Plotly-free HTML rendering for the target report, existing `price-action-backtest-plugin` CLI, pytest, ruff.

---

## Scope Check

This plan covers one subsystem only: explainable target price research artifacts from OHLCV bars, including Webull CSV inputs. It does not add LLM transcript extraction, options fair value, portfolio analytics, OpenBB widgets, MCP tools, or live trading. Those are separate plans because each can produce independently testable software.

## File Structure

- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/explainable_target.py`
  - Responsibility: pure calculation layer for price structure features, heuristic forward return distribution, target price, drivers, and JSON-serializable explanation payloads.
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/target_reports.py`
  - Responsibility: render a standalone QuantSeras-style HTML report from `target_explanation.json`.
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/scripts/price_action_backtest.py`
  - Responsibility: add `explain-target` and `render-target-report` CLI commands while preserving existing commands.
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_explainable_target.py`
  - Responsibility: unit-test feature calculation, probability bands, limitation text, and JSON file output.
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_target_reports.py`
  - Responsibility: unit-test HTML report rendering and CLI report command behavior.
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_cli_setup.py`
  - Responsibility: test `explain-target` CLI JSON output with the bundled sample OHLCV CSV.
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/README.md`
  - Responsibility: document the Webull -> explain-target -> target report workflow, credential safety, and research limitations.

## Task 1: Price Structure Feature Engine

**Files:**
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/explainable_target.py`
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_explainable_target.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_explainable_target.py` with this initial content:

```python
import math

import pandas as pd

from price_action_backtest.explainable_target import compute_price_structure_features


def sample_ohlcv() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                ]
            ),
            "open": [100.0, 101.0, 103.0, 104.0, 107.0, 109.0],
            "high": [101.0, 103.0, 105.0, 107.0, 110.0, 112.0],
            "low": [99.0, 100.0, 102.0, 103.0, 106.0, 108.0],
            "close": [100.0, 102.0, 104.0, 106.0, 109.0, 111.0],
            "volume": [1000, 1100, 1200, 1300, 1250, 1400],
        }
    )


def test_compute_price_structure_features_uses_recent_window():
    features = compute_price_structure_features(sample_ohlcv(), lookback=4)

    assert features.as_of_date == "2026-01-07"
    assert features.last_close == 111.0
    assert features.channel_low == 102.0
    assert features.channel_high == 112.0
    assert features.channel_midpoint == 107.0
    assert features.channel_width_pct == 10.0 / 111.0
    assert features.channel_position == 0.4
    assert features.trend_return == (111.0 / 104.0) - 1.0
    assert features.drawdown_from_high == (111.0 / 112.0) - 1.0
    assert features.annualized_volatility > 0.0
    assert math.isfinite(features.annualized_volatility)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_explainable_target.py::test_compute_price_structure_features_uses_recent_window -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'price_action_backtest.explainable_target'`.

- [ ] **Step 3: Write minimal implementation**

Create `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/explainable_target.py` with:

```python
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from price_action_backtest.data import normalize_ohlcv_frame

LIMITATIONS_TEXT = (
    "This target price is a deterministic research estimate from historical OHLCV "
    "structure. It is not a forecast guarantee, investment advice, or trading instruction."
)


@dataclass(frozen=True)
class PriceStructureFeatures:
    as_of_date: str
    last_close: float
    lookback_rows: int
    channel_low: float
    channel_high: float
    channel_midpoint: float
    channel_width_pct: float
    channel_position: float
    trend_return: float
    annualized_volatility: float
    drawdown_from_high: float


def compute_price_structure_features(data: pd.DataFrame, lookback: int = 120) -> PriceStructureFeatures:
    if lookback < 2:
        raise ValueError("lookback must be at least 2")

    clean = normalize_ohlcv_frame(data, min_rows=2)
    window = clean.tail(min(lookback, len(clean))).copy()
    first_close = float(window["close"].iloc[0])
    last_close = float(window["close"].iloc[-1])
    channel_low = float(window["low"].min())
    channel_high = float(window["high"].max())
    channel_midpoint = (channel_low + channel_high) / 2.0
    channel_width = channel_high - channel_low
    channel_width_pct = channel_width / last_close if last_close else 0.0
    channel_position = ((last_close - channel_midpoint) / channel_width) if channel_width else 0.0
    trend_return = (last_close / first_close) - 1.0
    daily_returns = window["close"].pct_change().dropna()
    annualized_volatility = float(daily_returns.std(ddof=0) * math.sqrt(252)) if not daily_returns.empty else 0.0
    drawdown_from_high = (last_close / channel_high) - 1.0 if channel_high else 0.0

    return PriceStructureFeatures(
        as_of_date=pd.Timestamp(window["date"].iloc[-1]).strftime("%Y-%m-%d"),
        last_close=last_close,
        lookback_rows=int(len(window)),
        channel_low=channel_low,
        channel_high=channel_high,
        channel_midpoint=channel_midpoint,
        channel_width_pct=channel_width_pct,
        channel_position=channel_position,
        trend_return=trend_return,
        annualized_volatility=annualized_volatility,
        drawdown_from_high=drawdown_from_high,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_explainable_target.py::test_compute_price_structure_features_uses_recent_window -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/price_action_backtest/explainable_target.py tests/test_explainable_target.py
git commit -m "feat: add price structure feature engine"
```

## Task 2: Explainable Target Payload

**Files:**
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/explainable_target.py`
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_explainable_target.py`

- [ ] **Step 1: Write the failing test**

Append this to `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_explainable_target.py`:

```python
import json

from price_action_backtest.explainable_target import build_explainable_target, write_target_explanation


def test_build_explainable_target_returns_ordered_probability_bands():
    payload = build_explainable_target(sample_ohlcv(), symbol="AAPL", lookback=4, horizon_days=126)

    bands = payload["price_bands"]
    assert payload["symbol"] == "AAPL"
    assert payload["as_of_date"] == "2026-01-07"
    assert payload["method"] == "price_structure_heuristic_v1"
    assert bands["p10"] < bands["p25"] < bands["p50"] < bands["p75"] < bands["p90"]
    assert payload["target_price"] == bands["p50"]
    assert payload["drivers"][0]["name"] == "trend_return"
    assert payload["drivers"][1]["name"] == "channel_position"
    assert payload["drivers"][2]["name"] == "drawdown_from_high"
    assert "not a forecast guarantee" in payload["limitations"]


def test_write_target_explanation_creates_json_file(tmp_path):
    output_path = tmp_path / "target_explanation.json"

    written = write_target_explanation(
        sample_ohlcv(),
        output_path,
        symbol="AAPL",
        lookback=4,
        horizon_days=126,
    )

    assert written == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["symbol"] == "AAPL"
    assert payload["input"]["lookback_rows"] == 4
    assert payload["target_price"] == payload["price_bands"]["p50"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_explainable_target.py::test_build_explainable_target_returns_ordered_probability_bands tests/test_explainable_target.py::test_write_target_explanation_creates_json_file -v
```

Expected: FAIL with `ImportError` for `build_explainable_target` or `write_target_explanation`.

- [ ] **Step 3: Write minimal implementation**

Append this code to `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/explainable_target.py`:

```python

QUANTILE_Z = {
    "p10": -1.2816,
    "p25": -0.6745,
    "p50": 0.0,
    "p75": 0.6745,
    "p90": 1.2816,
}


def build_explainable_target(
    data: pd.DataFrame,
    *,
    symbol: str,
    lookback: int = 120,
    horizon_days: int = 126,
) -> dict[str, Any]:
    if horizon_days < 1:
        raise ValueError("horizon_days must be positive")

    features = compute_price_structure_features(data, lookback=lookback)
    expected_return = _expected_forward_return(features)
    expected_log_return = math.log1p(expected_return)
    distribution_width = _distribution_width(features, horizon_days=horizon_days)
    price_bands = {
        label: round(
            features.last_close * math.exp(expected_log_return + z_value * distribution_width),
            4,
        )
        for label, z_value in QUANTILE_Z.items()
    }
    drivers = _drivers(features)

    return {
        "symbol": symbol.strip().upper(),
        "as_of_date": features.as_of_date,
        "method": "price_structure_heuristic_v1",
        "horizon_days": int(horizon_days),
        "expected_log_return": round(expected_log_return, 6),
        "target_price": price_bands["p50"],
        "price_bands": price_bands,
        "features": asdict(features),
        "drivers": drivers,
        "input": {
            "lookback_requested": int(lookback),
            "lookback_rows": features.lookback_rows,
        },
        "limitations": LIMITATIONS_TEXT,
    }


def write_target_explanation(
    data: pd.DataFrame,
    output_path: str | Path,
    *,
    symbol: str,
    lookback: int = 120,
    horizon_days: int = 126,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_explainable_target(
        data,
        symbol=symbol,
        lookback=lookback,
        horizon_days=horizon_days,
    )
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def _expected_forward_return(features: PriceStructureFeatures) -> float:
    raw = (
        (0.55 * features.trend_return)
        + (0.10 * features.channel_position)
        - (0.30 * features.drawdown_from_high)
    )
    return _clip(raw, -0.35, 0.35)


def _distribution_width(features: PriceStructureFeatures, *, horizon_days: int) -> float:
    horizon_volatility = features.annualized_volatility * math.sqrt(horizon_days / 252.0)
    channel_width_component = features.channel_width_pct * 0.35
    return max(horizon_volatility, channel_width_component, 0.03)


def _drivers(features: PriceStructureFeatures) -> list[dict[str, float | str]]:
    trend_contribution = 0.55 * features.trend_return
    channel_contribution = 0.10 * features.channel_position
    drawdown_contribution = -0.30 * features.drawdown_from_high
    return [
        {
            "name": "trend_return",
            "value": round(features.trend_return, 6),
            "contribution": round(trend_contribution, 6),
            "interpretation": "Positive when the recent price window trends upward.",
        },
        {
            "name": "channel_position",
            "value": round(features.channel_position, 6),
            "contribution": round(channel_contribution, 6),
            "interpretation": "Positive when the close is above the channel midpoint.",
        },
        {
            "name": "drawdown_from_high",
            "value": round(features.drawdown_from_high, 6),
            "contribution": round(drawdown_contribution, 6),
            "interpretation": "Positive when the close is below the recent channel high.",
        },
    ]


def _clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_explainable_target.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/price_action_backtest/explainable_target.py tests/test_explainable_target.py
git commit -m "feat: build explainable target payloads"
```

## Task 3: `explain-target` CLI Command

**Files:**
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/scripts/price_action_backtest.py`
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_cli_setup.py`

- [ ] **Step 1: Write the failing test**

Append this test to `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_cli_setup.py`:

```python

def test_explain_target_cli_writes_target_json(tmp_path):
    output_path = tmp_path / "target_explanation.json"

    result = run_cli(
        "explain-target",
        "--symbol",
        "AAPL",
        "--data-path",
        str(SAMPLE_DATA),
        "--lookback",
        "20",
        "--horizon-days",
        "126",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "symbol": "AAPL",
        "output_path": str(output_path),
    }
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["symbol"] == "AAPL"
    assert saved["horizon_days"] == 126
    assert saved["target_price"] == saved["price_bands"]["p50"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_setup.py::test_explain_target_cli_writes_target_json -v
```

Expected: FAIL with CLI JSON error containing `invalid choice: 'explain-target'`.

- [ ] **Step 3: Write minimal implementation**

In `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/scripts/price_action_backtest.py`, insert this function after `command_webull_fetch_bars` and before `build_parser`:

```python

def command_explain_target(args):
    output_path = Path(args.output) if args.output else Path(args.output_root) / "target_explanation.json"
    try:
        import pandas as pd

        from price_action_backtest.explainable_target import write_target_explanation

        data = pd.read_csv(args.data_path)
        written = write_target_explanation(
            data,
            output_path,
            symbol=args.symbol,
            lookback=args.lookback,
            horizon_days=args.horizon_days,
        )
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, ValueError) as exc:
        emit_error(str(exc))
        return 1

    emit_json(
        {
            "ok": True,
            "symbol": args.symbol.strip().upper(),
            "output_path": str(written),
        }
    )
    return 0
```

In `build_parser()`, insert this parser block after the `webull-fetch-bars` parser block:

```python
    explain = subparsers.add_parser(
        "explain-target",
        help="Build an explainable target price JSON artifact from OHLCV CSV data.",
    )
    explain.add_argument("--symbol", required=True)
    explain.add_argument("--data-path", required=True)
    explain.add_argument("--lookback", type=int, default=120)
    explain.add_argument("--horizon-days", type=int, default=126)
    explain.add_argument("--output")
    explain.add_argument("--output-root", default="outputs")
    explain.set_defaults(func=command_explain_target)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_cli_setup.py::test_explain_target_cli_writes_target_json -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/price_action_backtest.py tests/test_cli_setup.py
git commit -m "feat: add explain target cli"
```

## Task 4: Target Report Renderer

**Files:**
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/target_reports.py`
- Create: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_target_reports.py`

- [ ] **Step 1: Write the failing test**

Create `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_target_reports.py` with:

```python
import json
from pathlib import Path

from price_action_backtest.target_reports import render_target_report


def sample_payload() -> dict:
    return {
        "symbol": "AAPL",
        "as_of_date": "2026-01-07",
        "method": "price_structure_heuristic_v1",
        "horizon_days": 126,
        "target_price": 120.5,
        "price_bands": {
            "p10": 100.0,
            "p25": 110.0,
            "p50": 120.5,
            "p75": 130.0,
            "p90": 140.0,
        },
        "features": {
            "last_close": 111.0,
            "channel_low": 102.0,
            "channel_high": 112.0,
            "channel_midpoint": 107.0,
            "channel_width_pct": 0.09009,
            "channel_position": 0.4,
            "trend_return": 0.067308,
            "annualized_volatility": 0.08,
            "drawdown_from_high": -0.008929,
        },
        "drivers": [
            {
                "name": "trend_return",
                "value": 0.067308,
                "contribution": 0.037019,
                "interpretation": "Positive when the recent price window trends upward.",
            },
            {
                "name": "channel_position",
                "value": 0.4,
                "contribution": 0.04,
                "interpretation": "Positive when the close is above the channel midpoint.",
            },
            {
                "name": "drawdown_from_high",
                "value": -0.008929,
                "contribution": 0.002679,
                "interpretation": "Positive when the close is below the recent channel high.",
            },
        ],
        "limitations": "This target price is a deterministic research estimate from historical OHLCV structure. It is not a forecast guarantee, investment advice, or trading instruction.",
    }


def test_render_target_report_writes_html(tmp_path):
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(sample_payload()), encoding="utf-8")

    report_path = render_target_report(payload_path, tmp_path / "target_report.html")

    assert report_path == tmp_path / "target_report.html"
    html = report_path.read_text(encoding="utf-8")
    assert "AAPL Explainable Target Price" in html
    assert "120.5000" in html
    assert "Probability Bands" in html
    assert "trend_return" in html
    assert "#121212" in html
    assert "#69F0AE" in html
    assert "not a forecast guarantee" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_target_reports.py::test_render_target_report_writes_html -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'price_action_backtest.target_reports'`.

- [ ] **Step 3: Write minimal implementation**

Create `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/src/price_action_backtest/target_reports.py` with:

```python
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

THEME = {
    "dark": "#121212",
    "surface": "#1D1D1D",
    "surface_2": "#212121",
    "surface_3": "#242424",
    "primary": "#69F0AE",
    "secondary": "#03DAC6",
    "profit": "#00E676",
    "loss": "#FF5252",
    "text_high": "rgba(255, 255, 255, 0.87)",
    "text_medium": "rgba(255, 255, 255, 0.60)",
    "grid": "rgba(255, 255, 255, 0.08)",
}


def render_target_report(payload_path: str | Path, output_path: str | Path) -> Path:
    payload_file = Path(payload_path)
    output_file = Path(output_path)
    payload = json.loads(payload_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("target explanation JSON must contain an object")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(_render_document(payload), encoding="utf-8")
    return output_file


def _render_document(payload: dict[str, Any]) -> str:
    symbol = escape(str(payload["symbol"]))
    title = f"{symbol} Explainable Target Price"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      margin: 0;
      background: {THEME["dark"]};
      color: {THEME["text_high"]};
      font-family: Inter, "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    h1 {{
      margin: 0 0 8px;
      color: {THEME["primary"]};
      font-size: 32px;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    .subtitle {{
      color: {THEME["text_medium"]};
      font-size: 14px;
      margin: 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}
    .panel {{
      background: {THEME["surface"]};
      border: 1px solid {THEME["grid"]};
      border-radius: 8px;
      padding: 16px;
      margin-top: 16px;
    }}
    .metric-label {{
      color: {THEME["text_medium"]};
      font-size: 12px;
      text-transform: uppercase;
    }}
    .metric-value {{
      color: {THEME["primary"]};
      font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
      font-size: 28px;
      margin-top: 4px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th {{
      background: {THEME["surface_3"]};
      color: {THEME["text_medium"]};
      text-align: left;
    }}
    th, td {{
      border-bottom: 1px solid {THEME["grid"]};
      padding: 10px 12px;
    }}
    .number {{
      text-align: right;
      font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }}
    .limitations {{
      border-left: 3px solid {THEME["primary"]};
      background: {THEME["surface_2"]};
      color: {THEME["text_medium"]};
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{title}</h1>
      <p class="subtitle">Method: {escape(str(payload["method"]))} | As of {escape(str(payload["as_of_date"]))} | Horizon: {int(payload["horizon_days"])} days</p>
    </header>
    <section class="grid">
      {_metric_card("Last Close", payload["features"]["last_close"])}
      {_metric_card("Target Price", payload["target_price"])}
      {_metric_card("Channel Low", payload["features"]["channel_low"])}
      {_metric_card("Channel High", payload["features"]["channel_high"])}
    </section>
    <section class="panel">
      <h2>Probability Bands</h2>
      {_bands_table(payload["price_bands"])}
    </section>
    <section class="panel">
      <h2>Drivers</h2>
      {_drivers_table(payload["drivers"])}
    </section>
    <section class="panel">
      <h2>Features</h2>
      {_features_table(payload["features"])}
    </section>
    <section class="panel limitations">
      <h2>Limitations</h2>
      <p>{escape(str(payload["limitations"]))}</p>
    </section>
  </main>
</body>
</html>
"""


def _metric_card(label: str, value: Any) -> str:
    return (
        '<div class="panel">'
        f'<div class="metric-label">{escape(label)}</div>'
        f'<div class="metric-value">{_format_number(value)}</div>'
        "</div>"
    )


def _bands_table(bands: dict[str, Any]) -> str:
    rows = [
        f"<tr><td>{escape(label.upper())}</td><td class=\"number\">{_format_number(value)}</td></tr>"
        for label, value in bands.items()
    ]
    return "<table><thead><tr><th>Band</th><th class=\"number\">Price</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _drivers_table(drivers: list[dict[str, Any]]) -> str:
    rows = []
    for driver in drivers:
        rows.append(
            "<tr>"
            f"<td>{escape(str(driver['name']))}</td>"
            f"<td class=\"number\">{_format_number(driver['value'])}</td>"
            f"<td class=\"number\">{_format_number(driver['contribution'])}</td>"
            f"<td>{escape(str(driver['interpretation']))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Driver</th><th class=\"number\">Value</th><th class=\"number\">Contribution</th><th>Interpretation</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _features_table(features: dict[str, Any]) -> str:
    rows = [
        f"<tr><td>{escape(str(key))}</td><td class=\"number\">{_format_number(value)}</td></tr>"
        for key, value in features.items()
    ]
    return "<table><thead><tr><th>Feature</th><th class=\"number\">Value</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _format_number(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.4f}"
    return escape(str(value))
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_target_reports.py::test_render_target_report_writes_html -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/price_action_backtest/target_reports.py tests/test_target_reports.py
git commit -m "feat: render explainable target reports"
```

## Task 5: `render-target-report` CLI Command

**Files:**
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/scripts/price_action_backtest.py`
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_target_reports.py`

- [ ] **Step 1: Write the failing test**

Append this to `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/tests/test_target_reports.py`:

```python
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "price_action_backtest.py"


def run_cli(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_render_target_report_cli_writes_html(tmp_path):
    payload_path = tmp_path / "target_explanation.json"
    output_path = tmp_path / "target_report.html"
    payload_path.write_text(json.dumps(sample_payload()), encoding="utf-8")

    result = run_cli(
        "render-target-report",
        "--payload-path",
        str(payload_path),
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "payload_path": str(payload_path),
        "report_path": str(output_path),
    }
    assert output_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/python -m pytest tests/test_target_reports.py::test_render_target_report_cli_writes_html -v
```

Expected: FAIL with CLI JSON error containing `invalid choice: 'render-target-report'`.

- [ ] **Step 3: Write minimal implementation**

In `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/scripts/price_action_backtest.py`, insert this function after `command_explain_target` and before `build_parser`:

```python

def command_render_target_report(args):
    output_path = Path(args.output) if args.output else Path(args.output_root) / "target_report.html"
    try:
        from price_action_backtest.target_reports import render_target_report

        report_path = render_target_report(args.payload_path, output_path)
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        emit_error(str(exc))
        return 1

    emit_json(
        {
            "ok": True,
            "payload_path": args.payload_path,
            "report_path": str(report_path),
        }
    )
    return 0
```

In `build_parser()`, insert this parser block after the `explain-target` parser block:

```python
    target_report = subparsers.add_parser(
        "render-target-report",
        help="Render a target_explanation.json artifact as a standalone HTML report.",
    )
    target_report.add_argument("--payload-path", required=True)
    target_report.add_argument("--output")
    target_report.add_argument("--output-root", default="outputs")
    target_report.set_defaults(func=command_render_target_report)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
.venv/bin/python -m pytest tests/test_target_reports.py -v
```

Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/price_action_backtest.py tests/test_target_reports.py
git commit -m "feat: add target report cli"
```

## Task 6: README Workflow Documentation

**Files:**
- Modify: `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/README.md`

- [ ] **Step 1: Add the documentation section**

Insert this section after the existing `Webull Historical Bars` section:

````markdown
## Webull Explainable Target Price MVP

After fetching read-only Webull historical bars, build a deterministic target
price explanation artifact from the OHLCV CSV:

```bash
.venv/bin/python scripts/price_action_backtest.py explain-target \
  --symbol AAPL \
  --data-path data/private/webull-aapl-d.csv \
  --lookback 120 \
  --horizon-days 126 \
  --output outputs/aapl-target/target_explanation.json
```

Render the standalone HTML report:

```bash
.venv/bin/python scripts/price_action_backtest.py render-target-report \
  --payload-path outputs/aapl-target/target_explanation.json \
  --output outputs/aapl-target/target_report.html
```

The model is intentionally transparent and deterministic:

- It uses only historical OHLCV price structure.
- It computes a recent price channel, trend return, volatility, and drawdown
  from the selected lookback window.
- It creates heuristic P10/P25/P50/P75/P90 price bands for the selected horizon.
- It writes the driver contributions used in the target estimate.

This is a research artifact, not a price prediction guarantee, investment
advice, or trading instruction. It does not use Webull trading/order APIs.
````

- [ ] **Step 2: Verify documentation contains runnable commands**

Run:

```bash
rg -n "explain-target|render-target-report|target_explanation.json|target_report.html" README.md
```

Expected: output includes all four terms.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add explainable target workflow"
```

## Task 7: Full Local Validation

**Files:**
- No source edits expected.

- [ ] **Step 1: Run focused tests**

Run:

```bash
.venv/bin/python -m pytest tests/test_explainable_target.py tests/test_target_reports.py tests/test_cli_setup.py -v
```

Expected: all selected tests PASS.

- [ ] **Step 2: Run full test suite**

Run:

```bash
.venv/bin/python -m pytest -q
```

Expected: full test suite PASS.

- [ ] **Step 3: Run lint**

Run:

```bash
.venv/bin/python -m ruff check .
```

Expected: `All checks passed!`

- [ ] **Step 4: Run local sample end-to-end without Webull credentials**

Run:

```bash
rm -rf outputs/sample-target
mkdir -p outputs/sample-target
.venv/bin/python scripts/price_action_backtest.py explain-target \
  --symbol AAPL \
  --data-path templates/sample-ohlcv.csv \
  --lookback 20 \
  --horizon-days 126 \
  --output outputs/sample-target/target_explanation.json
.venv/bin/python scripts/price_action_backtest.py render-target-report \
  --payload-path outputs/sample-target/target_explanation.json \
  --output outputs/sample-target/target_report.html
test -f outputs/sample-target/target_explanation.json
test -f outputs/sample-target/target_report.html
```

Expected: both `test -f` checks exit 0.

- [ ] **Step 5: Run optional live Webull smoke only after credentials exist**

Run this only when `/Users/nuthdanai/Desktop/02_Quant_Investment/price-action-backtest-plugin/.env` contains `WEBULL_APP_KEY` and `WEBULL_APP_SECRET`:

```bash
.venv/bin/python scripts/price_action_backtest.py webull-fetch-bars \
  --symbol AAPL \
  --timespan D \
  --count 180 \
  --output data/private/webull-aapl-d.csv
.venv/bin/python scripts/price_action_backtest.py explain-target \
  --symbol AAPL \
  --data-path data/private/webull-aapl-d.csv \
  --lookback 120 \
  --horizon-days 126 \
  --output outputs/aapl-webull-target/target_explanation.json
.venv/bin/python scripts/price_action_backtest.py render-target-report \
  --payload-path outputs/aapl-webull-target/target_explanation.json \
  --output outputs/aapl-webull-target/target_report.html
```

Expected: Webull fetch emits JSON with `"ok": true`, and both target artifacts are created.

- [ ] **Step 6: Commit validation cleanup if generated files are gitignored**

Run:

```bash
git status --short
```

Expected: generated files under `outputs/` and `data/private/` do not appear because they are gitignored. If only intended source/docs/test files remain tracked, commit them:

```bash
git add src/price_action_backtest/explainable_target.py src/price_action_backtest/target_reports.py scripts/price_action_backtest.py tests/test_explainable_target.py tests/test_target_reports.py tests/test_cli_setup.py README.md
git commit -m "feat: add webull explainable target workflow"
```

## Self-Review

- Spec coverage: The plan covers Webull read-only market data usage through existing `webull-fetch-bars`, explainable target price calculation, probability bands, driver explanation, JSON output, HTML report output, documentation, and local/live validation.
- Scope boundaries: The plan excludes LLM transcript narrative extraction, OpenBB integration, MCP tools, options fair value, and trading APIs because they are independent subsystems.
- Placeholder scan: No placeholder implementation steps are present. Each code-changing step includes concrete code and each verification step includes exact commands and expected results.
- Type consistency: `compute_price_structure_features`, `build_explainable_target`, `write_target_explanation`, `render_target_report`, `command_explain_target`, and `command_render_target_report` are introduced before use. Payload keys are consistent across tests, CLI, and HTML renderer.
