#!/usr/bin/env python3
import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


RUNTIME_DEPENDENCIES = ("pandas", "numpy", "plotly")
CROSSOVER_STRATEGIES = {"sma_cross", "ema_cross"}


def emit_json(payload):
    print(json.dumps(payload, indent=2, sort_keys=True))


def has_module(name):
    return importlib.util.find_spec(name) is not None


def command_setup_check(args):
    runtime = {name: has_module(name) for name in RUNTIME_DEPENDENCIES}
    payload = {
        "python_ok": sys.version_info >= (3, 9),
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


def command_init_run(args):
    data_path = Path(args.data_path)
    if not data_path.exists():
        print(f"data path does not exist: {args.data_path}", file=sys.stderr)
        return 1

    if args.strategy in CROSSOVER_STRATEGIES and args.fast_window >= args.slow_window:
        print(
            "fast_window must be less than slow_window for "
            f"{args.strategy}",
            file=sys.stderr,
        )
        return 1

    created_at = datetime.now(timezone.utc)
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


def build_parser():
    parser = argparse.ArgumentParser(
        description="Price action backtest helper CLI."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

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

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
