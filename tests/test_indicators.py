import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from price_action_backtest.indicators import add_indicators


def make_frame(closes, highs=None, lows=None):
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(closes), freq="D"),
            "open": [close - 1 for close in closes],
            "high": highs or [close + 1 for close in closes],
            "low": lows or [close - 1 for close in closes],
            "close": closes,
            "volume": list(range(1_000, 1_000 + len(closes))),
        }
    )


def test_add_indicators_appends_expected_columns():
    frame = make_frame(list(range(100, 140)))

    data = add_indicators(frame, fast_window=5, slow_window=20)

    expected_columns = {
        "sma_fast",
        "sma_slow",
        "ema_fast",
        "ema_slow",
        "rsi_14",
        "macd",
        "macd_signal",
        "bb_mid",
        "bb_upper",
        "bb_lower",
        "atr_14",
    }
    assert expected_columns.issubset(data.columns)
    assert data["sma_fast"].iloc[-1] == 137.0
    assert data["sma_slow"].iloc[-1] == 129.5


def test_add_indicators_does_not_mutate_input_frame():
    frame = make_frame(list(range(100, 120)))
    original = frame.copy(deep=True)

    data = add_indicators(frame, fast_window=5, slow_window=20)

    assert_frame_equal(frame, original)
    assert "sma_fast" in data.columns
    assert "sma_fast" not in frame.columns


def test_rsi_warm_up_values_remain_nan():
    data = add_indicators(make_frame(list(range(100, 120))), fast_window=5, slow_window=20)

    assert data["rsi_14"].iloc[:14].isna().all()


def test_rsi_rising_market_is_100_after_warm_up():
    data = add_indicators(make_frame(list(range(100, 120))), fast_window=5, slow_window=20)

    assert data["rsi_14"].iloc[14:].eq(100).all()


def test_rsi_flat_market_is_50_after_warm_up():
    data = add_indicators(make_frame([100] * 20), fast_window=5, slow_window=20)

    assert data["rsi_14"].iloc[14:].eq(50).all()


def test_rsi_declining_market_is_0_after_warm_up():
    data = add_indicators(make_frame(list(range(120, 100, -1))), fast_window=5, slow_window=20)

    assert data["rsi_14"].iloc[14:].eq(0).all()


def test_atr_uses_true_range_gap_math():
    closes = [10] * 14 + [19]
    highs = [11] * 14 + [20]
    lows = [9] * 14 + [19]

    data = add_indicators(make_frame(closes, highs=highs, lows=lows), fast_window=5, slow_window=20)

    assert data["atr_14"].iloc[13] == 2.0
    assert data["atr_14"].iloc[14] == pytest.approx(18 / 7)


def test_bollinger_bands_use_population_std():
    data = add_indicators(make_frame([10, 12, 14]), fast_window=2, slow_window=3)
    expected_std = (8 / 3) ** 0.5

    assert data["bb_mid"].iloc[-1] == 12.0
    assert data["bb_upper"].iloc[-1] == pytest.approx(12 + (2 * expected_std))
    assert data["bb_lower"].iloc[-1] == pytest.approx(12 - (2 * expected_std))
