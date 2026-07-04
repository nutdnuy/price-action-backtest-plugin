import pandas as pd

from price_action_backtest.indicators import add_indicators


def test_add_indicators_appends_expected_columns():
    closes = list(range(100, 140))
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=40, freq="D"),
            "open": [close - 1 for close in closes],
            "high": [close + 1 for close in closes],
            "low": [close - 2 for close in closes],
            "close": closes,
            "volume": list(range(1_000, 1_040)),
        }
    )

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
