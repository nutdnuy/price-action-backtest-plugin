from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

LIMITATIONS_TEXT = "Historical performance does not guarantee future performance"
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

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
    "benchmark": "#03DAC6",
    "neutral": "#B0BEC5",
    "error": "#CF6679",
    "text_high": "rgba(255, 255, 255, 0.87)",
    "text_medium": "rgba(255, 255, 255, 0.60)",
    "grid": "rgba(255, 255, 255, 0.08)",
}

METRIC_LABELS = {
    "total_return": "Total Return",
    "buy_hold_return": "Buy & Hold Return",
    "annualized_return": "Annualized Return",
    "annualized_volatility": "Annualized Volatility",
    "sharpe": "Sharpe",
    "max_drawdown": "Max Drawdown",
    "trade_count": "Trade Count",
    "total_cost": "Total Cost",
}

PERCENT_METRICS = {
    "total_return",
    "buy_hold_return",
    "annualized_return",
    "annualized_volatility",
    "max_drawdown",
    "total_cost",
}


def render_html_report(
    run_dir: str | Path,
    title: str,
    equity: pd.DataFrame,
    trades: pd.DataFrame,
    metrics: dict[str, Any],
) -> str:
    """Render a QuantSeras-style standalone HTML report and return its path."""
    output_dir = Path(run_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    clean_equity = _prepare_equity(equity)
    clean_trades = _prepare_trades(trades)
    fig = _build_figure(title, clean_equity, clean_trades)
    heatmap = _build_monthly_heatmap(clean_equity)
    chart_html = fig.to_html(
        full_html=False,
        include_plotlyjs=True,
        config={"displayModeBar": False, "responsive": True},
    )
    heatmap_html = heatmap.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": False, "responsive": True},
    )

    html = _render_document(
        title=title,
        chart_html=chart_html,
        heatmap_html=heatmap_html,
        metrics_html=_render_metrics_table(metrics),
        trades_html=_render_trades_table(clean_trades),
    )
    report_path = output_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")
    return str(report_path)


def _prepare_equity(equity: pd.DataFrame) -> pd.DataFrame:
    required_columns = ["date", "close", "strategy_equity", "drawdown"]
    missing = [column for column in required_columns if column not in equity.columns]
    if missing:
        raise ValueError(f"equity is missing columns: {', '.join(missing)}")

    clean = equity.copy()
    clean["date"] = pd.to_datetime(clean["date"], errors="raise")
    numeric_columns = ["close", "strategy_equity", "drawdown"]
    if "buy_hold_equity" in clean.columns:
        numeric_columns.append("buy_hold_equity")
    for column in numeric_columns:
        clean[column] = pd.to_numeric(clean[column], errors="raise")
    return clean.sort_values("date").reset_index(drop=True)


def _prepare_trades(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()

    required_columns = ["date", "close", "position_change"]
    missing = [column for column in required_columns if column not in trades.columns]
    if missing:
        raise ValueError(f"trades is missing columns: {', '.join(missing)}")

    clean = trades.copy()
    clean["date"] = pd.to_datetime(clean["date"], errors="raise")
    clean["close"] = pd.to_numeric(clean["close"], errors="raise")
    clean["position_change"] = pd.to_numeric(clean["position_change"], errors="raise")
    if "cost" in clean.columns:
        clean["cost"] = pd.to_numeric(clean["cost"], errors="raise")
    return clean.sort_values("date").reset_index(drop=True)


def _build_figure(title: str, equity: pd.DataFrame, trades: pd.DataFrame) -> go.Figure:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.42, 0.36, 0.22],
        subplot_titles=("Price", "Equity Curve", "Drawdown"),
    )

    fig.add_trace(
        go.Scatter(
            x=equity["date"],
            y=equity["close"],
            mode="lines",
            name="Close",
            line={"color": THEME["neutral"], "width": 1.8},
            hovertemplate="%{x|%Y-%m-%d}<br>Close %{y:.4f}<extra></extra>",
        ),
        row=1,
        col=1,
    )
    _add_trade_markers(fig, trades)

    fig.add_trace(
        go.Scatter(
            x=equity["date"],
            y=equity["strategy_equity"],
            mode="lines",
            name="Strategy",
            line={"color": THEME["primary"], "width": 2.4},
            hovertemplate="%{x|%Y-%m-%d}<br>Strategy %{y:.4f}<extra></extra>",
        ),
        row=2,
        col=1,
    )
    if "buy_hold_equity" in equity.columns:
        fig.add_trace(
            go.Scatter(
                x=equity["date"],
                y=equity["buy_hold_equity"],
                mode="lines",
                name="Buy & Hold",
                line={"color": THEME["benchmark"], "width": 1.8, "dash": "dash"},
                hovertemplate="%{x|%Y-%m-%d}<br>Buy & Hold %{y:.4f}<extra></extra>",
            ),
            row=2,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=equity["date"],
            y=equity["drawdown"],
            mode="lines",
            name="Drawdown",
            fill="tozeroy",
            line={"color": THEME["loss"], "width": 1.8},
            fillcolor="rgba(255, 82, 82, 0.22)",
            hovertemplate="%{x|%Y-%m-%d}<br>Drawdown %{y:.2%}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        title={"text": title, "x": 0.01, "xanchor": "left"},
        height=880,
        paper_bgcolor=THEME["dark"],
        plot_bgcolor=THEME["dark"],
        font={
            "family": "Inter, IBM Plex Sans, -apple-system, sans-serif",
            "color": THEME["text_high"],
        },
        margin={"l": 58, "r": 26, "t": 80, "b": 48},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(0,0,0,0)",
        },
        hoverlabel={
            "bgcolor": "#2E2E2E",
            "bordercolor": "rgba(255, 255, 255, 0.12)",
            "font": {"color": THEME["text_high"]},
        },
    )
    fig.update_xaxes(
        gridcolor=THEME["grid"],
        linecolor=THEME["grid"],
        tickfont={"color": THEME["text_medium"]},
    )
    fig.update_yaxes(
        gridcolor=THEME["grid"],
        linecolor=THEME["grid"],
        tickfont={"color": THEME["text_medium"]},
    )
    fig.update_yaxes(tickformat=".2%", row=3, col=1)
    return fig


