"""JSON CLI over the public, guarded Task Manager API."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from importlib.resources import files
from pathlib import Path

from .contracts import TaskError
from .service import TaskManagerService


class TaskArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TaskError("validation_failed", message, hint=f"См. {self.prog} --help")


def _json_object(value: str) -> dict:
    try:
        result = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError("Требуется корректный JSON-объект") from exc
    if not isinstance(result, dict):
        raise argparse.ArgumentTypeError("Требуется JSON-объект")
    return result


def _resource_paths() -> dict[str, str]:
    root = files("orchestrator_task_manager").joinpath("resources")
    paths = {"contract": root.joinpath("docs", "contract.md"),
             "usage": root.joinpath("docs", "usage.md"),
             "example_skill": root.joinpath("examples", "skills", "orchestrator-task-manager", "SKILL.md")}
    for name, path in paths.items():
        if not path.is_file():
            raise TaskError("package_failure", f"Ресурс пакета отсутствует: {name}")
    return {name: str(path) for name, path in paths.items()}


# command -> (public API method, required flags, optional flags)
MUTATIONS = {
    "start": ("start_preparation", ("run_ref",), ()),
    "refine": ("refine_task_definition", (), ("objective", "problem_statement", "acceptance_criteria", "constraints", "evidence_refs")),
    "metadata": ("update_metadata", ("title",), ()),
    "artifact": ("attach_artifact", ("role", "ref"), ("path", "sha256", "metadata")),
    "execution-package": ("attach_execution_package", ("ref", "plan_sha256", "prepared_source_revision"), ("specification_sha256",)),
    "ready": ("mark_ready", (), ()),
    "claim": ("claim_task", ("worker_ref",), ("lease_seconds",)),
    "renew": ("renew_claim", ("claim_ref",), ("lease_seconds",)),
    "release": ("release_claim", ("claim_ref", "target_status", "reason"), ()),
    "recover": ("recover_expired_claim", (), ()),
    "run-link": ("link_workflow_run", ("run_ref", "relation"), ()),
    "blocker-add": ("add_blocker", ("blocker_type", "summary"), ("evidence_refs", "blocking")),
    "blocker-resolve": ("resolve_blocker", ("blocker_ref", "resolution"), ()),
    "decision": ("record_user_decision", ("decision_type", "value"), ("artifact_ref", "candidate_revision")),
    "transition": ("transition_status", ("to", "reason"), ()),
    "awaiting-acceptance": ("mark_awaiting_acceptance", (), ()),
    "complete": ("complete_task", ("completion_decision_ref",), ()),
    "accept": ("accept_task", ("candidate_revision", "completion_decision_ref"), ("artifact_ref",)),
    "cancel": ("cancel_task", ("reason",), ()),
    "archive": ("archive_task", ("reason",), ("actor_ref",)),
    "unarchive": ("unarchive_task", ("reason",), ()),
    "purge": ("purge_task", ("reason",), ("actor_ref",)),
    "external-link": ("register_external_link", ("tracker", "external_ref"), ()),
}
TRANSFER_COMMANDS = {"export": "export_state", "backup": "backup", "restore": "restore"}
ALIASES = {"target_status": "--to", "blocker_type": "--type", "acceptance_criteria": "--criterion",
           "constraints": "--constraint", "evidence_refs": "--evidence-ref"}
REPEATED = {"acceptance_criteria", "constraints", "evidence_refs"}


def _common(parser: argparse.ArgumentParser, *, child: bool = False) -> None:
    parser.add_argument("--project", type=Path, default=argparse.SUPPRESS if child else Path.cwd(),
                        help="Корень целевого проекта")
    parser.add_argument("--format", choices=("json", "table"), default=argparse.SUPPRESS if child else "json",
                        help="JSON для агента; table для list/show/summary")


def _filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--status", action="append")
    parser.add_argument("--type")
    parser.add_argument("--query")
    parser.add_argument("--include-archived", action="store_true")


def _parser() -> argparse.ArgumentParser:
    parser = TaskArgumentParser(description="Задачи Orchestrator: публичный API и защищённые переходы")
    _common(parser)
    commands = parser.add_subparsers(dest="command", required=True)

    def command(name: str) -> argparse.ArgumentParser:
        child = commands.add_parser(name)
        _common(child, child=True)
        return child

    create = command("create")
    for flag in ("title", "objective", "request"):
        create.add_argument("--" + flag, required=True)
    create.add_argument("--type", default="implementation")
    create.add_argument("--criterion", action="append", required=True)
    create.add_argument("--constraint", action="append", default=[])
    create.add_argument("--operation-id")
    create.add_argument("--event-context", type=_json_object)
    listing = command("list")
    _filters(listing)
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--cursor")
    _filters(command("summary"))
    command("show").add_argument("task_id")
    history = command("history")
    history.add_argument("task_id")
    history.add_argument("--after-sequence", type=int, default=0)
    document = command("document")
    document.add_argument("task_id")
    document.add_argument("--role", choices=("plan", "specification"), default="plan")
    for name in TRANSFER_COMMANDS:
        command(name).add_argument("source" if name == "restore" else "destination", type=Path)
    for name in ("validate", "resources", "api"):
        command(name)
    for name, (method, required, optional) in MUTATIONS.items():
        child = command(name)
        child.add_argument("task_id")
        child.add_argument("--expected-version", type=int, help="Явная версия; без неё читается текущая")
        fields = list(required + optional)
        signature = inspect.signature(getattr(TaskManagerService, method))
        for extra in ("operation_id", "event_context"):
            if extra in signature.parameters:
                fields.append(extra)
        child.set_defaults(method=method, fields=fields)
        for field in fields:
            flag = ALIASES.get(field, "--" + field.replace("_", "-"))
            options = {"dest": field, "required": field in required, "default": argparse.SUPPRESS}
            if field in REPEATED:
                options["action"] = "append"
            elif field in {"metadata", "event_context"}:
                options["type"] = _json_object
            elif field == "lease_seconds":
                options["type"] = int
            elif field == "blocking":
                flag = "--non-blocking"
                options["action"] = "store_false"
            child.add_argument(flag, **options)
    return parser


def _table(command: str, result) -> str:
    def clean(value) -> str:
        return " ".join(str(value).split())
    if command == "list":
        rows = [("ID", "STATUS", "TYPE", "TITLE")]
        rows.extend(tuple(clean(task.get(key, "")) for key in ("id", "status", "type", "title")) for task in result)
        widths = [max(len(row[index]) for row in rows) for index in range(3)]
        return "\n".join("  ".join(value.ljust(widths[index]) if index < 3 else value
                                  for index, value in enumerate(row)) for row in rows)
    if command == "show":
        fields = ("id", "version", "status", "type", "title", "objective", "active_run_ref", "active_claim", "archive")
        return "\n".join(f"{key}: {clean(result.get(key))}" for key in fields)
    if command == "summary":
        return " | ".join(f"{key}: {value}" for key, value in sorted(result["by_status"].items())) + (
            f"\ntotal: {result['total']} | archived_total: {result['archived_total']} | purged_total: {result['purged_total']}")
    return json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    try:
        args = _parser().parse_args(argv)
        if args.command == "resources":
            result = _resource_paths()
        elif args.command == "api":
            result = {name: str(inspect.signature(method)) for name, method in inspect.getmembers(TaskManagerService, inspect.isfunction)
                      if not name.startswith("_")}
        else:
            service = TaskManagerService(args.project)
            if args.command == "create":
                result = service.create_task(title=args.title, task_type=args.type, objective=args.objective,
                                             original_request=args.request, acceptance_criteria=args.criterion,
                                             constraints=args.constraint, operation_id=args.operation_id,
                                             event_context=args.event_context)
            elif args.command in {"list", "summary"}:
                filters = dict(statuses=set(args.status) if args.status else None, task_type=args.type,
                               query=args.query, include_archived=args.include_archived)
                result = service.list_tasks(**filters, limit=args.limit, cursor=args.cursor) if args.command == "list" else service.summary(**filters)
            elif args.command == "show":
                result = service.get_task(args.task_id)
            elif args.command == "history":
                result = service.get_history(args.task_id, args.after_sequence)
            elif args.command == "document":
                result = service.get_document(args.task_id, args.role)
            elif args.command == "validate":
                result = service.health_check()
            elif args.command in TRANSFER_COMMANDS:
                result = getattr(service, TRANSFER_COMMANDS[args.command])(
                    args.source if args.command == "restore" else args.destination)
            else:
                version = args.expected_version
                if version is None:
                    version = service.get_task(args.task_id)["version"]
                kwargs = {field: getattr(args, field) for field in args.fields if hasattr(args, field)}
                result = getattr(service, args.method)(args.task_id, version, **kwargs)
        healthy = args.command != "validate" or not result
        output = _table(args.command, result) if args.format == "table" and healthy else json.dumps(
            {"ok": healthy, "result": result}, ensure_ascii=False, indent=2)
        print(output)
        return 0 if healthy else 1
    except (TaskError, OSError) as exc:
        error = exc.as_dict() if isinstance(exc, TaskError) else {
            "code": "repository_failure", "message": str(exc), "details": {}}
        hints = {"task_version_conflict": "Прочитайте show и history, оцените изменение; не повторяйте мутацию вслепую.",
                 "operation_conflict": "Повторите прежние параметры, включая первоначальную --expected-version; для нового намерения используйте новый ID.",
                 "task_not_found": "Проверьте --project и ID через list --include-archived.",
                 "guard_failed": "Проверьте show и history; используйте профильную команду, не создавайте фиктивные свидетельства.",
                 "invalid_transition": "Проверьте текущий статус и контракт через resources."}
        if error["code"] in hints:
            error["details"].setdefault("hint", hints[error["code"]])
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
