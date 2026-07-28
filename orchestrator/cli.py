from __future__ import annotations

import argparse
import json
from pathlib import Path

from .health import format_json, format_text, run_health_checks
from .telemetry import TelemetryError, format_summary_text, load_events, summarize_events
from . import context_cli, knowledge_cli, memory_cli


class CliInputError(ValueError):
    pass


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliInputError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = JsonArgumentParser(prog="orchestrator")
    subcommands = parser.add_subparsers(
        dest="command", required=True, parser_class=JsonArgumentParser
    )
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
    memory = subcommands.add_parser("memory", help="Curate project memory")
    memory_cli.configure(memory)
    knowledge = subcommands.add_parser("knowledge", help="Curate project knowledge")
    knowledge_cli.configure(knowledge)
    context = subcommands.add_parser("context", help="Build a bounded context pack")
    context_cli.configure(context)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except CliInputError as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {"code": "INVALID_ARGUMENTS", "message": str(exc)},
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 2
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
            print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_summary_text(summary))
        return 0
    if args.command in {"memory", "knowledge", "context"}:
        try:
            handler = {
                "memory": memory_cli.run,
                "knowledge": knowledge_cli.run,
                "context": context_cli.run,
            }[args.command]
            payload = handler(args)
            print(json.dumps({"ok": True, "result": payload}, ensure_ascii=False, indent=2, sort_keys=True))
            return 0
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "code": type(exc).__name__.upper(),
                            "message": str(exc),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
