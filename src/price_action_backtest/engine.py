from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestResult:
    equity: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float | int]


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0

    running_peak = equity.cummax()
    drawdown = (equity / running_peak) - 1
    return float(drawdown.min())


def _validate_frame(frame: pd.DataFrame) -> None:
    required_columns = ("date", "close")
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")


def _validate_cost(name: str, value: float) -> None:
    try:
        cost = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be finite and non-negative") from exc
    if not isfinite(cost) or cost < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def run_backtest(
    frame: pd.DataFrame,
    signal: pd.Series,
    fee_bps: float,
    slippage_bps: float,
) -> BacktestResult:
    _validate_frame(frame)
    if len(signal) != len(frame):
        raise ValueError(f"signal length must match frame length: {len(signal)} != {len(frame)}")
    _validate_cost("fee_bps", fee_bps)
    _validate_cost("slippage_bps", slippage_bps)

    data = frame.copy().reset_index(drop=True)
    close = pd.to_numeric(data["close"], errors="raise")

    asset_return = close.pct_change().fillna(0)

    clean_signal = signal.astype(int).clip(lower=0, upper=1).reset_index(drop=True)
    position = clean_signal.shift(1).fillna(0).astype(int)
    turnover = position.diff().abs().fillna(position.abs())
    cost_rate = (float(fee_bps) + float(slippage_bps)) / 10_000
    cost = turnover * cost_rate
    strategy_return = (position * asset_return) - cost
    strategy_equity = (1 + strategy_return).cumprod()
    buy_hold_equity = (1 + asset_return).cumprod()
    drawdown = (strategy_equity / strategy_equity.cummax()) - 1

    if "date" in data.columns:
        equity = data.loc[:, ["date", "close"]].copy()
    else:
        equity = data[["close"]].copy()
    equity["asset_return"] = asset_return
    equity["signal"] = clean_signal
    equity["position"] = position
    equity["turnover"] = turnover
    equity["cost"] = cost
    equity["strategy_return"] = strategy_return
    equity["strategy_equity"] = strategy_equity
    equity["buy_hold_equity"] = buy_hold_equity
    equity["drawdown"] = drawdown

    trade_mask = turnover > 0
    trade_columns = ["date", "close"] if "date" in equity.columns else ["close"]
    trades = equity.loc[trade_mask, trade_columns].copy()
    position_change = position.diff().fillna(position)
    trades["position_change"] = position_change.loc[trade_mask]
    trades["turnover"] = turnover.loc[trade_mask]
    trades["cost"] = cost.loc[trade_mask]
    trades = trades.reset_index(drop=True)

    total_return = float(strategy_equity.iloc[-1] - 1) if len(strategy_equity) else 0.0
    buy_hold_return = float(buy_hold_equity.iloc[-1] - 1) if len(buy_hold_equity) else 0.0
    periods = len(strategy_return)
    annualized_return = (
        float((1 + total_return) ** (TRADING_DAYS_PER_YEAR / periods) - 1)
        if periods and (1 + total_return) > 0
        else 0.0
    )
    annualized_volatility = float(strategy_return.std(ddof=0) * (TRADING_DAYS_PER_YEAR**0.5))
    periodic_volatility = float(strategy_return.std(ddof=0))
    sharpe = (
        float(strategy_return.mean() / periodic_volatility * (TRADING_DAYS_PER_YEAR**0.5))
        if periodic_volatility
        else 0.0
    )

    metrics: dict[str, float | int] = {
        "total_return": total_return,
        "buy_hold_return": buy_hold_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe": float(sharpe),
        "max_drawdown": _max_drawdown(strategy_equity),
        "trade_count": int(trade_mask.sum()),
        "total_cost": float(cost.sum()),
    }

    return BacktestResult(equity=equity, trades=trades, metrics=metrics)
