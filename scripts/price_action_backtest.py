#!/usr/bin/env python3
import argparse
import datetime as dt
import importlib.util
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

RUNTIME_DEPENDENCIES = ("pandas", "numpy", "plotly")
CROSSOVER_STRATEGIES = {"sma_cross", "ema_cross"}
UTC = getattr(dt, "UTC", vars(dt.timezone)["utc"])


def emit_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def emit_error(error, field=None):
    payload = {
        "ok": False,
        "error": error,
    }
    if field is not None:
        payload["field"] = field
    emit_json(payload)


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        emit_error(message)
        raise SystemExit(2)


def has_module(name):
    return importlib.util.find_spec(name) is not None


def command_setup_check(args):
    runtime = {name: has_module(name) for name in RUNTIME_DEPENDENCIES}
    payload = {
        "python_ok": sys.version_info >= (3, 11),
        "runtime": runtime,
    }
    payload["ok"] = payload["python_ok"] and all(runtime.values())
    emit_json(payload)
    if args.strict and not payload["ok"]:
        return 1
    return 0


def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "run"


def make_run_dir(output_root, name, created_at):
    base_name = f"{created_at.strftime('%Y%m%dT%H%M%SZ')}-{slugify(name)}"
    run_dir = output_root / base_name
    suffix = 2
    while run_dir.exists():
        run_dir = output_root / f"{base_name}-{suffix}"
        suffix += 1
    return run_dir


def validate_bps_field(name, value):
    if not math.isfinite(value) or value < 0:
        emit_error(f"{name} must be finite and non-negative", field=name)
        return False
    return True


def command_init_run(args):
    data_path = Path(args.data_path)
    if not data_path.exists():
        emit_error(f"data path does not exist: {args.data_path}", field="data_path")
        return 1

    if args.strategy in CROSSOVER_STRATEGIES and args.fast_window >= args.slow_window:
        emit_error(
            f"fast_window must be less than slow_window for {args.strategy}",
            field="fast_window",
        )
        return 1

    if not validate_bps_field("fee_bps", args.fee_bps):
        return 1
    if not validate_bps_field("slippage_bps", args.slippage_bps):
        return 1

    created_at = dt.datetime.now(UTC)
    created_at_utc = created_at.isoformat().replace("+00:00", "Z")
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = make_run_dir(output_root, args.name, created_at)
    run_dir.mkdir(parents=True)

    config = {
        "name": args.name,
        "data_path": args.data_path,
        "strategy": args.strategy,
        "fast_window": args.fast_window,
        "slow_window": args.slow_window,
        "rsi_entry": args.rsi_entry,
        "rsi_exit": args.rsi_exit,
        "fee_bps": args.fee_bps,
        "slippage_bps": args.slippage_bps,
        "initial_equity": 1.0,
        "created_at_utc": created_at_utc,
    }
    config_path = run_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    emit_json(
        {
            "ok": True,
            "run_dir": str(run_dir),
            "config_path": str(config_path),
        }
    )
    return 0


