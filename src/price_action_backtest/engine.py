from __future__ import annotations

from dataclasses import dataclass

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


def run_backtest(
    frame: pd.DataFrame,
    signal: pd.Series,
    fee_bps: float,
    slippage_bps: float,
) -> BacktestResult:
    data = frame.copy().reset_index(drop=True)
    close = pd.to_numeric(data["close"], errors="raise")

    clean_signal = pd.Series(signal, index=data.index, dtype="float64").fillna(0).clip(0, 1)
    position = clean_signal.shift(1).fillna(0)

    asset_return = close.pct_change().fillna(0)
    position_change = clean_signal.diff().fillna(clean_signal)
    turnover = position_change.abs()
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
    equity["signal"] = clean_signal.astype(int)
    equity["position"] = position.astype(int)
    equity["turnover"] = turnover
    equity["cost"] = cost
    equity["strategy_return"] = strategy_return
    equity["strategy_equity"] = strategy_equity
    equity["buy_hold_equity"] = buy_hold_equity
    equity["drawdown"] = drawdown

    trade_mask = turnover > 0
    trade_columns = ["date", "close"] if "date" in equity.columns else ["close"]
    trades = equity.loc[trade_mask, trade_columns].copy()
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
    sharpe = annualized_return / annualized_volatility if annualized_volatility else 0.0

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
