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

    data["date"] = pd.to_datetime(data["date"], errors="coerce", format="mixed")
    if data["date"].isna().any():
        invalid_count = int(data["date"].isna().sum())
        raise DataQualityError(f"invalid dates: {invalid_count} rows")

    numeric_columns = [column for column in columns if column != "date"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    invalid_numeric_columns = [column for column in numeric_columns if data[column].isna().any()]
    if invalid_numeric_columns:
        raise DataQualityError(
            f"missing or non-numeric values: {', '.join(invalid_numeric_columns)}"
        )

    ohlc_columns = ["open", "high", "low", "close"]
    non_positive_columns = [column for column in ohlc_columns if (data[column] <= 0).any()]
    if non_positive_columns:
        raise DataQualityError(f"non-positive OHLC prices: {', '.join(non_positive_columns)}")

    high_too_low = data["high"].lt(data[["open", "low", "close"]].max(axis=1))
    low_too_high = data["low"].gt(data[["open", "high", "close"]].min(axis=1))
    if (high_too_low | low_too_high).any():
        raise DataQualityError("inconsistent OHLC")

    if data["date"].duplicated().any():
        raise DataQualityError("duplicate dates")

    if len(data) < min_rows:
        raise DataQualityError(f"too few rows: expected at least {min_rows}")

    return data.sort_values("date").reset_index(drop=True)
