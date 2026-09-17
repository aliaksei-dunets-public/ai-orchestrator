"""Минимальный MCP stdio-адаптер над публичным TaskManagerService.

Адаптер не владеет состоянием и не содержит SQL: один экземпляр получает один
фиксированный project root, а вся предметная логика остаётся в сервисе.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .contracts import TaskError
from .service import TaskManagerService


SUPPORTED_PROTOCOL_VERSIONS = ("2026-07-28", "2025-11-25", "2025-03-26", "2024-11-05")
SERVER_VERSION = "0.1.0"


def _schema(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "object", "properties": properties, "additionalProperties": False,
    }
    if required:
        result["required"] = list(required)
    return result


STRING = {"type": "string"}
INTEGER = {"type": "integer"}
BOOLEAN = {"type": "boolean"}
STRING_ARRAY = {"type": "array", "items": STRING}
OBJECT = {"type": "object"}
TASK_TYPE = {"type": "string", "enum": ["implementation", "analysis", "investigation", "incident", "exploration"]}
TASK_STATUS = {"type": "string", "enum": ["created", "preparing", "ready", "active", "awaiting_input", "blocked", "awaiting_acceptance", "completed", "cancelled"]}
ARTIFACT_ROLE = {"type": "string", "enum": ["specification", "plan", "plan_review", "execution_package", "implementation", "code_review", "testing", "documentation", "readiness", "acceptance_package", "user_acceptance", "completion_decision"]}
EVENT_CONTEXT = {
    "type": "object", "additionalProperties": False,
    "properties": {name: STRING for name in ("actor_ref", "source", "correlation_id", "run_ref")},
}


def _validate_schema(value: Any, schema: dict[str, Any], path: str = "$") -> None:
    """Validate tool arguments against the published JSON Schema subset.

    The adapter deliberately keeps this validator local: MCP clients must see
    the same strict contract that the server enforces, without adding a
    dependency merely for checking the small schemas used by these tools.
    """
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise TaskError("validation_failed", "Ожидался объект", path=path)
        properties = schema.get("properties", {})
        missing = [name for name in schema.get("required", []) if name not in value]
        if missing:
            raise TaskError("validation_failed", "Отсутствуют обязательные аргументы", path=f"{path}.{missing[0]}")
        if schema.get("additionalProperties") is False:
            unknown = [name for name in value if name not in properties]
            if unknown:
                raise TaskError("validation_failed", "Неизвестный аргумент MCP-инструмента", path=f"{path}.{unknown[0]}")
        for name, item in value.items():
            if name in properties:
                _validate_schema(item, properties[name], f"{path}.{name}")
    elif expected == "array":
        if not isinstance(value, list):
            raise TaskError("validation_failed", "Ожидался список", path=path)
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                _validate_schema(item, item_schema, f"{path}[{index}]")
    elif expected == "string":
        if not isinstance(value, str):
            raise TaskError("validation_failed", "Ожидалась строка", path=path)
    elif expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise TaskError("validation_failed", "Ожидалось целое число", path=path)
    elif expected == "boolean":
        if type(value) is not bool:
            raise TaskError("validation_failed", "Ожидалось boolean-значение", path=path)
    else:
        raise TaskError("validation_failed", "Неподдерживаемый тип схемы MCP", path=path)
    if "enum" in schema and value not in schema["enum"]:
        raise TaskError("validation_failed", "Значение не входит в допустимый enum", path=path)


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]
    read_only: bool = False
    idempotent: bool = False

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
            "annotations": {
                "readOnlyHint": self.read_only,
                "destructiveHint": not self.read_only,
                "idempotentHint": self.idempotent,
            },
        }


def _common_read_properties() -> dict[str, Any]:
    return {
        "task_id": STRING,
        "expected_version": INTEGER,
        "operation_id": STRING,
        "event_context": EVENT_CONTEXT,
    }


class TaskMCPServer:
    """Serve one project over MCP stdio."""

    def __init__(self, project_root: Path) -> None:
        root = Path(project_root).resolve(strict=False)
        if not root.is_dir():
            raise TaskError("validation_failed", "project_root должен быть существующим каталогом", path=str(root))
        self.project_root = root
        self.service = TaskManagerService(root)
        self.initialize_received = False
        self.initialized = False
        self.tools = self._build_tools()

    def _build_tools(self) -> dict[str, MCPTool]:
        tools: list[MCPTool] = []

        def add(name: str, description: str, properties: dict[str, Any], handler: Callable[[dict[str, Any]], Any],
                required: tuple[str, ...] = (), *, read_only: bool = False, idempotent: bool = False) -> None:
            tools.append(MCPTool(name, description, _schema(properties, required), handler, read_only, idempotent))

        add("task_get", "Прочитать одну карточку задачи.", {"task_id": STRING},
            lambda a: self.service.get_task(a["task_id"]), ("task_id",), read_only=True)
        add("task_list", "Получить страницу задач с фильтрами.", {
            "status": {"type": "array", "items": TASK_STATUS}, "type": TASK_TYPE, "query": STRING, "limit": INTEGER,
            "cursor": STRING, "include_archived": BOOLEAN,
        }, lambda a: self.service.list_tasks(
            statuses=set(a["status"]) if a.get("status") else None, task_type=a.get("type"),
            query=a.get("query"), limit=a.get("limit", 100), cursor=a.get("cursor"),
            include_archived=a.get("include_archived", False)), read_only=True)
        add("task_summary", "Получить агрегированную сводку задач.", {
            "status": {"type": "array", "items": TASK_STATUS}, "type": TASK_TYPE, "query": STRING, "include_archived": BOOLEAN,
        }, lambda a: self.service.summary(
            statuses=set(a["status"]) if a.get("status") else None, task_type=a.get("type"),
            query=a.get("query"), include_archived=a.get("include_archived", False)), read_only=True)
        add("task_history", "Прочитать историю событий задачи.", {"task_id": STRING, "after_sequence": INTEGER},
            lambda a: self.service.get_history(a["task_id"], a.get("after_sequence", 0)), ("task_id",), read_only=True)
        add("task_document", "Прочитать проверенный plan или legacy specification задачи.",
            {"task_id": STRING, "role": {"type": "string", "enum": ["plan", "specification"]}}, lambda a: self.service.get_document(a["task_id"], a.get("role", "plan")),
            ("task_id",), read_only=True)
        add("task_get_claim", "Прочитать активный claim задачи.", {"task_id": STRING},
            lambda a: self.service.get_claim(a["task_id"]), ("task_id",), read_only=True)
        add("task_list_executable", "Получить готовые задачи development для исполнения.", {"limit": INTEGER},
            lambda a: self.service.list_executable_tasks(a.get("limit", 100)), read_only=True)
        add("task_health_check", "Проверить целостность Task Manager без исправлений.", {},
            lambda a: self.service.health_check(), read_only=True)

        add("task_create", "Создать задачу в статусе created.", {
            "title": STRING, "type": TASK_TYPE, "objective": STRING, "original_request": STRING,
            "acceptance_criteria": STRING_ARRAY, "constraints": STRING_ARRAY, "target_workflow": STRING,
            "handoff_mode": STRING, "operation_id": STRING, "event_context": EVENT_CONTEXT,
        }, lambda a: self.service.create_task(
            title=a["title"], task_type=a["type"], objective=a["objective"],
            original_request=a["original_request"], acceptance_criteria=a["acceptance_criteria"],
            constraints=a.get("constraints"), target_workflow=a.get("target_workflow", "development"),
            handoff_mode=a.get("handoff_mode", "deferred"), operation_id=a.get("operation_id"),
            event_context=a.get("event_context")),
            ("title", "type", "objective", "original_request", "acceptance_criteria"), idempotent=True)

        def mutation(method: str, properties: dict[str, Any], required: tuple[str, ...], *, idempotent: bool = False) -> None:
            def invoke(args: dict[str, Any]) -> Any:
                task_id = args.pop("task_id")
                expected_version = args.pop("expected_version")
                return getattr(self.service, method)(task_id, expected_version, **args)
            add("task_" + method.removesuffix("_task"), method, properties, invoke, required,
                idempotent=idempotent)

        common = {"task_id": STRING, "expected_version": INTEGER}
        mutation("start_preparation", {**common, "run_ref": STRING, "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "run_ref"), idempotent=True)
        mutation("refine_task_definition", {**common, "objective": STRING, "problem_statement": STRING,
                 "acceptance_criteria": STRING_ARRAY, "constraints": STRING_ARRAY, "evidence_refs": STRING_ARRAY},
                 ("task_id", "expected_version"))
        mutation("update_metadata", {**common, "title": STRING}, ("task_id", "expected_version"))
        mutation("attach_artifact", {**common, "role": ARTIFACT_ROLE, "ref": STRING, "path": STRING, "sha256": STRING, "metadata": OBJECT},
                 ("task_id", "expected_version", "role", "ref"))
        mutation("attach_execution_package", {**common, "ref": STRING, "plan_sha256": STRING,
                 "prepared_source_revision": STRING, "specification_sha256": STRING},
                 ("task_id", "expected_version", "ref", "plan_sha256", "prepared_source_revision"))
        mutation("mark_ready", {**common, "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version"), idempotent=True)
        mutation("claim_task", {**common, "worker_ref": STRING, "lease_seconds": INTEGER,
                 "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "worker_ref"), idempotent=True)
        mutation("renew_claim", {**common, "claim_ref": STRING, "lease_seconds": INTEGER},
                 ("task_id", "expected_version", "claim_ref"))
        mutation("release_claim", {**common, "claim_ref": STRING, "target_status": {"type": "string", "enum": ["ready", "preparing", "blocked", "awaiting_input"]}, "reason": STRING},
                 ("task_id", "expected_version", "claim_ref", "target_status", "reason"))
        mutation("recover_expired_claim", common, ("task_id", "expected_version"))
        mutation("link_workflow_run", {**common, "run_ref": STRING, "relation": {"type": "string", "enum": ["active", "finished"]},
                 "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "run_ref", "relation"), idempotent=True)
        mutation("add_blocker", {**common, "blocker_type": STRING, "summary": STRING,
                 "evidence_refs": STRING_ARRAY, "blocking": BOOLEAN}, ("task_id", "expected_version", "blocker_type", "summary"))
        mutation("resolve_blocker", {**common, "blocker_ref": STRING, "resolution": STRING},
                 ("task_id", "expected_version", "blocker_ref", "resolution"))
        mutation("record_user_decision", {**common, "decision_type": STRING, "value": STRING,
                 "artifact_ref": STRING, "candidate_revision": STRING, "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "decision_type", "value"), idempotent=True)
        mutation("transition_status", {**common, "to": TASK_STATUS, "reason": STRING,
                 "operation_id": STRING, "event_context": EVENT_CONTEXT}, ("task_id", "expected_version", "to", "reason"), idempotent=True)
        mutation("mark_awaiting_acceptance", common, ("task_id", "expected_version"))
        mutation("complete_task", {**common, "completion_decision_ref": STRING,
                 "operation_id": STRING, "event_context": EVENT_CONTEXT}, ("task_id", "expected_version", "completion_decision_ref"), idempotent=True)
        mutation("accept_task", {**common, "candidate_revision": STRING, "completion_decision_ref": STRING,
                 "artifact_ref": STRING, "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "candidate_revision", "completion_decision_ref"), idempotent=True)
        mutation("cancel_task", {**common, "reason": STRING}, ("task_id", "expected_version", "reason"))
        mutation("archive_task", {**common, "reason": STRING, "actor_ref": STRING,
                 "operation_id": STRING, "event_context": EVENT_CONTEXT}, ("task_id", "expected_version", "reason"), idempotent=True)
        mutation("unarchive_task", {**common, "reason": STRING, "operation_id": STRING, "event_context": EVENT_CONTEXT},
                 ("task_id", "expected_version", "reason"), idempotent=True)
        mutation("purge_task", {**common, "reason": STRING, "actor_ref": STRING, "operation_id": STRING},
                 ("task_id", "expected_version", "reason"), idempotent=True)
        mutation("register_external_link", {**common, "tracker": STRING, "external_ref": STRING},
                 ("task_id", "expected_version", "tracker", "external_ref"))

        add("task_export", "Экспортировать согласованный JSON-снимок состояния.", {"destination": STRING},
            lambda a: self.service.export_state(self._project_path(a["destination"], "destination")), ("destination",))
        add("task_backup", "Создать проверенную SQLite-копию состояния.", {"destination": STRING},
            lambda a: self.service.backup(self._project_path(a["destination"], "destination")), ("destination",))
        add("task_restore", "Проверить и атомарно восстановить SQLite-копию.", {"source": STRING},
            lambda a: self.service.restore(self._project_path(a["source"], "source")), ("source",))
        return {tool.name: tool for tool in tools}

    def _project_path(self, value: str, field: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise TaskError("validation_failed", f"Требуется путь {field}")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self.project_root / candidate
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.project_root):
            raise TaskError("validation_failed", f"Путь {field} выходит за project_root", path=str(resolved))
        return resolved

    @staticmethod
    def _error(code: int, message: str, request_id: Any = None, data: Any = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}

    @staticmethod
    def _tool_result(value: Any, *, is_error: bool = False) -> dict[str, Any]:
        payload = {"error": value} if is_error else (value if isinstance(value, dict) else {"value": value})
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False, sort_keys=True)}],
            "structuredContent": payload,
            "isError": is_error,
        }

    def handle(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            if not isinstance(message, dict) or "id" not in message or message.get("id") is None:
                return None
            return self._error(-32600, "Invalid Request", message.get("id"))
        request_id = message.get("id")
        has_request_id = "id" in message and request_id is not None
        method = message["method"]
        params = message.get("params", {})
        if params is None:
            params = {}
        if not isinstance(params, dict):
            if not has_request_id:
                return None
            return self._error(-32602, "params must be an object", request_id)
        if method == "notifications/initialized":
            if self.initialize_received:
                self.initialized = True
            return None
        if not has_request_id:
            return None
        if method == "initialize":
            requested = params.get("protocolVersion")
            if not isinstance(requested, str):
                return self._error(-32602, "protocolVersion is required", request_id)
            self.initialize_received = True
            version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "orchestrator-task-manager", "version": SERVER_VERSION},
                "instructions": "Task Manager state is scoped to the fixed project root. Mutations require expected_version.",
            }}
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if not self.initialized:
            return self._error(-32002, "Server is not initialized", request_id)
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": {"tools": [tool.definition() for tool in self.tools.values()]}}
        if method != "tools/call":
            return self._error(-32601, "Method not found", request_id)
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in self.tools:
            return self._error(-32602, "Unknown tool", request_id, {"name": name})
        if not isinstance(arguments, dict):
            return self._error(-32602, "Tool arguments must be an object", request_id)
        tool = self.tools[name]
        try:
            _validate_schema(arguments, tool.input_schema, "$.arguments")
            # Do not mutate the request object while removing common parameters.
            result = tool.handler(dict(arguments))
        except TaskError as exc:
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": self._tool_result(exc.as_dict(), is_error=True)}
        except (TypeError, ValueError, KeyError) as exc:
            error = TaskError("validation_failed", "Некорректные аргументы MCP-инструмента", field=str(exc))
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": self._tool_result(error.as_dict(), is_error=True)}
        except OSError as exc:
            error = TaskError("repository_failure", "Ошибка файловой операции Task Manager", os_error=str(exc))
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": self._tool_result(error.as_dict(), is_error=True)}
        except Exception as exc:  # Keep one malformed tool call from killing the stdio session.
            print(f"MCP adapter internal error: {type(exc).__name__}", file=sys.stderr, flush=True)
            error = TaskError("repository_failure", "Внутренняя ошибка MCP-адаптера")
            return {"jsonrpc": "2.0", "id": request_id,
                    "result": self._tool_result(error.as_dict(), is_error=True)}
        return {"jsonrpc": "2.0", "id": request_id, "result": self._tool_result(result)}

    def serve(self, input_stream: Any = None, output_stream: Any = None) -> None:
        input_stream = sys.stdin if input_stream is None else input_stream
        output_stream = sys.stdout if output_stream is None else output_stream
        if hasattr(input_stream, "reconfigure"):
            input_stream.reconfigure(encoding="utf-8", newline=None)
        if hasattr(output_stream, "reconfigure"):
            output_stream.reconfigure(encoding="utf-8", newline="\n")
        for line in input_stream:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                response = self._error(-32700, "Parse error")
            else:
                response = self.handle(message)
            if response is not None:
                output_stream.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                output_stream.flush()


def main(argv: list[str] | None = None) -> int:
    # argparse prints localized help before the stdio server starts. Configure
    # UTF-8 first so `--help` is reliable on Windows code pages as well.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Task Manager MCP stdio server")
    parser.add_argument("--project", type=Path, required=True, help="Фиксированный корень проекта")
    args = parser.parse_args(argv)
    try:
        TaskMCPServer(args.project).serve()
    except (TaskError, OSError) as exc:
        error = exc.as_dict() if isinstance(exc, TaskError) else {
            "code": "repository_failure", "message": str(exc), "details": {},
        }
        print(json.dumps({"ok": False, "error": error}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
