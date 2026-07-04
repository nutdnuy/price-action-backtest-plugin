import pandas as pd
import pytest

from price_action_backtest.data import DataQualityError, load_ohlcv


def write_csv(tmp_path, rows: str):
    path = tmp_path / "ohlcv.csv"
    path.write_text(rows, encoding="utf-8")
    return path


def test_load_ohlcv_normalizes_columns_and_sorts_dates(tmp_path):
    path = write_csv(
        tmp_path,
        "\n".join(
            [
                " Date , Open , HIGH , low , Close , Volume , ignored",
                "2024-01-03,103,105,101,104,3000,x",
                "2024-01-01,100,102,99,101,1000,y",
                "2024-01-02,101,104,100,103,2000,z",
            ]
        ),
    )

    data = load_ohlcv(path)

    assert list(data.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert data["date"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-02"),
        pd.Timestamp("2024-01-03"),
    ]
    assert data["close"].tolist() == [101, 103, 104]
    assert data.index.tolist() == [0, 1, 2]


def test_load_ohlcv_rejects_duplicate_dates(tmp_path):
    path = write_csv(
        tmp_path,
        "\n".join(
            [
                "date,open,high,low,close",
                "2024-01-01,100,102,99,101",
                "2024-01-01,101,103,100,102",
            ]
        ),
    )

    with pytest.raises(DataQualityError, match="duplicate dates"):
        load_ohlcv(path)


def test_load_ohlcv_rejects_missing_required_columns(tmp_path):
    path = write_csv(
        tmp_path,
        "\n".join(
            [
                "date,open,high,close",
                "2024-01-01,100,102,101",
                "2024-01-02,101,103,102",
            ]
        ),
    )

    with pytest.raises(DataQualityError, match="missing columns"):
        load_ohlcv(path)
