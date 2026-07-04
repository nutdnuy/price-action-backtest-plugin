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
    frame = make_frame([100, 100, 100])
    signal = pd.Series([0, 1, 0])

    result = run_backtest(frame, signal, fee_bps=10, slippage_bps=5)

    assert result.metrics["total_cost"] == pytest.approx(0.003)
    assert result.metrics["trade_count"] == 2
