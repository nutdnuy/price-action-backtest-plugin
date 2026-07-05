from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

THEME = {
    "dark": "#121212",
    "surface": "#1D1D1D",
    "surface_2": "#212121",
    "surface_3": "#242424",
    "primary": "#69F0AE",
    "primary_variant": "#00C853",
    "secondary": "#03DAC6",
    "profit": "#00E676",
    "loss": "#FF5252",
    "neutral": "#B0BEC5",
    "error": "#CF6679",
    "text_high": "rgba(255, 255, 255, 0.87)",
    "text_medium": "rgba(255, 255, 255, 0.60)",
    "grid": "rgba(255, 255, 255, 0.08)",
}

BAND_LABELS = {
    "p10": "P10",
    "p25": "P25",
    "p50": "P50",
    "p75": "P75",
    "p90": "P90",
}

DRIVER_INTERPRETATIONS = {
    "trend_return": "Positive when the recent price window trends upward.",
    "channel_position": "Positive when the close is above the channel midpoint.",
    "drawdown_from_high": "Positive when the close is below the recent channel high.",
    "clipping_adjustment": (
        "Adjustment applied so the heuristic expected return stays within the capped "
        "research range."
    ),
}

PERCENT_FIELDS = {
    "annualized_volatility",
    "channel_width_pct",
    "drawdown_from_high",
    "expected_return",
    "raw_expected_return",
    "trend_return",
}


