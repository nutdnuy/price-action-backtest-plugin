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
