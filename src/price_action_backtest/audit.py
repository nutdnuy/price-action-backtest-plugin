from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_FILES = ("config.json", "metrics.json", "equity.csv", "trades.csv", "report.html")
EXTREME_DRAWDOWN_THRESHOLD = -0.80


def audit_run(run_dir: str | Path) -> dict[str, list[str] | bool]:
    output_dir = Path(run_dir)
    errors: list[str] = []
    warnings: list[str] = []

    if not output_dir.exists():
        errors.append(f"run directory does not exist: {output_dir}")
        return _result(errors, warnings)
    if not output_dir.is_dir():
        errors.append(f"run path is not a directory: {output_dir}")
        return _result(errors, warnings)

    for name in REQUIRED_FILES:
        if not (output_dir / name).exists():
            errors.append(f"missing required output file: {name}")

    config = _read_json_object(output_dir / "config.json", "config.json", errors)
    metrics = _read_json_object(output_dir / "metrics.json", "metrics.json", errors)

    if config is not None:
        _audit_costs(config, warnings)
    if metrics is not None:
        _audit_metrics(metrics, warnings)

    return _result(errors, warnings)


def _result(errors: list[str], warnings: list[str]) -> dict[str, list[str] | bool]:
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _read_json_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label}: {exc}")
        return None

    if not isinstance(payload, dict):
        errors.append(f"{label} must contain a JSON object")
        return None
    return payload


def _audit_costs(config: dict[str, Any], warnings: list[str]) -> None:
    fee_bps = _numeric(config.get("fee_bps", 0.0))
    slippage_bps = _numeric(config.get("slippage_bps", 0.0))
    if fee_bps == 0.0 and slippage_bps == 0.0:
        warnings.append("fee_bps and slippage_bps are both zero; results ignore trading costs.")


def _audit_metrics(metrics: dict[str, Any], warnings: list[str]) -> None:
    trade_count = _numeric(metrics.get("trade_count"))
    if trade_count == 0.0:
        warnings.append(
            "trade_count is zero; review signal parameters and confirm a no-trade run is expected."
        )

    max_drawdown = _numeric(metrics.get("max_drawdown"))
    if max_drawdown is not None and max_drawdown <= EXTREME_DRAWDOWN_THRESHOLD:
        warnings.append(
            f"max_drawdown is {max_drawdown:.2%}; "
            "review risk assumptions before sharing this result."
        )


def _numeric(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
