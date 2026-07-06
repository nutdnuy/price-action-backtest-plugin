from __future__ import annotations

import logging
import os
import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from price_action_backtest.data import normalize_ohlcv_frame

WEBULL_ENDPOINTS = {
    "uat": "us-openapi-alb.uat.webullbroker.com",
    "prod": "api.webull.com",
}
WEBULL_CATEGORIES = {"US_STOCK", "US_ETF"}
WEBULL_TIMESPANS = {"M1", "M5", "M15", "M30", "M60", "M120", "M240", "D", "W", "M", "Y"}
SENSITIVE_ERROR_PATTERNS = (
    (re.compile(r'("x-app-key"\s*:\s*")[^"]+'), r"\1<redacted>"),
    (re.compile(r'("x-signature"\s*:\s*")[^"]+'), r"\1<redacted>"),
    (re.compile(r'("x-signature-nonce"\s*:\s*")[^"]+'), r"\1<redacted>"),
    (re.compile(r'("x-timestamp"\s*:\s*")[^"]+'), r"\1<redacted>"),
    (re.compile(r"(app[_ -]?key[=: ]+)[A-Za-z0-9._/-]+", re.IGNORECASE), r"\1<redacted>"),
    (re.compile(r"(app[_ -]?secret[=: ]+)[A-Za-z0-9._/-]+", re.IGNORECASE), r"\1<redacted>"),
)


class WebullAPIError(RuntimeError):
    pass


