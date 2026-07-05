import json

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
