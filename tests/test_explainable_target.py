import json
import math

import pandas as pd
import pytest

from price_action_backtest.explainable_target import (
    build_explainable_target,
    compute_price_structure_features,
    write_target_explanation,
)


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

    expected_returns = pd.Series([104.0, 106.0, 109.0, 111.0]).pct_change().dropna()
    assert features.annualized_volatility == pytest.approx(
        expected_returns.std(ddof=0) * math.sqrt(252)
    )


def test_compute_price_structure_features_rejects_too_short_lookback():
    with pytest.raises(ValueError, match="lookback must be at least 2"):
        compute_price_structure_features(sample_ohlcv(), lookback=1)


def test_compute_price_structure_features_does_not_mutate_input_columns():
    data = sample_ohlcv().rename(columns={"date": " Date ", "open": " Open "})
    original_columns = list(data.columns)

    compute_price_structure_features(data, lookback=4)

    assert list(data.columns) == original_columns


def test_build_explainable_target_returns_ordered_probability_bands():
    payload = build_explainable_target(
        sample_ohlcv(), symbol="AAPL", lookback=4, horizon_days=126
    )

    assert payload["symbol"] == "AAPL"
    assert payload["as_of_date"] == "2026-01-07"
    assert payload["method"] == "price_structure_heuristic_v1"
    price_bands = payload["price_bands"]
    assert (
        price_bands["p10"]
        < price_bands["p25"]
        < price_bands["p50"]
        < price_bands["p75"]
        < price_bands["p90"]
    )
    assert payload["target_price"] == price_bands["p50"]
    assert [driver["name"] for driver in payload["drivers"]] == [
        "trend_return",
        "channel_position",
        "drawdown_from_high",
    ]
    assert "not a forecast guarantee" in payload["limitations"]


def test_write_target_explanation_creates_json_file(tmp_path):
    output_path = tmp_path / "target.json"

    returned_path = write_target_explanation(
        sample_ohlcv(), output_path, symbol="AAPL", lookback=4, horizon_days=126
    )

    assert returned_path == output_path
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["symbol"] == "AAPL"
    assert payload["input"]["lookback_rows"] == 4
    assert payload["target_price"] == payload["price_bands"]["p50"]