def _build_monthly_heatmap(equity: pd.DataFrame) -> go.Figure:
    monthly = _monthly_strategy_returns(equity)
    years = sorted(monthly["year"].unique().tolist()) if not monthly.empty else []
    values_by_cell = {
        (int(row.year), int(row.month)): float(row.monthly_return)
        for row in monthly.itertuples(index=False)
    }
    z = []
    text = []
    for year in years:
        z_row = []
        text_row = []
        for month in range(1, 13):
            value = values_by_cell.get((year, month))
            z_row.append(value)
            text_row.append("" if value is None else f"{value:+.1%}")
        z.append(z_row)
        text.append(text_row)

    heatmap = go.Figure(
        data=[
            go.Heatmap(
                x=MONTH_LABELS,
                y=[str(year) for year in years],
                z=z,
                text=text,
                texttemplate="%{text}",
                textfont={"color": THEME["text_high"]},
                colorscale=[
                    [0.0, THEME["loss"]],
                    [0.5, THEME["surface_3"]],
                    [1.0, THEME["profit"]],
                ],
                zmid=0,
                hovertemplate="%{y} %{x}<br>Return %{z:.2%}<extra></extra>",
                colorbar={
                    "title": {"text": "Return", "font": {"color": THEME["text_medium"]}},
                    "tickformat": ".1%",
                    "tickfont": {"color": THEME["text_medium"]},
                },
            )
        ]
    )
    heatmap.update_layout(
        title={"text": "Monthly Returns Heatmap", "x": 0.01, "xanchor": "left"},
        height=max(260, 80 + (len(years) * 42)),
        paper_bgcolor=THEME["dark"],
        plot_bgcolor=THEME["dark"],
        font={
            "family": "Inter, IBM Plex Sans, -apple-system, sans-serif",
            "color": THEME["text_high"],
        },
        margin={"l": 58, "r": 26, "t": 64, "b": 44},
    )
    heatmap.update_xaxes(
        side="top",
        gridcolor=THEME["grid"],
        linecolor=THEME["grid"],
        tickfont={"color": THEME["text_medium"]},
    )
    heatmap.update_yaxes(
        autorange="reversed",
        gridcolor=THEME["grid"],
        linecolor=THEME["grid"],
        tickfont={"color": THEME["text_medium"]},
    )
    return heatmap


def _monthly_strategy_returns(equity: pd.DataFrame) -> pd.DataFrame:
    indexed = equity.loc[:, ["date", "strategy_equity"]].set_index("date")
    monthly = indexed["strategy_equity"].resample("ME").agg(["first", "last"]).dropna()
    previous_month_end = monthly["last"].shift(1)
    baseline = previous_month_end.fillna(monthly["first"])
    returns = (monthly["last"] / baseline) - 1
    output = returns.rename("monthly_return").reset_index()
    output["year"] = output["date"].dt.year
    output["month"] = output["date"].dt.month
    return output.loc[:, ["year", "month", "monthly_return"]]


