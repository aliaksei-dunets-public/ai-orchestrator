from __future__ import annotations

import argparse
from pathlib import Path

from .health import format_json, format_text, run_health_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator")
    subcommands = parser.add_subparsers(dest="command", required=True)
    health = subcommands.add_parser("health", help="Run deterministic repository diagnostics")
    health.add_argument("--root", type=Path, default=Path.cwd())
    health.add_argument("--json", action="store_true", dest="as_json")
    health.add_argument("--strict", action="store_true")
    health.add_argument("--scope", choices=("all", "tasks"), default="all")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "health":
        report = run_health_checks(args.root, scope=args.scope)
        print(format_json(report) if args.as_json else format_text(report))
        return report.exit_code(strict=args.strict)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
