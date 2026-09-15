"""Small JSON CLI for task creation and inspection."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import files
from pathlib import Path

from .task_manager import TaskError, TaskManagerService


def _resource_paths() -> dict[str, str]:
    root = files("orchestrator_task_manager").joinpath("resources")
    paths = {
        "contract": root.joinpath("docs", "contract.md"),
        "usage": root.joinpath("docs", "usage.md"),
        "example_skill": root.joinpath("examples", "skills", "orchestrator-task-manager", "SKILL.md"),
    }
    for name, path in paths.items():
        if not path.is_file():
            raise TaskError("package_failure", f"Ресурс пакета отсутствует: {name}")
    return {name: str(path) for name, path in paths.items()}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Задачи Orchestrator")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--title", required=True)
    create.add_argument("--type", default="implementation")
    create.add_argument("--objective", required=True)
    create.add_argument("--request", required=True)
    create.add_argument("--criterion", action="append", required=True)
    create.add_argument("--constraint", action="append", default=[])
    listing = commands.add_parser("list")
    listing.add_argument("--status", action="append")
    listing.add_argument("--type")
    listing.add_argument("--query")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--cursor")
    listing.add_argument("--include-archived", action="store_true")
    show = commands.add_parser("show")
    show.add_argument("task_id")
    history = commands.add_parser("history")
    history.add_argument("task_id")
    history.add_argument("--after-sequence", type=int, default=0)
    export = commands.add_parser("export")
    export.add_argument("destination", type=Path)
    backup = commands.add_parser("backup")
    backup.add_argument("destination", type=Path)
    restore = commands.add_parser("restore")
    restore.add_argument("source", type=Path)
    archive = commands.add_parser("archive")
    archive.add_argument("task_id")
    archive.add_argument("--reason", required=True)
    archive.add_argument("--actor-ref")
    archive.add_argument("--operation-id")
    unarchive = commands.add_parser("unarchive")
    unarchive.add_argument("task_id")
    unarchive.add_argument("--reason", required=True)
    unarchive.add_argument("--operation-id")
    purge = commands.add_parser("purge")
    purge.add_argument("task_id")
    purge.add_argument("--reason", required=True)
    purge.add_argument("--actor-ref")
    purge.add_argument("--operation-id")
    commands.add_parser("validate")
    commands.add_parser("resources")
    args = parser.parse_args(argv)
    try:
        if args.command == "resources":
            result = _resource_paths()
        else:
            service = TaskManagerService(args.project)
        if args.command == "create":
            result = service.create_task(
                title=args.title, task_type=args.type, objective=args.objective,
                original_request=args.request, acceptance_criteria=args.criterion,
                constraints=args.constraint,
            )
        elif args.command == "list":
            result = service.list_tasks(
                statuses=set(args.status) if args.status else None,
                task_type=args.type, query=args.query, limit=args.limit,
                cursor=args.cursor,
                include_archived=args.include_archived,
            )
        elif args.command == "show":
            result = service.get_task(args.task_id)
        elif args.command == "history":
            result = service.get_history(args.task_id, args.after_sequence)
        elif args.command == "validate":
            result = service.health_check()
        elif args.command == "export":
            result = service.export_state(args.destination)
        elif args.command == "backup":
            result = service.backup(args.destination)
        elif args.command == "restore":
            result = service.restore(args.source)
        elif args.command == "archive":
            task = service.get_task(args.task_id)
            result = service.archive_task(
                args.task_id, task["version"], reason=args.reason,
                actor_ref=args.actor_ref, operation_id=args.operation_id,
            )
        elif args.command == "unarchive":
            task = service.get_task(args.task_id)
            result = service.unarchive_task(
                args.task_id, task["version"], reason=args.reason, operation_id=args.operation_id,
            )
        elif args.command == "purge":
            task = service.get_task(args.task_id)
            result = service.purge_task(
                args.task_id, task["version"], reason=args.reason,
                actor_ref=args.actor_ref, operation_id=args.operation_id,
            )
        healthy = args.command != "validate" or not result
        print(json.dumps({"ok": healthy, "result": result}, ensure_ascii=False, indent=2))
        return 0 if healthy else 1
    except (TaskError, OSError) as exc:
        error = exc.as_dict() if isinstance(exc, TaskError) else {
            "code": "repository_failure", "message": str(exc), "details": {}
        }
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
