import math

import pandas as pd
import pytest

from price_action_backtest.engine import run_backtest


def make_frame(closes):
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=len(closes), freq="D"),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
        }
    )


def test_one_bar_shift_avoids_same_bar_lookahead():
    frame = make_frame([100, 110, 121, 108.9])
    signal = pd.Series([0, 1, 1, 0])

    result = run_backtest(frame, signal, fee_bps=0, slippage_bps=0)

    assert result.equity["strategy_return"].tolist() == pytest.approx([0, 0, 0.1, -0.1])
    assert result.metrics["total_return"] == pytest.approx(-0.01)


def test_costs_charged_on_position_changes():
    frame = make_frame([100, 100, 100, 100])
    signal = pd.Series([0, 1, 0, 0])

    result = run_backtest(frame, signal, fee_bps=10, slippage_bps=5)

    assert result.metrics["total_cost"] == pytest.approx(0.003)
    assert result.metrics["trade_count"] == 2


def test_signal_is_coerced_to_clipped_integer_values():
    frame = make_frame([100, 100, 100, 100])
    signal = pd.Series([0.2, 1.9, 2.0, -1.0])

    result = run_backtest(frame, signal, fee_bps=0, slippage_bps=0)

    assert result.equity["signal"].tolist() == [0, 1, 1, 0]


def test_turnover_and_trades_occur_on_shifted_position_bar():
    frame = make_frame([100, 100, 100])
    signal = pd.Series([0, 1, 0])

    result = run_backtest(frame, signal, fee_bps=0, slippage_bps=0)

    assert result.equity["position"].tolist() == [0, 0, 1]
    assert result.equity["turnover"].tolist() == [0, 0, 1]
    assert result.trades["date"].tolist() == [pd.Timestamp("2024-01-03")]


@pytest.mark.parametrize(
    ("columns_to_drop", "message"),
    [
        (["date"], "missing columns.*date"),
        (["close"], "missing columns.*close"),
        (["date", "close"], "missing columns.*date.*close"),
    ],
)
def test_missing_required_columns_raise_value_error(columns_to_drop, message):
    frame = make_frame([100, 101]).drop(columns=columns_to_drop)

    with pytest.raises(ValueError, match=message):
        run_backtest(frame, pd.Series([0, 1]), fee_bps=0, slippage_bps=0)


def test_signal_length_mismatch_raises_value_error():
    frame = make_frame([100, 101, 102])

    with pytest.raises(ValueError, match="signal length"):
        run_backtest(frame, pd.Series([0, 1]), fee_bps=0, slippage_bps=0)


@pytest.mark.parametrize(
    ("fee_bps", "slippage_bps", "message"),
    [
        (-1, 0, "fee_bps"),
        (float("nan"), 0, "fee_bps"),
        (float("inf"), 0, "fee_bps"),
        (0, -1, "slippage_bps"),
        (0, float("nan"), "slippage_bps"),
        (0, float("inf"), "slippage_bps"),
    ],
)
def test_invalid_cost_inputs_raise_value_error(fee_bps, slippage_bps, message):
    frame = make_frame([100, 101])

    with pytest.raises(ValueError, match=message):
        run_backtest(frame, pd.Series([0, 1]), fee_bps=fee_bps, slippage_bps=slippage_bps)


def test_sharpe_uses_standard_periodic_mean_return():
    frame = make_frame([100, 110, 121])
    signal = pd.Series([1, 1, 1])

    result = run_backtest(frame, signal, fee_bps=0, slippage_bps=0)

    strategy_return = pd.Series([0.0, 0.1, 0.1])
    expected_sharpe = strategy_return.mean() / strategy_return.std(ddof=0) * math.sqrt(252)

    assert result.metrics["sharpe"] == pytest.approx(expected_sharpe)
    for value in result.metrics.values():
        if isinstance(value, float):
            assert math.isfinite(value)
