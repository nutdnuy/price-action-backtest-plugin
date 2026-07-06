import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from price_action_backtest.webull import (
    WebullAPIError,
    WebullSettings,
    build_webull_data_client,
    fetch_stock_bars,
    format_webull_error,
    load_webull_settings,
    redact_webull_error,
    silence_webull_sdk_logging,
    webull_bars_to_ohlcv,
    write_webull_bars_csv,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "price_action_backtest.py"


class FakeResponse:
    def __init__(self, payload, status_code=200, text="ok"):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class FakeMarketData:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get_history_bar(self, symbol, category, timespan, **kwargs):
        self.calls.append((symbol, category, timespan, kwargs))
        return self.response


class FakeDataClient:
    def __init__(self, market_data):
        self.market_data = market_data


class FakeApiClient:
    def __init__(self, app_key, app_secret, region):
        self.app_key = app_key
        self.app_secret = app_secret
        self.region = region
        self.endpoints = []
        self.token_dir = None

    def add_endpoint(self, region, endpoint):
        self.endpoints.append((region, endpoint))

    def set_token_dir(self, token_dir):
        self.token_dir = token_dir


class WrappedDataClient:
    def __init__(self, api_client):
        self.api_client = api_client


def sample_bars():
    return [
        {
            "symbol": "AAPL",
            "time": "2026-01-02T14:30:00.000+0000",
            "open": "100",
            "high": "102",
            "low": "99",
            "close": "101",
            "volume": "1000",
        },
        {
            "symbol": "AAPL",
            "time": "2026-01-03T14:30:00.000+0000",
            "open": "101",
            "high": "103",
            "low": "100",
            "close": "102",
            "volume": "1100",
        },
    ]


def test_load_webull_settings_uses_env_file_and_redacts_repr(tmp_path, monkeypatch):
    for key in ["WEBULL_ENV", "WEBULL_REGION", "WEBULL_APP_KEY", "WEBULL_APP_SECRET"]:
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "WEBULL_ENV=prod",
                "WEBULL_REGION=us",
                "WEBULL_APP_KEY=app_key_123456",
                "WEBULL_APP_SECRET=secret_abcdef",
                f"WEBULL_TOKEN_DIR={tmp_path / 'tokens'}",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_webull_settings(env_file)

    assert settings.endpoint == "api.webull.com"
    assert settings.token_dir == tmp_path / "tokens"
    assert "app_...3456" in repr(settings)
    assert "secret_abcdef" not in repr(settings)


def test_build_webull_data_client_configures_endpoint_and_token_dir(tmp_path):
    settings = WebullSettings(
        env="uat",
        region="us",
        app_key="key",
        app_secret="secret",
        token_dir=tmp_path / "tokens",
    )

    client = build_webull_data_client(
        settings,
        api_client_cls=FakeApiClient,
        data_client_cls=WrappedDataClient,
    )

    assert client.api_client.endpoints == [("us", "us-openapi-alb.uat.webullbroker.com")]
    assert client.api_client.token_dir == str(tmp_path / "tokens")
    assert client.api_client._stream_logger_set is True
    assert client.api_client._file_logger_set is True


def test_silence_webull_sdk_logging_marks_client_logger_configured():
    api_client = FakeApiClient("visible_key", "visible_secret", "us")

    silence_webull_sdk_logging(api_client)

    assert api_client._stream_logger_set is True
    assert api_client._file_logger_set is True


def test_redact_webull_error_removes_sensitive_headers():
    message = (
        'Request: {"x-app-key": "abc123", "x-signature": "signed-value", '
        '"x-signature-nonce": "nonce-value", "x-timestamp": "2026-07-06T01:00:00Z"} '
        "app secret=secret_abcdef app key=key_123456"
    )

    redacted = redact_webull_error(message)

    assert "abc123" not in redacted
    assert "signed-value" not in redacted
    assert "nonce-value" not in redacted
    assert "2026-07-06T01:00:00Z" not in redacted
    assert "secret_abcdef" not in redacted
    assert "key_123456" not in redacted
    assert redacted.count("<redacted>") == 6


def test_format_webull_error_adds_actionable_credential_hints():
    unauthorized = format_webull_error("HTTP Status: 401, Code: UNAUTHORIZED")
    invalid_symbol = format_webull_error("HTTP Status: 403, Msg: Only AAPL is allowed")

    assert "WEBULL_ENV" in unauthorized
    assert "approved by Webull OpenAPI" in unauthorized
    assert "only permits AAPL" in invalid_symbol
    assert "production credentials" in invalid_symbol


def test_fetch_stock_bars_normalizes_args_and_passes_query_options():
    market_data = FakeMarketData(FakeResponse(sample_bars()))
    client = FakeDataClient(market_data)

    payload = fetch_stock_bars(
        client,
        " aapl ",
        timespan="d",
        count=2,
        real_time_required=False,
        trading_sessions="RTH",
        start_time=1711262998500,
        end_time=1711349398500,
    )

    assert payload == sample_bars()
    assert market_data.calls == [
        (
            "AAPL",
            "US_STOCK",
            "D",
            {
                "count": 2,
                "real_time_required": "false",
                "trading_sessions": "RTH",
                "start_time": 1711262998500,
                "end_time": 1711349398500,
            },
        )
    ]


def test_fetch_stock_bars_rejects_invalid_count_before_sdk_call():
    market_data = FakeMarketData(FakeResponse(sample_bars()))
    client = FakeDataClient(market_data)

    with pytest.raises(ValueError, match="count must be between"):
        fetch_stock_bars(client, "AAPL", timespan="D", count=1201)

    assert market_data.calls == []


def test_fetch_stock_bars_raises_api_error_on_non_200():
    response = FakeResponse({"message": "no"}, status_code=403, text="no")
    client = FakeDataClient(FakeMarketData(response))

    with pytest.raises(WebullAPIError, match="status 403"):
        fetch_stock_bars(client, "AAPL")


def test_webull_bars_to_ohlcv_normalizes_official_bar_shape():
    data = webull_bars_to_ohlcv(list(reversed(sample_bars())))

    assert list(data.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert data["date"].tolist() == [
        pd.Timestamp("2026-01-02T14:30:00.000+0000"),
        pd.Timestamp("2026-01-03T14:30:00.000+0000"),
    ]
    assert data["close"].tolist() == [101, 102]


def test_write_webull_bars_csv_creates_private_output_path(tmp_path):
    output = tmp_path / "nested" / "aapl-d.csv"

    written = write_webull_bars_csv(sample_bars(), output)

    assert written == output
    csv_text = output.read_text(encoding="utf-8")
    assert "date,open,high,low,close,volume" in csv_text


def test_webull_fetch_bars_cli_missing_credentials_returns_json_error(monkeypatch):
    for key in ["WEBULL_APP_KEY", "WEBULL_APP_SECRET"]:
        monkeypatch.delenv(key, raising=False)

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "webull-fetch-bars",
            "--symbol",
            "AAPL",
            "--env-file",
            str(ROOT / "does-not-exist.env"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "WEBULL_APP_KEY" in payload["error"]
