import json
import subprocess
import sys
from pathlib import Path

from price_action_backtest.audit import audit_run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "price_action_backtest.py"


def run_cli(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def write_complete_run(
    run_dir,
    *,
    fee_bps=5,
    slippage_bps=2,
    trade_count=2,
    max_drawdown=-0.12,
):
    run_dir.mkdir()
    (run_dir / "config.json").write_text(
        json.dumps(
            {
                "name": "Audit Demo",
                "fee_bps": fee_bps,
                "slippage_bps": slippage_bps,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps(
            {
                "max_drawdown": max_drawdown,
                "trade_count": trade_count,
                "total_return": 0.08,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "equity.csv").write_text(
        "date,close,strategy_equity,drawdown\n2024-01-01,100,1.0,0.0\n",
        encoding="utf-8",
    )
    (run_dir / "trades.csv").write_text(
        "date,close,position_change,cost\n2024-01-02,101,1,0.001\n",
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html>report</html>\n", encoding="utf-8")


def test_audit_run_passes_when_required_files_exist(tmp_path):
    run_dir = tmp_path / "run"
    write_complete_run(run_dir)

    result = audit_run(run_dir)

    assert result == {
        "ok": True,
        "errors": [],
        "warnings": [],
    }


def test_audit_run_flags_missing_files_and_zero_cost_warning(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.json").write_text(
        json.dumps({"fee_bps": 0, "slippage_bps": 0}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "metrics.json").write_text(
        json.dumps({"trade_count": 1, "max_drawdown": -0.1}) + "\n",
        encoding="utf-8",
    )

    result = audit_run(run_dir)

    assert result["ok"] is False
    assert result["errors"] == [
        "missing required output file: equity.csv",
        "missing required output file: trades.csv",
        "missing required output file: report.html",
    ]
    assert result["warnings"] == [
        "fee_bps and slippage_bps are both zero; results ignore trading costs."
    ]


def test_audit_run_warns_for_zero_trades_and_extreme_drawdown(tmp_path):
    run_dir = tmp_path / "run"
    write_complete_run(run_dir, trade_count=0, max_drawdown=-0.85)

    result = audit_run(run_dir)

    assert result["ok"] is True
    assert (
        "trade_count is zero; review signal parameters and confirm a no-trade run is expected."
        in result["warnings"]
    )
    assert (
        "max_drawdown is -85.00%; review risk assumptions before sharing this result."
        in result["warnings"]
    )


def test_audit_output_cli_emits_json_and_fails_when_errors_exist(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = run_cli("audit-output", "--run-dir", str(run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "missing required output file: config.json" in payload["errors"]


def test_audit_output_cli_returns_zero_for_warning_only_run(tmp_path):
    run_dir = tmp_path / "run"
    write_complete_run(run_dir, fee_bps=0, slippage_bps=0)

    result = run_cli("audit-output", "--run-dir", str(run_dir))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["errors"] == []
    assert payload["warnings"] == [
        "fee_bps and slippage_bps are both zero; results ignore trading costs."
    ]