def _add_trade_markers(fig: go.Figure, trades: pd.DataFrame) -> None:
    if trades.empty:
        return

    entries = trades[trades["position_change"] > 0]
    exits = trades[trades["position_change"] < 0]
    if not entries.empty:
        fig.add_trace(
            go.Scatter(
                x=entries["date"],
                y=entries["close"],
                mode="markers",
                name="Entry",
                marker={"symbol": "triangle-up", "size": 11, "color": THEME["profit"]},
                hovertemplate="%{x|%Y-%m-%d}<br>Entry %{y:.4f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
    if not exits.empty:
        fig.add_trace(
            go.Scatter(
                x=exits["date"],
                y=exits["close"],
                mode="markers",
                name="Exit",
                marker={"symbol": "x", "size": 11, "color": THEME["loss"]},
                hovertemplate="%{x|%Y-%m-%d}<br>Exit %{y:.4f}<extra></extra>",
            ),
            row=1,
            col=1,
        )


def _render_document(
    title: str,
    chart_html: str,
    heatmap_html: str,
    metrics_html: str,
    trades_html: str,
) -> str:
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{
      --qs-dark: #121212;
      --qs-surface: #1D1D1D;
      --qs-surface-2: #212121;
      --qs-surface-3: #242424;
      --qs-primary: #69F0AE;
      --qs-primary-variant: #00C853;
      --qs-secondary: #03DAC6;
      --qs-profit: #00E676;
      --qs-loss: #FF5252;
      --qs-benchmark: #03DAC6;
      --qs-text-high: rgba(255, 255, 255, 0.87);
      --qs-text-medium: rgba(255, 255, 255, 0.60);
      --qs-grid: rgba(255, 255, 255, 0.08);
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
      max-width: 1440px;
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
    .subtitle {{
      margin: 0;
      color: var(--qs-text-medium);
      font-size: 14px;
    }}
    .panel {{
      background: var(--qs-surface);
      border: 1px solid var(--qs-grid);
      border-radius: 8px;
      padding: 16px;
      margin-top: 16px;
    }}
    .chart {{
      padding: 0;
      overflow: hidden;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      font-weight: 600;
      line-height: 1.35;
      letter-spacing: 0;
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
    th, td {{
      border-bottom: 1px solid var(--qs-grid);
      padding: 10px 12px;
    }}
    td.number, th.number {{
      text-align: right;
      font-family: "JetBrains Mono", "IBM Plex Mono", Consolas, monospace;
      font-variant-numeric: tabular-nums;
    }}
    .profit {{
      color: var(--qs-profit);
    }}
    .loss {{
      color: var(--qs-loss);
    }}
    .limitations {{
      color: var(--qs-text-medium);
      border-left: 3px solid var(--qs-primary);
      background: var(--qs-surface-2);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{safe_title}</h1>
      <p class="subtitle">
        QuantSeras research report. Backtest outputs are historical diagnostics,
        not trading instructions.
      </p>
    </header>
    <section class="panel chart">{chart_html}</section>
    <section class="panel chart">
      <h2>Monthly Returns Heatmap</h2>
      {heatmap_html}
    </section>
    <section class="panel">
      <h2>Metrics</h2>
      {metrics_html}
    </section>
    <section class="panel">
      <h2>Trades</h2>
      {trades_html}
    </section>
    <section class="panel limitations">
      <h2>Limitations</h2>
      <p>
        {LIMITATIONS_TEXT}. Results depend on data quality, sample period,
        costs, slippage, and implementation assumptions.
      </p>
    </section>
  </main>
</body>
</html>
"""


def _render_metrics_table(metrics: dict[str, Any]) -> str:
    ordered_keys = [key for key in METRIC_LABELS if key in metrics]
    ordered_keys.extend(sorted(key for key in metrics if key not in METRIC_LABELS))
    rows = []
    for key in ordered_keys:
        value = metrics[key]
        css_class = _number_class(value)
        rows.append(
            "<tr>"
            f"<td>{escape(METRIC_LABELS.get(key, _labelize(key)))}</td>"
            f'<td class="number {css_class}">{escape(_format_metric(key, value))}</td>'
            "</tr>"
        )
    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def _render_trades_table(trades: pd.DataFrame, limit: int = 25) -> str:
    if trades.empty:
        return '<p class="subtitle">No trades were generated for this run.</p>'

    display_columns = [
        column
        for column in ["date", "close", "position_change", "cost"]
        if column in trades.columns
    ]
    preview = trades.loc[:, display_columns].head(limit)
    header = "".join(f"<th>{escape(_labelize(column))}</th>" for column in display_columns)
    rows = []
    for _, row in preview.iterrows():
        cells = []
        for column in display_columns:
            value = row[column]
            if column == "date":
                cells.append(f"<td>{escape(pd.Timestamp(value).strftime('%Y-%m-%d'))}</td>")
            else:
                cells.append(
                    f'<td class="number {_number_class(value)}">'
                    f"{escape(_format_cell(value))}</td>"
                )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    note = ""
    if len(trades) > limit:
        note = f'<p class="subtitle">Showing first {limit} of {len(trades)} trades.</p>'
    return (
        "<table><thead><tr>"
        + header
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + note
    )


def _format_metric(key: str, value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        if key in PERCENT_METRICS:
            return f"{value:.2%}"
        return f"{value:.4f}"
    return str(value)


def _format_cell(value: Any) -> str:
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _number_class(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value > 0:
            return "profit"
        if value < 0:
            return "loss"
    return ""


def _labelize(value: str) -> str:
    return value.replace("_", " ").title()
