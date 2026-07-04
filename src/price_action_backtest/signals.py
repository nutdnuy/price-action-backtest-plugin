from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SignalSpec:
    strategy: str
    rsi_entry: float = 30.0
    rsi_exit: float = 55.0


def _binary_signal(condition: pd.Series) -> pd.Series:
    return condition.fillna(False).astype(int)


def _rsi_reversion(frame: pd.DataFrame, entry: float, exit: float) -> pd.Series:
    positions: list[int] = []
    is_long = False

    for value in frame["rsi_14"]:
        if pd.notna(value):
            if not is_long and value < entry:
                is_long = True
            elif is_long and value > exit:
                is_long = False
        positions.append(int(is_long))

    return pd.Series(positions, index=frame.index, name="signal")


def build_signal(frame: pd.DataFrame, spec: SignalSpec) -> pd.Series:
    if spec.strategy == "sma_cross":
        return _binary_signal(frame["sma_fast"] > frame["sma_slow"]).rename("signal")
    if spec.strategy == "ema_cross":
        return _binary_signal(frame["ema_fast"] > frame["ema_slow"]).rename("signal")
    if spec.strategy == "rsi_reversion":
        return _rsi_reversion(frame, spec.rsi_entry, spec.rsi_exit)
    if spec.strategy == "macd_trend":
        return _binary_signal(frame["macd"] > frame["macd_signal"]).rename("signal")

    raise ValueError(f"unsupported strategy: {spec.strategy}")