def run_command(args):
    run_dir = Path(args.run_dir)
    config_path = run_dir / "config.json"

    if not run_dir.exists():
        emit_error(f"run directory does not exist: {args.run_dir}", field="run_dir")
        return 1
    if not config_path.exists():
        emit_error(f"config does not exist: {config_path}", field="run_dir")
        return 1

    try:
        from price_action_backtest.data import load_ohlcv
        from price_action_backtest.engine import run_backtest
        from price_action_backtest.indicators import add_indicators
        from price_action_backtest.signals import SignalSpec, build_signal

        config = json.loads(config_path.read_text(encoding="utf-8"))
        slow_window = int(config["slow_window"])
        fast_window = int(config["fast_window"])
        data = load_ohlcv(config["data_path"], min_rows=max(slow_window, 2))
        enriched = add_indicators(data, fast_window=fast_window, slow_window=slow_window)
        signal = build_signal(
            enriched,
            SignalSpec(
                strategy=config["strategy"],
                rsi_entry=float(config.get("rsi_entry", 30.0)),
                rsi_exit=float(config.get("rsi_exit", 70.0)),
            ),
        )
        result = run_backtest(
            enriched,
            signal,
            fee_bps=float(config.get("fee_bps", 0.0)),
            slippage_bps=float(config.get("slippage_bps", 0.0)),
        )
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        emit_error(str(exc))
        return 1

    result.equity.to_csv(run_dir / "equity.csv", index=False)
    result.trades.to_csv(run_dir / "trades.csv", index=False)
    (run_dir / "metrics.json").write_text(
        json.dumps(result.metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    emit_json(
        {
            "ok": True,
            "run_dir": str(run_dir),
            "metrics": result.metrics,
        }
    )
    return 0


def require_run_file(run_dir, name):
    path = run_dir / name
    if not path.exists():
        emit_error(f"required run output does not exist: {path}", field="run_dir")
        return None
    return path


def command_render_report(args):
    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        emit_error(f"run directory does not exist: {args.run_dir}", field="run_dir")
        return 1

    config_path = require_run_file(run_dir, "config.json")
    if config_path is None:
        return 1
    equity_path = require_run_file(run_dir, "equity.csv")
    if equity_path is None:
        return 1
    trades_path = require_run_file(run_dir, "trades.csv")
    if trades_path is None:
        return 1
    metrics_path = require_run_file(run_dir, "metrics.json")
    if metrics_path is None:
        return 1

    try:
        import pandas as pd

        from price_action_backtest.reports import render_html_report

        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("config.json must contain an object")
        equity = pd.read_csv(equity_path)
        trades = pd.read_csv(trades_path)
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if not isinstance(metrics, dict):
            raise ValueError("metrics.json must contain an object")
        title = str(config.get("name") or "Price Action Backtest Report")
        report_path = render_html_report(run_dir, title, equity, trades, metrics)
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        emit_error(str(exc))
        return 1

    emit_json(
        {
            "ok": True,
            "run_dir": str(run_dir),
            "report_path": report_path,
        }
    )
    return 0


def command_audit_output(args):
    from price_action_backtest.audit import audit_run

    result = audit_run(args.run_dir)
    emit_json(result)
    return 0 if result["ok"] else 1


def default_webull_output_path(args):
    symbol = slugify(args.symbol.upper())
    timespan = slugify(args.timespan.upper())
    return Path(args.output_root) / f"webull-{symbol}-{timespan}.csv"


def command_webull_fetch_bars(args):
    output_path = Path(args.output) if args.output else default_webull_output_path(args)
    try:
        from price_action_backtest.webull import (
            build_webull_data_client,
            fetch_stock_bars,
            format_webull_error,
            load_webull_settings,
            write_webull_bars_csv,
        )

        settings = load_webull_settings(args.env_file)
        data_client = build_webull_data_client(settings)
        payload = fetch_stock_bars(
            data_client,
            args.symbol,
            category=args.category,
            timespan=args.timespan,
            count=args.count,
            real_time_required=not args.include_latest,
            trading_sessions=args.trading_sessions,
            start_time=args.start_time_ms,
            end_time=args.end_time_ms,
        )
        written = write_webull_bars_csv(payload, output_path, min_rows=args.min_rows)
    except ImportError as exc:
        emit_error(
            "missing Webull SDK dependency; install with "
            "python3 -m pip install -e '.[runtime,webull]' "
            f"({exc})"
        )
        return 1
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        emit_error(format_webull_error(str(exc)))
        return 1
    except Exception as exc:
        emit_error(format_webull_error(f"Webull SDK error: {exc}"))
        return 1

    emit_json(
        {
            "ok": True,
            "symbol": args.symbol.strip().upper(),
            "category": args.category.strip().upper(),
            "timespan": args.timespan.strip().upper(),
            "count_requested": args.count,
            "output_path": str(written),
        }
    )
    return 0


def command_explain_target(args):
    output_path = (
        Path(args.output)
        if args.output
        else Path(args.output_root) / "target_explanation.json"
    )
    try:
        import pandas as pd

        from price_action_backtest.explainable_target import write_target_explanation

        data = pd.read_csv(args.data_path)
        written = write_target_explanation(
            data,
            output_path,
            symbol=args.symbol,
            lookback=args.lookback,
            horizon_days=args.horizon_days,
        )
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, ValueError) as exc:
        emit_error(str(exc))
        return 1

    emit_json(
        {
            "ok": True,
            "symbol": args.symbol.strip().upper(),
            "output_path": str(written),
        }
    )
    return 0


def command_render_target_report(args):
    output_path = (
        Path(args.output)
        if args.output
        else Path(args.output_root) / "target_report.html"
    )
    try:
        from price_action_backtest.target_reports import render_target_report

        report_path = render_target_report(args.payload_path, output_path)
    except ImportError as exc:
        emit_error(f"missing runtime dependency: {exc}")
        return 1
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        emit_error(str(exc))
        return 1

    emit_json(
        {
            "ok": True,
            "payload_path": args.payload_path,
            "report_path": str(report_path),
        }
    )
    return 0


def build_parser():
    parser = JsonArgumentParser(
        description="Price action backtest helper CLI."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        parser_class=JsonArgumentParser,
        required=True,
    )

    setup = subparsers.add_parser("setup-check", help="Check runtime setup.")
    setup.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when runtime dependencies are missing.",
    )
    setup.set_defaults(func=command_setup_check)

    init_run = subparsers.add_parser("init-run", help="Create a configured run folder.")
    init_run.add_argument("--name", required=True)
    init_run.add_argument("--data-path", required=True)
    init_run.add_argument(
        "--strategy",
        required=True,
        choices=("sma_cross", "ema_cross", "rsi_reversion", "macd_trend"),
    )
    init_run.add_argument("--fast-window", type=int, default=5)
    init_run.add_argument("--slow-window", type=int, default=20)
    init_run.add_argument("--rsi-entry", type=float, default=30.0)
    init_run.add_argument("--rsi-exit", type=float, default=70.0)
    init_run.add_argument("--fee-bps", type=float, default=0.0)
    init_run.add_argument("--slippage-bps", type=float, default=0.0)
    init_run.add_argument("--output-root", default="outputs")
    init_run.set_defaults(func=command_init_run)

    run = subparsers.add_parser("run", help="Run a configured backtest.")
    run.add_argument("--run-dir", required=True)
    run.set_defaults(func=run_command)

    report = subparsers.add_parser("render-report", help="Render a backtest HTML report.")
    report.add_argument("--run-dir", required=True)
    report.set_defaults(func=command_render_report)

    audit = subparsers.add_parser("audit-output", help="Audit a completed backtest run folder.")
    audit.add_argument("--run-dir", required=True)
    audit.set_defaults(func=command_audit_output)

    webull = subparsers.add_parser(
        "webull-fetch-bars",
        help="Fetch Webull historical bars as a local OHLCV CSV for backtesting.",
    )
    webull.add_argument("--symbol", required=True)
    webull.add_argument("--category", default="US_STOCK", choices=("US_STOCK", "US_ETF"))
    webull.add_argument("--timespan", default="D")
    webull.add_argument("--count", type=int, default=200)
    webull.add_argument(
        "--include-latest",
        action="store_true",
        help="Include latest market data instead of only completed bars.",
    )
    webull.add_argument("--trading-sessions")
    webull.add_argument("--start-time-ms", type=int)
    webull.add_argument("--end-time-ms", type=int)
    webull.add_argument("--min-rows", type=int, default=2)
    webull.add_argument("--env-file", default=".env")
    webull.add_argument("--output")
    webull.add_argument("--output-root", default="data/private")
    webull.set_defaults(func=command_webull_fetch_bars)

    explain = subparsers.add_parser(
        "explain-target",
        help="Build an explainable target price JSON artifact from OHLCV CSV data.",
    )
    explain.add_argument("--symbol", required=True)
    explain.add_argument("--data-path", required=True)
    explain.add_argument("--lookback", type=int, default=120)
    explain.add_argument("--horizon-days", type=int, default=126)
    explain.add_argument("--output")
    explain.add_argument("--output-root", default="outputs")
    explain.set_defaults(func=command_explain_target)

    target_report = subparsers.add_parser(
        "render-target-report",
        help="Render a target_explanation.json artifact as a standalone HTML report.",
    )
    target_report.add_argument("--payload-path", required=True)
    target_report.add_argument("--output")
    target_report.add_argument("--output-root", default="outputs")
    target_report.set_defaults(func=command_render_target_report)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