def redact_secret(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 5:
        return "*****"
    return f"{value[:4]}...{value[-4:]}"


def redact_webull_error(message: str) -> str:
    redacted = message
    for pattern, replacement in SENSITIVE_ERROR_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def format_webull_error(message: str) -> str:
    redacted = redact_webull_error(message)
    normalized = redacted.upper()
    if "UNAUTHORIZED" in normalized:
        return (
            f"{redacted}. Check that WEBULL_ENV matches the app key environment "
            "and that the key is approved by Webull OpenAPI."
        )
    if "ONLY AAPL IS ALLOWED" in normalized:
        return (
            f"{redacted}. The current Webull UAT test credential only permits AAPL; "
            "use approved production credentials with US market-data permission for other symbols."
        )
    return redacted


def silence_webull_sdk_logging(api_client: Any | None = None) -> None:
    silent_logger = logging.getLogger("price_action_backtest.webull.silent")
    silent_logger.handlers.clear()
    silent_logger.addHandler(logging.NullHandler())
    silent_logger.setLevel(logging.CRITICAL + 1)
    silent_logger.propagate = False

    for logger_name in ("webull.core", "webull.data"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(logging.NullHandler())
        logger.setLevel(logging.CRITICAL + 1)
        logger.propagate = False

    if api_client is not None:
        if hasattr(api_client, "set_logger"):
            api_client.set_logger(silent_logger)
        # Prevent DataClient from installing its default stdout/file loggers, which
        # include signed request headers when Webull returns an authentication error.
        api_client._stream_logger_set = True
        api_client._file_logger_set = True


@dataclass(frozen=True)
class WebullSettings:
    env: str
    region: str
    app_key: str
    app_secret: str
    token_dir: Path | None = None

    @property
    def endpoint(self) -> str:
        return WEBULL_ENDPOINTS[self.env]

    def __repr__(self) -> str:
        return (
            "WebullSettings("
            f"env={self.env!r}, "
            f"region={self.region!r}, "
            f"app_key={redact_secret(self.app_key)!r}, "
            f"app_secret={redact_secret(self.app_secret)!r}, "
            f"token_dir={str(self.token_dir) if self.token_dir else None!r}"
            ")"
        )


def _read_env_file(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    env_path = Path(path).expanduser()
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = shlex.split(value, comments=False, posix=True)[0] if value.strip() else ""
    return values


def _env_value(key: str, file_values: dict[str, str], default: str = "") -> str:
    return os.getenv(key, file_values.get(key, default)).strip()


def load_webull_settings(env_file: str | Path | None = ".env") -> WebullSettings:
    file_values = _read_env_file(env_file)
    env = _env_value("WEBULL_ENV", file_values, "uat").lower()
    if env not in WEBULL_ENDPOINTS:
        valid = ", ".join(sorted(WEBULL_ENDPOINTS))
        raise ValueError(f"WEBULL_ENV must be one of: {valid}")

    app_key = _env_value("WEBULL_APP_KEY", file_values)
    app_secret = _env_value("WEBULL_APP_SECRET", file_values)
    if not app_key or not app_secret:
        raise RuntimeError("WEBULL_APP_KEY and WEBULL_APP_SECRET are required")

    token_dir_value = _env_value("WEBULL_TOKEN_DIR", file_values)
    return WebullSettings(
        env=env,
        region=_env_value("WEBULL_REGION", file_values, "us").lower(),
        app_key=app_key,
        app_secret=app_secret,
        token_dir=Path(token_dir_value).expanduser() if token_dir_value else None,
    )


def build_webull_data_client(
    settings: WebullSettings,
    api_client_cls: type[Any] | None = None,
    data_client_cls: type[Any] | None = None,
) -> Any:
    silence_webull_sdk_logging()
    if api_client_cls is None:
        from webull.core.client import ApiClient

        api_client_cls = ApiClient
    if data_client_cls is None:
        from webull.data.data_client import DataClient

        data_client_cls = DataClient

    api_client = api_client_cls(settings.app_key, settings.app_secret, settings.region)
    api_client.add_endpoint(settings.region, settings.endpoint)
    if settings.token_dir is not None:
        api_client.set_token_dir(str(settings.token_dir))
    silence_webull_sdk_logging(api_client)
    return data_client_cls(api_client)


def response_json_or_raise(response: Any) -> Any:
    status_code = getattr(response, "status_code", None)
    if status_code != 200:
        text = getattr(response, "text", "")
        raise WebullAPIError(f"Webull API returned status {status_code}: {text}")
    return response.json()


def _validate_fetch_args(
    symbol: str,
    category: str,
    timespan: str,
    count: int,
) -> tuple[str, str, str]:
    clean_symbol = symbol.strip().upper()
    clean_category = category.strip().upper()
    clean_timespan = timespan.strip().upper()
    if not clean_symbol:
        raise ValueError("symbol is required")
    if clean_category not in WEBULL_CATEGORIES:
        valid = ", ".join(sorted(WEBULL_CATEGORIES))
        raise ValueError(f"category must be one of: {valid}")
    if clean_timespan not in WEBULL_TIMESPANS:
        valid = ", ".join(sorted(WEBULL_TIMESPANS))
        raise ValueError(f"timespan must be one of: {valid}")
    max_count = 1650 if clean_timespan == "M1" else 1200
    if count < 1 or count > max_count:
        raise ValueError(f"count must be between 1 and {max_count} for {clean_timespan}")
    return clean_symbol, clean_category, clean_timespan


def fetch_stock_bars(
    data_client: Any,
    symbol: str,
    *,
    category: str = "US_STOCK",
    timespan: str = "D",
    count: int = 200,
    real_time_required: bool = True,
    trading_sessions: str | None = None,
    start_time: int | None = None,
    end_time: int | None = None,
) -> Any:
    clean_symbol, clean_category, clean_timespan = _validate_fetch_args(
        symbol, category, timespan, count
    )
    kwargs: dict[str, Any] = {
        "count": count,
        "real_time_required": str(real_time_required).lower(),
    }
    if trading_sessions:
        kwargs["trading_sessions"] = trading_sessions
    if start_time is not None:
        kwargs["start_time"] = start_time
    if end_time is not None:
        kwargs["end_time"] = end_time

    try:
        response = data_client.market_data.get_history_bar(
            clean_symbol, clean_category, clean_timespan, **kwargs
        )
    except TypeError as exc:
        raise TypeError(
            "Installed Webull SDK does not accept the requested historical-bar "
            "parameters; upgrade webull-openapi-python-sdk or retry with fewer options."
        ) from exc
    return response_json_or_raise(response)


def webull_bars_to_ohlcv(payload: Any, min_rows: int = 2) -> pd.DataFrame:
    if not isinstance(payload, list):
        raise ValueError("Webull historical bars response must be a list")
    if not payload:
        raise ValueError("Webull historical bars response is empty")

    raw = pd.DataFrame(payload)
    if "time" not in raw.columns:
        raise ValueError("Webull historical bars response missing time")

    rename_map = {"time": "date"}
    raw = raw.rename(columns=rename_map)
    columns = ["date", "open", "high", "low", "close"]
    if "volume" in raw.columns:
        columns.append("volume")
    missing = [column for column in columns if column not in raw.columns]
    if missing:
        raise ValueError(f"Webull historical bars response missing: {', '.join(missing)}")
    return normalize_ohlcv_frame(raw.loc[:, columns], min_rows=min_rows)


def write_webull_bars_csv(payload: Any, output_path: str | Path, min_rows: int = 2) -> Path:
    output = Path(output_path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    data = webull_bars_to_ohlcv(payload, min_rows=min_rows)
    data.to_csv(output, index=False)
    return output
