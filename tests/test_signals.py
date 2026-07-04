import pandas as pd
import pytest

from price_action_backtest.signals import SignalSpec, build_signal


def test_sma_cross_returns_binary_signal():
    frame = pd.DataFrame(
        {
            "sma_fast": [1, 2, 3],
            "sma_slow": [2, 2, 2],
        }
    )

    signal = build_signal(frame, SignalSpec(strategy="sma_cross"))

    assert signal.tolist() == [0, 0, 1]


def test_rsi_reversion_enters_below_entry_and_exits_above_exit():
    frame = pd.DataFrame({"rsi_14": [50, 25, 35, 60, 45]})

    signal = build_signal(
        frame,
        SignalSpec(strategy="rsi_reversion", rsi_entry=30.0, rsi_exit=55.0),
    )

    assert signal.tolist() == [0, 1, 1, 0, 0]


def test_unknown_strategy_raises_value_error():
    with pytest.raises(ValueError, match="unsupported strategy"):
        build_signal(pd.DataFrame(), SignalSpec(strategy="not_real"))