def render_target_report(payload_path: str | Path, output_path: str | Path) -> Path:
    """Render a standalone QuantSeras-style target explanation report."""
    source_path = Path(payload_path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    _validate_payload(payload)

    report_path = Path(output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render_document(payload), encoding="utf-8")
    return report_path


def _render_document(payload: dict[str, Any]) -> str:
    symbol = str(payload.get("symbol", "Unknown")).upper()
    title = f"{symbol} Explainable Target Price"
    safe_title = html.escape(title)
    subtitle = _subtitle(payload)
    limitations = html.escape(str(payload.get("limitations", "")))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{
      --qs-dark: {THEME["dark"]};
      --qs-surface: {THEME["surface"]};
      --qs-surface-2: {THEME["surface_2"]};
      --qs-surface-3: {THEME["surface_3"]};
      --qs-primary: {THEME["primary"]};
      --qs-primary-variant: {THEME["primary_variant"]};
      --qs-secondary: {THEME["secondary"]};
      --qs-profit: {THEME["profit"]};
      --qs-loss: {THEME["loss"]};
      --qs-neutral: {THEME["neutral"]};
      --qs-error: {THEME["error"]};
      --qs-text-high: {THEME["text_high"]};
      --qs-text-medium: {THEME["text_medium"]};
      --qs-grid: {THEME["grid"]};
    }}
    body {{
      margin: 0;
      background: var(--qs-dark);
      color: var(--qs-text-high);
      font-family:
        Inter,
        "IBM Plex Sans",
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    header {{
      margin-bottom: 24px;
    }}
    h1 {{
      margin: 0 0 8px;
      color: var(--qs-primary);
      font-size: 32px;
      font-weight: 600;
      line-height: 1.25;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      font-weight: 600;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    .subtitle {{
      margin: 0;
      color: var(--qs-text-medium);
      font-size: 14px;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}
    .card,
    .panel {{
      background: var(--qs-surface);
      border: 1px solid var(--qs-grid);
      border-radius: 8px;
      padding: 16px;
    }}
    .panel {{
      margin-top: 16px;
      overflow-x: auto;
    }}
    .label {{
      color: var(--qs-text-medium);
      font-size: 12px;
      line-height: 16px;
      margin-bottom: 8px;
      text-transform: uppercase;
    }}
    .value {{
      font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
      font-size: 24px;
      font-variant-numeric: tabular-nums;
      line-height: 32px;
      overflow-wrap: anywhere;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th {{
      background: var(--qs-surface-3);
      color: var(--qs-text-medium);
      font-weight: 600;
      text-align: left;
    }}
    th,
    td {{
      border-bottom: 1px solid var(--qs-grid);
      padding: 10px 12px;
      vertical-align: top;
    }}
    td.number,
    th.number {{
      text-align: right;
      font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
      font-variant-numeric: tabular-nums;
      white-space: nowrap;
    }}
    .profit {{
      color: var(--qs-profit);
    }}
    .loss {{
      color: var(--qs-loss);
    }}
    .limitations {{
      background: var(--qs-surface-2);
      border-left: 3px solid var(--qs-primary);
      color: var(--qs-text-medium);
    }}
    .limitations p {{
      margin: 0;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{safe_title}</h1>
      <p class="subtitle">{subtitle}</p>
    </header>
    <section class="cards">
      {_metric_card("Target Price", payload.get("target_price"))}
      {_metric_card("Last Close", _feature(payload, "last_close"))}
      {_metric_card("Expected Return", payload.get("expected_return"), "expected_return")}
      {_metric_card("Horizon", payload.get("horizon_days"), suffix=" days")}
    </section>
    <section class="panel">
      <h2>Probability Bands</h2>
      {_bands_table(payload)}
    </section>
    <section class="panel">
      <h2>Drivers</h2>
      {_drivers_table(payload)}
    </section>
    <section class="panel">
      <h2>Features</h2>
      {_features_table(payload)}
    </section>
    <section class="panel limitations">
      <h2>Limitations</h2>
      <p>{limitations}</p>
    </section>
  </main>
</body>
</html>
"""


def _metric_card(
    label: str,
    value: Any,
    field_name: str | None = None,
    *,
    suffix: str = "",
) -> str:
    css_class = _number_class(value)
    formatted = _format_number(value, field_name=field_name)
    return (
        '<article class="card">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="value {css_class}">{html.escape(formatted + suffix)}</div>'
        "</article>"
    )


def _bands_table(payload: dict[str, Any]) -> str:
    bands = payload.get("price_bands", {})
    if not isinstance(bands, dict) or not bands:
        return '<p class="subtitle">No probability bands were supplied.</p>'

    ordered_keys = [key for key in BAND_LABELS if key in bands]
    ordered_keys.extend(sorted(key for key in bands if key not in BAND_LABELS))
    rows = []
    for key in ordered_keys:
        value = bands[key]
        rows.append(
            "<tr>"
            f"<td>{html.escape(BAND_LABELS.get(str(key), str(key)))}</td>"
            f'<td class="number {_number_class(value)}">'
            f"{html.escape(_format_number(value))}</td>"
            "</tr>"
        )
    return "<table><thead><tr><th>Band</th><th class=\"number\">Price</th></tr></thead><tbody>" + (
        "".join(rows)
    ) + "</tbody></table>"


def _drivers_table(payload: dict[str, Any]) -> str:
    drivers = payload.get("drivers", [])
    if not isinstance(drivers, list) or not drivers:
        return '<p class="subtitle">No target drivers were supplied.</p>'

    rows = []
    for driver in drivers:
        if not isinstance(driver, dict):
            continue
        name = html.escape(str(driver.get("name", "")))
        value = driver.get("value")
        weight = driver.get("weight")
        contribution = driver.get("contribution")
        raw_interpretation = driver.get("interpretation") or DRIVER_INTERPRETATIONS.get(
            str(driver.get("name", "")), ""
        )
        interpretation = html.escape(str(raw_interpretation))
        rows.append(
            "<tr>"
            f"<td>{name}</td>"
            f'<td class="number {_number_class(value)}">'
            f"{html.escape(_format_number(value, field_name=str(driver.get('name', ''))))}</td>"
            f'<td class="number {_number_class(weight)}">{html.escape(_format_number(weight))}</td>'
            f'<td class="number {_number_class(contribution)}">'
            f"{html.escape(_format_number(contribution))}</td>"
            f"<td>{interpretation}</td>"
            "</tr>"
        )
    if not rows:
        return '<p class="subtitle">No target drivers were supplied.</p>'
    return (
        "<table><thead><tr>"
        "<th>Driver</th>"
        '<th class="number">Value</th>'
        '<th class="number">Weight</th>'
        '<th class="number">Contribution</th>'
        "<th>Interpretation</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _features_table(payload: dict[str, Any]) -> str:
    features = payload.get("features", {})
    if not isinstance(features, dict) or not features:
        return '<p class="subtitle">No features were supplied.</p>'

    rows = []
    for key in sorted(features):
        value = features[key]
        rows.append(
            "<tr>"
            f"<td>{html.escape(_labelize(str(key)))}</td>"
            f'<td class="number {_number_class(value)}">'
            f"{html.escape(_format_number(value, field_name=str(key)))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Feature</th><th class=\"number\">Value</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _format_number(value: Any, *, field_name: str | None = None) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if field_name in PERCENT_FIELDS:
            return f"{value:.2%}"
        return f"{value:.4f}"
    return str(value)


def _validate_payload(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise ValueError("target explanation JSON must contain an object")

    required_fields = [
        "symbol",
        "as_of_date",
        "method",
        "horizon_days",
        "target_price",
        "price_bands",
        "features",
        "drivers",
        "limitations",
    ]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"target explanation JSON missing required field: {field}")

    if not isinstance(payload["price_bands"], dict):
        raise ValueError("target explanation field must be an object: price_bands")
    if not isinstance(payload["features"], dict):
        raise ValueError("target explanation field must be an object: features")
    if not isinstance(payload["drivers"], list):
        raise ValueError("target explanation field must be a list: drivers")


def _subtitle(payload: dict[str, Any]) -> str:
    parts = []
    for key, label in [
        ("as_of_date", "As of"),
        ("method", "Method"),
    ]:
        value = payload.get(key)
        if value:
            parts.append(f"{label}: {value}")
    if payload.get("expected_return_clipped") is True:
        parts.append("Expected return clipped")
    if not parts:
        return "Deterministic price-structure research report."
    return html.escape(" | ".join(str(part) for part in parts))


def _feature(payload: dict[str, Any], key: str) -> Any:
    features = payload.get("features", {})
    if not isinstance(features, dict):
        return None
    return features.get(key)


def _number_class(value: Any) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int | float):
        if value > 0:
            return "profit"
        if value < 0:
            return "loss"
    return ""


def _labelize(value: str) -> str:
    return value.replace("_", " ").title()
