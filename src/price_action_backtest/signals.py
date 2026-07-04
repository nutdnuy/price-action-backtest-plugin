from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

import pandas as pd


@dataclass(frozen=True)
class SignalSpec:
    strategy: str
    rsi_entry: float = 30.0
    rsi_exit: float = 55.0


def _binary_signal(condition: pd.Series) -> pd.Series:
    return condition.fillna(False).astype(int)


def _require_columns(frame: pd.DataFrame, strategy: str, columns: tuple[str, ...]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(f"missing columns for {strategy}: {missing_names}")


def _validate_rsi_params(entry: float, exit: float) -> None:
    if not isinstance(entry, Real) or not isfinite(entry):
        raise ValueError("rsi_entry must be finite")
    if not isinstance(exit, Real) or not isfinite(exit):
        raise ValueError("rsi_exit must be finite")
    if not 0 <= entry <= 100:
        raise ValueError("rsi_entry must be within [0, 100]")
    if not 0 <= exit <= 100:
        raise ValueError("rsi_exit must be within [0, 100]")
    if entry >= exit:
        raise ValueError("rsi_entry must be less than rsi_exit")


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
        _require_columns(frame, spec.strategy, ("sma_fast", "sma_slow"))
        return _binary_signal(frame["sma_fast"] > frame["sma_slow"]).rename("signal")
    if spec.strategy == "ema_cross":
        _require_columns(frame, spec.strategy, ("ema_fast", "ema_slow"))
        return _binary_signal(frame["ema_fast"] > frame["ema_slow"]).rename("signal")
    if spec.strategy == "rsi_reversion":
        _require_columns(frame, spec.strategy, ("rsi_14",))
        _validate_rsi_params(spec.rsi_entry, spec.rsi_exit)
        return _rsi_reversion(frame, spec.rsi_entry, spec.rsi_exit)
    if spec.strategy == "macd_trend":
        _require_columns(frame, spec.strategy, ("macd", "macd_signal"))
        return _binary_signal(frame["macd"] > frame["macd_signal"]).rename("signal")

    raise ValueError(f"unsupported strategy: {spec.strategy}")
