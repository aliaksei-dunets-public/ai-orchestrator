from __future__ import annotations

import argparse
from pathlib import Path

from .health import format_json, format_text, run_health_checks
from .telemetry import TelemetryError, format_summary_text, load_events, summarize_events


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator")
    subcommands = parser.add_subparsers(dest="command", required=True)
    health = subcommands.add_parser("health", help="Run deterministic repository diagnostics")
    health.add_argument("--root", type=Path, default=Path.cwd())
    health.add_argument("--json", action="store_true", dest="as_json")
    health.add_argument("--strict", action="store_true")
    health.add_argument("--scope", choices=("all", "tasks"), default="all")
    telemetry = subcommands.add_parser(
        "telemetry",
        help="Summarize operational execution telemetry",
    )
    telemetry.add_argument(
        "--path",
        type=Path,
        default=Path(".orchestrator/telemetry/events.jsonl"),
    )
    telemetry.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "health":
        report = run_health_checks(args.root, scope=args.scope)
        print(format_json(report) if args.as_json else format_text(report))
        return report.exit_code(strict=args.strict)
    if args.command == "telemetry":
        try:
            summary = summarize_events(load_events(args.path))
        except TelemetryError as exc:
            print(f"TELEMETRY_ERROR {exc}")
            return 2
        if args.as_json:
            import json

            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_summary_text(summary))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
