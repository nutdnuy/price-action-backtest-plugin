import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "price_action_backtest.py"
SAMPLE_DATA = ROOT / "templates" / "sample-ohlcv.csv"


def run_cli(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_setup_check_emits_json_status():
    result = run_cli("setup-check")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["python_ok"] is (sys.version_info >= (3, 11))
    assert set(payload["runtime"]) == {"pandas", "numpy", "plotly"}
    assert payload["ok"] == (payload["python_ok"] and all(payload["runtime"].values()))


def test_init_run_creates_run_folder_and_config(tmp_path):
    result = run_cli(
        "init-run",
        "--name",
        "SMA demo",
        "--data-path",
        str(SAMPLE_DATA),
        "--strategy",
        "sma_cross",
        "--fast-window",
        "5",
        "--slow-window",
        "20",
        "--fee-bps",
        "5",
        "--slippage-bps",
        "2",
        "--output-root",
        str(tmp_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    run_dir = Path(payload["run_dir"])
    config_path = run_dir / "config.json"

    assert payload["ok"] is True
    assert run_dir.exists()
    assert run_dir.parent == tmp_path
    assert run_dir.name.endswith("-sma-demo")
    assert config_path.exists()

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["name"] == "SMA demo"
    assert config["data_path"] == str(SAMPLE_DATA)
    assert config["strategy"] == "sma_cross"
    assert config["fast_window"] == 5
    assert config["slow_window"] == 20


def test_init_run_missing_data_path_returns_json_error(tmp_path):
    missing_path = tmp_path / "missing.csv"
    result = run_cli(
        "init-run",
        "--name",
        "Missing data demo",
        "--data-path",
        str(missing_path),
        "--strategy",
        "sma_cross",
        "--fast-window",
        "5",
        "--slow-window",
        "20",
        "--output-root",
        str(tmp_path / "outputs"),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "data_path"
    assert "does not exist" in payload["error"]


def test_init_run_invalid_crossover_windows_returns_json_error(tmp_path):
    result = run_cli(
        "init-run",
        "--name",
        "Bad windows",
        "--data-path",
        str(SAMPLE_DATA),
        "--strategy",
        "sma_cross",
        "--fast-window",
        "20",
        "--slow-window",
        "5",
        "--output-root",
        str(tmp_path),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "fast_window"
    assert "fast_window" in payload["error"]


def test_init_run_negative_fee_returns_json_error(tmp_path):
    result = run_cli(
        "init-run",
        "--name",
        "Bad fee",
        "--data-path",
        str(SAMPLE_DATA),
        "--strategy",
        "sma_cross",
        "--fast-window",
        "5",
        "--slow-window",
        "20",
        "--fee-bps",
        "-1",
        "--output-root",
        str(tmp_path),
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "fee_bps"
    assert "fee_bps" in payload["error"]


def test_unsupported_command_returns_json_error():
    result = run_cli("unknown-command")

    assert result.returncode == 2
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "invalid choice" in payload["error"]


def test_run_command_writes_metrics(tmp_path):
    init_result = run_cli(
        "init-run",
        "--name",
        "SMA demo",
        "--data-path",
        str(SAMPLE_DATA),
        "--strategy",
        "sma_cross",
        "--fast-window",
        "5",
        "--slow-window",
        "20",
        "--fee-bps",
        "5",
        "--slippage-bps",
        "2",
        "--output-root",
        str(tmp_path),
    )
    assert init_result.returncode == 0, init_result.stderr
    run_dir = Path(json.loads(init_result.stdout)["run_dir"])

    run_result = run_cli("run", "--run-dir", str(run_dir))

    assert run_result.returncode == 0, run_result.stderr
    payload = json.loads(run_result.stdout)
    metrics_path = run_dir / "metrics.json"

    assert payload["ok"] is True
    assert payload["run_dir"] == str(run_dir)
    assert (run_dir / "equity.csv").exists()
    assert (run_dir / "trades.csv").exists()
    assert metrics_path.exists()

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert payload["metrics"] == metrics
    assert "total_return" in metrics
    assert "max_drawdown" in metrics
    assert "trade_count" in metrics


def test_run_missing_run_dir_returns_json_error(tmp_path):
    missing_run_dir = tmp_path / "missing-run"

    result = run_cli("run", "--run-dir", str(missing_run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "run_dir"
    assert "run directory does not exist" in payload["error"]


def test_run_missing_config_returns_json_error(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()

    result = run_cli("run", "--run-dir", str(run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["field"] == "run_dir"
    assert "config does not exist" in payload["error"]


def test_run_invalid_config_json_returns_json_error(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "config.json").write_text("{bad json", encoding="utf-8")

    result = run_cli("run", "--run-dir", str(run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert "Expecting property name" in payload["error"]


def test_run_missing_data_path_in_config_returns_json_error(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    missing_data_path = tmp_path / "missing.csv"
    config = {
        "data_path": str(missing_data_path),
        "strategy": "sma_cross",
        "fast_window": 1,
        "slow_window": 2,
        "fee_bps": 0,
        "slippage_bps": 0,
    }
    (run_dir / "config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_cli("run", "--run-dir", str(run_dir))

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert str(missing_data_path) in payload["error"]


def test_explain_target_cli_writes_target_json(tmp_path):
    output_path = tmp_path / "target_explanation.json"

    result = run_cli(
        "explain-target",
        "--symbol",
        "AAPL",
        "--data-path",
        str(SAMPLE_DATA),
        "--lookback",
        "20",
        "--horizon-days",
        "126",
        "--output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "ok": True,
        "symbol": "AAPL",
        "output_path": str(output_path),
    }
    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["symbol"] == "AAPL"
    assert saved["horizon_days"] == 126
    assert saved["target_price"] == saved["price_bands"]["p50"]
