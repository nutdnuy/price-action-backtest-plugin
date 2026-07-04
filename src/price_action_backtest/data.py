from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["date", "open", "high", "low", "close"]
OPTIONAL_COLUMNS = ["volume"]


class DataQualityError(ValueError):
    pass


def load_ohlcv(path: str | Path, min_rows: int = 2) -> pd.DataFrame:
    data = pd.read_csv(path)
    data.columns = [column.strip().lower() for column in data.columns]

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        raise DataQualityError(f"missing columns: {', '.join(missing_columns)}")

    columns = REQUIRED_COLUMNS + [column for column in OPTIONAL_COLUMNS if column in data.columns]
    data = data.loc[:, columns].copy()

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    if data["date"].isna().any():
        raise DataQualityError("invalid dates")

    numeric_columns = [column for column in columns if column != "date"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    if data[numeric_columns].isna().any().any():
        raise DataQualityError("missing or non-numeric values")

    if (data[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataQualityError("non-positive OHLC prices")

    if data["date"].duplicated().any():
        raise DataQualityError("duplicate dates")

    if len(data) < min_rows:
        raise DataQualityError(f"too few rows: expected at least {min_rows}")

    return data.sort_values("date").reset_index(drop=True)
