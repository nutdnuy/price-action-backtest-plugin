from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from price_action_backtest.data import normalize_ohlcv_frame

LIMITATIONS_TEXT = (
    "This target price is a deterministic research estimate from historical OHLCV "
    "structure. It is not a forecast guarantee, investment advice, or trading instruction."
)
TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class PriceStructureFeatures:
    as_of_date: str
    last_close: float
    lookback_rows: int
    channel_low: float
    channel_high: float
    channel_midpoint: float
    channel_width_pct: float
    channel_position: float
    trend_return: float
    annualized_volatility: float
    drawdown_from_high: float


def compute_price_structure_features(
    data: pd.DataFrame, lookback: int = 120
) -> PriceStructureFeatures:
    """Compute recent OHLCV structure; channel_position is midpoint-centered, not 0-to-1."""
    if lookback < 2:
        raise ValueError("lookback must be at least 2")

    clean = normalize_ohlcv_frame(data.copy(), min_rows=2)
    window = clean.tail(min(lookback, len(clean))).copy()
    first_close = float(window["close"].iloc[0])
    last_close = float(window["close"].iloc[-1])
    channel_low = float(window["low"].min())
    channel_high = float(window["high"].max())
    channel_midpoint = (channel_low + channel_high) / 2.0
    channel_width = channel_high - channel_low
    channel_width_pct = channel_width / last_close if last_close else 0.0
    channel_position = ((last_close - channel_midpoint) / channel_width) if channel_width else 0.0
    trend_return = (last_close / first_close) - 1.0
    daily_returns = window["close"].pct_change().dropna()
    annualized_volatility = (
        float(daily_returns.std(ddof=0) * math.sqrt(TRADING_DAYS_PER_YEAR))
        if not daily_returns.empty
        else 0.0
    )
    drawdown_from_high = (last_close / channel_high) - 1.0 if channel_high else 0.0

    return PriceStructureFeatures(
        as_of_date=pd.Timestamp(window["date"].iloc[-1]).strftime("%Y-%m-%d"),
        last_close=last_close,
        lookback_rows=int(len(window)),
        channel_low=channel_low,
        channel_high=channel_high,
        channel_midpoint=channel_midpoint,
        channel_width_pct=channel_width_pct,
        channel_position=channel_position,
        trend_return=trend_return,
        annualized_volatility=annualized_volatility,
        drawdown_from_high=drawdown_from_high,
    )
