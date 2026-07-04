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


def test_rsi_reversion_nan_warmup_starts_flat_and_keeps_prior_position():
    frame = pd.DataFrame({"rsi_14": [None, float("nan"), 25, None, 35, 60, None]})

    signal = build_signal(
        frame,
        SignalSpec(strategy="rsi_reversion", rsi_entry=30.0, rsi_exit=55.0),
    )

    assert signal.tolist() == [0, 0, 1, 1, 1, 0, 0]


@pytest.mark.parametrize(
    "spec, message",
    [
        (SignalSpec(strategy="rsi_reversion", rsi_entry=55.0, rsi_exit=55.0), "rsi_entry"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry=60.0, rsi_exit=55.0), "rsi_entry"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry=-1.0, rsi_exit=55.0), "rsi_entry"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry=30.0, rsi_exit=101.0), "rsi_exit"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry=float("nan"), rsi_exit=55.0), "rsi_entry"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry=30.0, rsi_exit=float("inf")), "rsi_exit"),
        (SignalSpec(strategy="rsi_reversion", rsi_entry="30", rsi_exit=55.0), "rsi_entry"),
    ],
)
def test_rsi_reversion_invalid_params_raise_value_error(spec, message):
    frame = pd.DataFrame({"rsi_14": [25, 60]})

    with pytest.raises(ValueError, match=message):
        build_signal(frame, spec)


def test_sma_cross_missing_columns_raise_clear_value_error():
    frame = pd.DataFrame({"sma_fast": [1, 2, 3]})

    with pytest.raises(ValueError, match="missing columns.*sma_cross.*sma_slow"):
        build_signal(frame, SignalSpec(strategy="sma_cross"))


def test_rsi_reversion_missing_columns_raise_clear_value_error():
    frame = pd.DataFrame({"close": [1, 2, 3]})

    with pytest.raises(ValueError, match="missing columns.*rsi_reversion.*rsi_14"):
        build_signal(frame, SignalSpec(strategy="rsi_reversion"))


def test_ema_cross_returns_binary_signal():
    frame = pd.DataFrame(
        {
            "ema_fast": [3, 2, 1],
            "ema_slow": [2, 2, 2],
        }
    )

    signal = build_signal(frame, SignalSpec(strategy="ema_cross"))

    assert signal.tolist() == [1, 0, 0]


def test_macd_trend_returns_binary_signal():
    frame = pd.DataFrame(
        {
            "macd": [-1, 0, 2],
            "macd_signal": [0, 0, 1],
        }
    )

    signal = build_signal(frame, SignalSpec(strategy="macd_trend"))

    assert signal.tolist() == [0, 0, 1]


def test_unknown_strategy_raises_value_error():
    with pytest.raises(ValueError, match="unsupported strategy"):
        build_signal(pd.DataFrame(), SignalSpec(strategy="not_real"))
