from __future__ import annotations

import pandas as pd


def add_indicators(
    frame: pd.DataFrame,
    fast_window: int = 5,
    slow_window: int = 20,
) -> pd.DataFrame:
    data = frame.copy()
    close = data["close"]

    data["sma_fast"] = close.rolling(window=fast_window).mean()
    data["sma_slow"] = close.rolling(window=slow_window).mean()
    data["ema_fast"] = close.ewm(span=fast_window, adjust=False).mean()
    data["ema_slow"] = close.ewm(span=slow_window, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.rolling(window=14).mean()
    average_loss = loss.rolling(window=14).mean()
    relative_strength = average_gain / average_loss
    rsi = 100 - (100 / (1 + relative_strength))
    no_gain = average_gain.eq(0)
    no_loss = average_loss.eq(0)
    rsi = rsi.mask(no_loss & average_gain.gt(0), 100)
    rsi = rsi.mask(no_gain & average_loss.gt(0), 0)
    rsi = rsi.mask(no_gain & no_loss, 50)
    data["rsi_14"] = rsi

    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    data["macd"] = ema_12 - ema_26
    data["macd_signal"] = data["macd"].ewm(span=9, adjust=False).mean()

    rolling_close = close.rolling(window=slow_window)
    data["bb_mid"] = rolling_close.mean()
    bb_std = rolling_close.std(ddof=0)
    data["bb_upper"] = data["bb_mid"] + (2 * bb_std)
    data["bb_lower"] = data["bb_mid"] - (2 * bb_std)

    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            data["high"] - data["low"],
            (data["high"] - previous_close).abs(),
            (data["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    data["atr_14"] = true_range.rolling(window=14).mean()

    return data
