from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .finalization import finalize_task, write_receipt
from .task_manager import (
    ExecutionSettings,
    TaskManager,
    TaskManagerError,
    validate_registry,
)


def _result(task: dict[str, Any]) -> dict[str, object]:
    return {
        "ok": True,
        "task": {
            **task,
            "context": f".orchestrator/tasks/{task['context']}",
        },
    }


def _print(payload: object, *, as_json: bool = True) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="orchestrator-task")
    parser.add_argument("--tasks-root", type=Path, default=Path.cwd() / ".orchestrator" / "tasks")
    commands = parser.add_subparsers(dest="command", required=True)

    register = commands.add_parser("register")
    register.add_argument("--context", required=True)

    finalize = commands.add_parser("finalize")
    finalize.add_argument("task_id")
    finalize.add_argument("--request", type=Path, required=True)
    finalize.add_argument("--repository-root", type=Path)

    listing = commands.add_parser("list")
    listing.add_argument("--json", action="store_true", dest="as_json")

    show = commands.add_parser("show")
    show.add_argument("task_id")
    show.add_argument("--json", action="store_true", dest="as_json")

    next_command = commands.add_parser("next")
    next_command.add_argument("--json", action="store_true", dest="as_json")

    claim = commands.add_parser("claim-next")
    claim.add_argument("--json", action="store_true", dest="as_json")
    claim.add_argument(
        "--mode",
        choices=("serial", "isolated_parallel"),
        default="serial",
    )
    claim.add_argument("--run-id")
    claim.add_argument("--max-workers", type=int, default=1)
    claim.add_argument("--worktree-root")
    claim.add_argument("--repository-root", type=Path)

    status = commands.add_parser("status")
    status.add_argument("task_id")
    status.add_argument("status")
    status.add_argument("--note")

    block = commands.add_parser("block")
    block.add_argument("task_id")
    block.add_argument("--note", required=True)

    for name in ("resume", "complete", "cancel"):
        command = commands.add_parser(name)
        command.add_argument("task_id")
        if name == "cancel":
            command.add_argument("--note")
        if name == "complete":
            command.add_argument("--commit-evidence")
            command.add_argument("--repository-root", type=Path)
            command.add_argument("--finalization-receipt", type=Path)

    assignment = commands.add_parser("assignment")
    assignment.add_argument("task_id")
    assignment.add_argument("--json", action="store_true", dest="as_json")

    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("task_id")
    cleanup.add_argument(
        "--outcome",
        choices=("completed", "cancelled", "failed"),
        required=True,
    )
    cleanup.add_argument("--repository-root", type=Path)

    validate = commands.add_parser("validate")
    validate.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manager = TaskManager(args.tasks_root)
    try:
        if args.command == "register":
            _print(_result(manager.register(args.context)))
        elif args.command == "finalize":
            repository = (
                args.repository_root.resolve()
                if args.repository_root is not None
                else manager.tasks_root.parents[1].resolve()
            )
            request = json.loads(args.request.read_text(encoding="utf-8"))
            if not isinstance(request, dict):
                raise ValueError("finalization request must be an object")
            task = manager.show(args.task_id)
            receipt = finalize_task(
                project_root=repository,
                task_id=args.task_id,
                context_path=manager.tasks_root / str(task["context"]),
                checkpoint_path=manager.checkpoint_path(args.task_id),
                changed_paths=request.get("changed_paths", []),
                documentation_dispositions=request.get(
                    "documentation_dispositions", []
                ),
                knowledge_proposal=request.get("knowledge_proposal"),
                memory_candidates=request.get("memory_candidates", []),
            )
            destination = manager.tasks_root / "finalization" / f"{args.task_id}.json"
            write_receipt(destination, receipt)
            _print(
                {
                    "ok": True,
                    "task_id": args.task_id,
                    "receipt": destination.as_posix(),
                    "result": receipt.to_dict(),
                }
            )
        elif args.command == "list":
            tasks = manager.list_tasks()
            _print({"ok": True, "tasks": tasks} if args.as_json else "\n".join(f"{t['id']} {t['status']} {t['title']}" for t in tasks), as_json=args.as_json)
        elif args.command == "show":
            task = manager.show(args.task_id)
            _print(_result(task) if args.as_json else f"{task['id']} {task['status']} {task['title']}", as_json=args.as_json)
        elif args.command == "next":
            task = manager.next_task()
            _print(_result(task) if args.as_json else f"{task['id']} {task['title']}", as_json=args.as_json)
        elif args.command == "claim-next":
            settings = ExecutionSettings(
                mode=args.mode,
                run_id=args.run_id,
                max_workers=args.max_workers,
                worktree_root=args.worktree_root,
            )
            task = manager.claim_next(
                settings,
                repository_root=args.repository_root,
            )
            _print(_result(task) if args.as_json else f"{task['id']} {task['context']}", as_json=args.as_json)
        elif args.command == "status":
            _print(_result(manager.set_status(args.task_id, args.status, args.note)))
        elif args.command == "block":
            _print(_result(manager.block(args.task_id, args.note)))
        elif args.command == "resume":
            _print(_result(manager.resume(args.task_id)))
        elif args.command == "complete":
            _print(
                _result(
                    manager.complete(
                        args.task_id,
                        commit_evidence=args.commit_evidence,
                        repository_root=args.repository_root,
                        finalization_receipt=args.finalization_receipt,
                    )
                )
            )
        elif args.command == "cancel":
            _print(_result(manager.cancel(args.task_id, args.note)))
        elif args.command == "assignment":
            assignment = manager.assignment(args.task_id)
            payload = {"ok": True, "task_id": args.task_id, "assignment": assignment}
            _print(
                payload
                if args.as_json
                else json.dumps(assignment, ensure_ascii=False, sort_keys=True),
                as_json=args.as_json,
            )
        elif args.command == "cleanup":
            removed = manager.cleanup_assignment(
                args.task_id,
                repository_root=args.repository_root,
                outcome=args.outcome,
            )
            _print(
                {
                    "ok": True,
                    "task_id": args.task_id,
                    "removed": removed,
                    "preserved": not removed,
                }
            )
        elif args.command == "validate":
            issues = validate_registry(args.tasks_root)
            payload = {
                "ok": not issues,
                "findings": [
                    {
                        "code": item.code,
                        "severity": item.severity,
                        "message": item.message,
                        "path": item.path.as_posix() if item.path else None,
                    }
                    for item in issues
                ],
            }
            _print(payload if args.as_json else ("\n".join(item.message for item in issues) or "Task Registry is valid"), as_json=args.as_json)
            return 0 if not issues else 4
        return 0
    except TaskManagerError as exc:
        _print(exc.to_dict())
        return exc.exit_code
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _print(
            {
                "ok": False,
                "error": {
                    "code": type(exc).__name__.upper(),
                    "message": str(exc),
                },
            }
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
