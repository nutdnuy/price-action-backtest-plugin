import json

import pandas as pd
import pytest

from price_action_backtest.explainable_target import write_target_explanation
from price_action_backtest.target_reports import render_target_report


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
        "limitations": (
            "This target price is a deterministic research estimate from historical OHLCV "
            "structure. It is not a forecast guarantee, investment advice, or trading "
            "instruction."
        ),
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


def test_render_target_report_handles_real_producer_payload(tmp_path):
    payload_path = tmp_path / "target_explanation.json"
    write_target_explanation(
        sample_ohlcv(),
        payload_path,
        symbol="AAPL",
        lookback=4,
        horizon_days=126,
    )

    report_path = render_target_report(payload_path, tmp_path / "target_report.html")

    html = report_path.read_text(encoding="utf-8")
    assert "Positive when the recent price window trends upward." in html
    assert "Positive when the close is above the channel midpoint." in html
    assert "Positive when the close is below the recent channel high." in html
    assert "<td></td>" not in html


def test_render_target_report_rejects_non_object_json(tmp_path):
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        render_target_report(payload_path, tmp_path / "target_report.html")

    assert str(exc_info.value) == "target explanation JSON must contain an object"


def test_render_target_report_rejects_missing_required_field(tmp_path):
    payload = sample_payload()
    payload.pop("target_price")
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing required field: target_price"):
        render_target_report(payload_path, tmp_path / "target_report.html")


def test_render_target_report_rejects_invalid_price_bands_type(tmp_path):
    payload = sample_payload()
    payload["price_bands"] = []
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="field must be an object: price_bands"):
        render_target_report(payload_path, tmp_path / "target_report.html")


def test_render_target_report_rejects_invalid_drivers_type(tmp_path):
    payload = sample_payload()
    payload["drivers"] = {}
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="field must be a list: drivers"):
        render_target_report(payload_path, tmp_path / "target_report.html")


def test_render_target_report_escapes_string_content(tmp_path):
    payload = sample_payload()
    payload["symbol"] = "<script>alert(1)</script>"
    payload["drivers"][0]["name"] = "<script>alert(1)</script>"
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")

    report_path = render_target_report(payload_path, tmp_path / "target_report.html")

    html = report_path.read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in html
    assert "<SCRIPT>ALERT(1)</SCRIPT>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "&lt;SCRIPT&gt;ALERT(1)&lt;/SCRIPT&gt;" in html


def test_render_target_report_creates_nested_output_path(tmp_path):
    payload_path = tmp_path / "target_explanation.json"
    payload_path.write_text(json.dumps(sample_payload()), encoding="utf-8")
    output_path = tmp_path / "nested" / "reports" / "target_report.html"

    report_path = render_target_report(payload_path, output_path)

    assert report_path == output_path
    assert output_path.exists()
