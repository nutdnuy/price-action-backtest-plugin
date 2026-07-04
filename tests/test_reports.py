import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from price_action_backtest.reports import render_html_report

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "price_action_backtest.py"


def sample_equity():
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=4, freq="D"),
            "close": [100.0, 102.0, 101.0, 105.0],
            "strategy_equity": [1.0, 1.02, 1.01, 1.05],
            "buy_hold_equity": [1.0, 1.02, 1.01, 1.05],
            "drawdown": [0.0, 0.0, -0.0098039216, 0.0],
        }
    )


def sample_trades():
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-04")],
            "close": [102.0, 105.0],
            "position_change": [1.0, -1.0],
            "cost": [0.001, 0.001],
        }
    )


def sample_metrics():
    return {
        "total_return": 0.05,
        "buy_hold_return": 0.05,
        "annualized_return": 2.0,
        "annualized_volatility": 0.18,
        "sharpe": 1.25,
        "max_drawdown": -0.01,
        "trade_count": 2,
        "total_cost": 0.002,
    }


def run_cli(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def write_run_outputs(run_dir):
    run_dir.mkdir()
    (run_dir / "config.json").write_text(
        json.dumps({"name": "SMA Demo"}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sample_equity().to_csv(run_dir / "equity.csv", index=False)
    sample_trades().to_csv(run_dir / "trades.csv", index=False)
    (run_dir / "metrics.json").write_text(
        json.dumps(sample_metrics(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_render_html_report_writes_quantseras_report(tmp_path):
    report_path = render_html_report(
        tmp_path,
        "SMA Demo Report",
        sample_equity(),
        sample_trades(),
        sample_metrics(),
    )

    assert report_path == str(tmp_path / "report.html")
    html = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "SMA Demo Report" in html
    assert "#121212" in html
    assert "#69F0AE" in html
    assert "#00E676" in html
    assert "#FF5252" in html
    assert "#03DAC6" in html
    assert "Historical performance does not guarantee future performance" in html
    assert "Total Return" in html
    assert "Plotly.newPlot" in html


def test_render_report_cli_reads_run_outputs_and_emits_report_path(tmp_path):
    run_dir = tmp_path / "run"
    write_run_outputs(run_dir)

    result = run_cli("render-report", "--run-dir", str(run_dir))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    report_path = run_dir / "report.html"
    assert payload == {
        "ok": True,
        "report_path": str(report_path),
        "run_dir": str(run_dir),
    }
    assert report_path.exists()


def test_render_report_missing_required_output_returns_json_error(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.json").write_text(
        json.dumps({"name": "Missing outputs"}) + "\n",
        encoding="utf-8",
    )

    result = run_cli("render-report", "--run-dir", str(run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "run_dir"
    assert "equity.csv" in payload["error"]
