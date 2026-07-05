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
