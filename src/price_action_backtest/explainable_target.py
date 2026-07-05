from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from price_action_backtest.data import normalize_ohlcv_frame

LIMITATIONS_TEXT = (
    "This target price is a deterministic research estimate from historical OHLCV "
    "structure. It is not a forecast guarantee, investment advice, or trading instruction."
)
TRADING_DAYS_PER_YEAR = 252
QUANTILE_Z = {"p10": -1.2816, "p25": -0.6745, "p50": 0.0, "p75": 0.6745, "p90": 1.2816}


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


def build_explainable_target(
    data: pd.DataFrame, *, symbol: str, lookback: int = 120, horizon_days: int = 126
) -> dict[str, Any]:
    if horizon_days < 1:
        raise ValueError("horizon_days must be positive")

    features = compute_price_structure_features(data, lookback=lookback)
    expected_return = _expected_forward_return(features)
    width = _distribution_width(features, horizon_days=horizon_days)
    price_bands = {
        quantile: features.last_close * (1.0 + expected_return + (z_score * width))
        for quantile, z_score in QUANTILE_Z.items()
    }

    return {
        "symbol": symbol.strip().upper(),
        "as_of_date": features.as_of_date,
        "method": "price_structure_heuristic_v1",
        "horizon_days": int(horizon_days),
        "target_price": price_bands["p50"],
        "price_bands": price_bands,
        "drivers": _drivers(features),
        "features": asdict(features),
        "input": {
            "lookback_requested": int(lookback),
            "lookback_rows": features.lookback_rows,
        },
        "limitations": LIMITATIONS_TEXT,
    }


def write_target_explanation(
    data: pd.DataFrame,
    output_path: str | Path,
    *,
    symbol: str,
    lookback: int = 120,
    horizon_days: int = 126,
) -> Path:
    payload = build_explainable_target(
        data, symbol=symbol, lookback=lookback, horizon_days=horizon_days
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _expected_forward_return(features: PriceStructureFeatures) -> float:
    raw = (
        (0.55 * features.trend_return)
        + (0.10 * features.channel_position)
        - (0.30 * features.drawdown_from_high)
    )
    return _clip(raw, -0.35, 0.35)


def _distribution_width(features: PriceStructureFeatures, *, horizon_days: int) -> float:
    horizon_volatility = features.annualized_volatility * math.sqrt(
        horizon_days / TRADING_DAYS_PER_YEAR
    )
    channel_width_component = features.channel_width_pct * 0.35
    return max(horizon_volatility, channel_width_component, 0.03)


def _drivers(features: PriceStructureFeatures) -> list[dict[str, float | str]]:
    return [
        {
            "name": "trend_return",
            "value": features.trend_return,
            "weight": 0.55,
            "contribution": 0.55 * features.trend_return,
        },
        {
            "name": "channel_position",
            "value": features.channel_position,
            "weight": 0.10,
            "contribution": 0.10 * features.channel_position,
        },
        {
            "name": "drawdown_from_high",
            "value": features.drawdown_from_high,
            "weight": -0.30,
            "contribution": -0.30 * features.drawdown_from_high,
        },
    ]


def _clip(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)
