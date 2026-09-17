"""Детерминированный жизненный цикл задач и общие защитные условия."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from .contracts import (
    ARTIFACT_ROLES, TERMINAL, TASK_TYPES, RETENTION_MONTHS, TaskError,
    _now, _utc, _stamp, _task_id, _version, _limit, _required,
    _event_context, _add_months,
)
from .repository import SQLiteTaskRepository
from .storage_transfer import StorageTransfer
from .diagnostics import health_check


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_digest(path: Path, code: str) -> str:
    try:
        return _sha256(path)
    except OSError as exc:
        raise TaskError(code, "Файл артефакта недоступен", path=str(path), os_error=str(exc)) from exc


def _string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TaskError("validation_failed", f"{field} должен быть списком строк")
    return [_required(item, field) for item in value]


class TaskManagerService:
    def __init__(self, project_root: Path, *, clock: Callable[[], datetime] = _now,
                 acceptance_required: bool = True) -> None:
        self.repository = SQLiteTaskRepository(project_root)
        self.clock = clock
        self.acceptance_required = acceptance_required

    @staticmethod
    def _operation_fingerprint(*parts: Any) -> str:
        body = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _mutate(self, task_id: str, expected_version: int, event_type: str,
                change: Callable[[dict[str, Any]], dict[str, Any]], *,
                operation_id: str | None = None, operation_payload: Any = None,
                event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        _task_id(task_id)
        _version(expected_version)
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        context = _event_context(event_context, operation_id=operation_id)
        fingerprint = self._operation_fingerprint(event_type, task_id, expected_version, operation_payload, context)
        return self.repository.mutate(
            task_id, expected_version, event_type, change, _stamp(self.clock()),
            operation_id=operation_id, fingerprint=fingerprint, event_context=context,
        )

    def create_task(self, *, title: str, task_type: str, objective: str,
                    original_request: str, acceptance_criteria: list[str],
                    constraints: list[str] | None = None, target_workflow: str = "development",
                    handoff_mode: str = "deferred", operation_id: str | None = None,
                    event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(handoff_mode, str) or handoff_mode not in {"immediate", "deferred"}:
            raise TaskError("validation_failed", "Неизвестный режим передачи")
        if not isinstance(task_type, str) or task_type not in TASK_TYPES:
            raise TaskError("validation_failed", "Неизвестный тип задачи")
        if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
            raise TaskError("validation_failed", "Нужен хотя бы один критерий приёмки")
        criteria = [
            {"id": f"AC-{index:02d}", "text": _required(text, "acceptance_criteria")}
            for index, text in enumerate(acceptance_criteria, 1)
        ]
        constraints = [] if constraints is None else constraints
        if not isinstance(constraints, list):
            raise TaskError("validation_failed", "constraints должен быть списком")
        snapshot = {
            "title": _required(title, "title"), "type": _required(task_type, "task_type"),
            "status": "created", "original_request": _required(original_request, "original_request"),
            "objective": _required(objective, "objective"), "problem_statement": None,
            "acceptance_criteria": criteria,
            "constraints": [_required(item, "constraint") for item in constraints],
            "definition_version": 1, "target_workflow": _required(target_workflow, "target_workflow"),
            "handoff_mode": handoff_mode, "prepared_source_revision": None,
            "terminal_at": None, "archive": None,
            "artifacts": {}, "workflow_runs": [], "active_run_ref": None,
            "active_claim": None, "blockers": [], "user_decisions": [], "external_links": [],
            "resume_status": None, "pending_decision_count": None,
        }
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        fingerprint = self._operation_fingerprint("task_created", snapshot)
        context = _event_context(event_context, operation_id=operation_id)
        return self.repository.create(
            snapshot, _stamp(self.clock()), operation_id=operation_id, fingerprint=fingerprint,
            event_context=context,
        )

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self.repository.get(task_id)

    def list_tasks(self, *, statuses: set[str] | None = None, task_type: str | None = None,
                   query: str | None = None, limit: int | None = 100,
                   cursor: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.repository.list(statuses=statuses, task_type=task_type, query=query,
                                    limit=limit, cursor=cursor, include_archived=include_archived)

    def get_history(self, task_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        return self.repository.history(task_id, after_sequence)

    def summary(self, *, statuses: set[str] | None = None, task_type: str | None = None,
                query: str | None = None, include_archived: bool = False) -> dict[str, Any]:
        return self.repository.summary(statuses=statuses, task_type=task_type, query=query,
                                       include_archived=include_archived)

    def get_document(self, task_id: str, role: str) -> str:
        if not isinstance(role, str) or role not in {"specification", "plan"}:
            raise TaskError("validation_failed", "Можно читать только plan или legacy specification")
        task = self.get_task(task_id)
        artifact = task["artifacts"].get(role)
        if not artifact or not artifact.get("path"):
            raise TaskError("task_not_found", "Документ задачи не найден")
        path = self._artifact_path(task_id, artifact["path"])
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise TaskError("guard_failed", "Документ задачи недоступен", path=str(path), os_error=str(exc)) from exc
        if hashlib.sha256(content).hexdigest() != artifact.get("sha256"):
            raise TaskError("guard_failed", "Документ изменился после привязки")
        try:
            return content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError as exc:
            raise TaskError("validation_failed", "Документ должен быть UTF-8", path=str(path)) from exc

    def get_claim(self, task_id: str) -> dict[str, Any] | None:
        return self.get_task(task_id)["active_claim"]

    def export_state(self, destination: Path) -> dict[str, Any]:
        return StorageTransfer(self.repository).export_state(destination)

    def backup(self, destination: Path) -> dict[str, Any]:
        return StorageTransfer(self.repository).backup(destination)

    def restore(self, source: Path) -> dict[str, Any]:
        return StorageTransfer(self.repository).restore(source)

    @staticmethod
    def _database_version(path: Path) -> int:
        return StorageTransfer._database_version(path)

    @staticmethod
    def _validate_database(path: Path) -> None:
        return StorageTransfer._validate_database(path)

    def health_check(self) -> list[dict[str, str]]:
        return health_check(self.repository, self._ready_guard)

    def list_executable_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        _limit(limit)
        if limit is None:
            raise TaskError("validation_failed", "Для списка исполнения требуется limit")
        return [task for task in self.list_tasks(statuses={"ready"}, limit=None)
                if task["target_workflow"] == "development"][:limit]

    def start_preparation(self, task_id: str, expected_version: int, run_ref: str,
                          *, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        run_ref = _required(run_ref, "run_ref")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "created":
                raise TaskError("invalid_transition", "Подготовка начинается только из created")
            task["status"] = "preparing"
            task["active_run_ref"] = run_ref
            task["workflow_runs"].append(run_ref)
            return {"from": "created", "to": "preparing", "run_ref": run_ref}

        return self._mutate(task_id, expected_version, "preparation_started", change,
                            operation_id=operation_id, operation_payload={"run_ref": run_ref},
                            event_context=event_context)

    def refine_task_definition(self, task_id: str, expected_version: int, *, objective: str | None = None,
                               problem_statement: str | None = None,
                               acceptance_criteria: list[str] | None = None,
                               constraints: list[str] | None = None,
                               evidence_refs: list[str] | None = None) -> dict[str, Any]:
        if all(value is None for value in (objective, problem_statement, acceptance_criteria, constraints, evidence_refs)):
            raise TaskError("validation_failed", "Нет изменений определения")
        if evidence_refs is not None:
            evidence_refs = _string_list(evidence_refs, "evidence_refs")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] not in {"created", "preparing", "ready"}:
                raise TaskError("invalid_transition", "Определение нельзя уточнить в текущем статусе")
            if task["status"] == "ready":
                task["status"] = "preparing"
                task["artifacts"].clear()
                task["prepared_source_revision"] = None
            if objective is not None:
                task["objective"] = _required(objective, "objective")
            if problem_statement is not None:
                task["problem_statement"] = _required(problem_statement, "problem_statement")
            if acceptance_criteria is not None:
                if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
                    raise TaskError("validation_failed", "Нужны критерии приёмки")
                task["acceptance_criteria"] = [
                    {"id": f"AC-{index:02d}", "text": _required(text, "acceptance_criteria")}
                    for index, text in enumerate(acceptance_criteria, 1)
                ]
            if constraints is not None:
                if not isinstance(constraints, list):
                    raise TaskError("validation_failed", "constraints должен быть списком")
                task["constraints"] = [_required(item, "constraint") for item in constraints]
            task["definition_version"] += 1
            return {"definition_version": task["definition_version"], "evidence_refs": evidence_refs or []}

        return self._mutate(task_id, expected_version, "definition_refined", change)

    def update_metadata(self, task_id: str, expected_version: int, *, title: str) -> dict[str, Any]:
        title = _required(title, "title")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя изменить")
            task["title"] = title
            return {"title": title}

        return self._mutate(task_id, expected_version, "metadata_updated", change)

    def _artifact_path(self, task_id: str, path: str) -> Path:
        _task_id(task_id)
        path = _required(path, "path")
        root = self.repository.project_root / ".orchestrator/tasks" / task_id
        candidate = self.repository.project_root / path
        try:
            resolved_root = root.resolve(strict=False)
            if not resolved_root.is_relative_to(self.repository.project_root) or not candidate.resolve(strict=False).is_relative_to(resolved_root):
                raise TaskError("validation_failed", "Артефакт должен находиться в каталоге задачи")
            if candidate.is_symlink() or not candidate.is_file():
                raise TaskError("validation_failed", "Файл артефакта отсутствует или является ссылкой")
        except OSError as exc:
            raise TaskError("validation_failed", "Путь артефакта недоступен", path=path) from exc
        return candidate

    def attach_artifact(self, task_id: str, expected_version: int, *, role: str, ref: str,
                        path: str | None = None, sha256: str | None = None,
                        metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(role, str) or role not in ARTIFACT_ROLES:
            raise TaskError("validation_failed", "Неизвестная роль артефакта")
        ref = _required(ref, "ref")
        metadata = {} if metadata is None else metadata
        if not isinstance(metadata, dict):
            raise TaskError("validation_failed", "metadata должен быть объектом")
        if role in {"specification", "plan"}:
            if not path or not sha256:
                raise TaskError("validation_failed", "Для документа требуются путь и хеш")
            candidate = self._artifact_path(task_id, path)
            if _artifact_digest(candidate, "validation_failed") != sha256:
                raise TaskError("validation_failed", "Хеш документа не совпадает")
        artifact = {"ref": ref, "path": path, "sha256": sha256, "metadata": metadata}

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "К конечной задаче нельзя добавить артефакт")
            if role in {"specification", "plan", "plan_review", "execution_package"} and task["status"] not in {
                "created", "preparing", "ready"
            }:
                raise TaskError("invalid_transition", "Артефакт подготовки нельзя менять во время исполнения")
            if role in {"plan_review", "execution_package"} and task["status"] != "preparing":
                raise TaskError("invalid_transition", "Одобрение и пакет добавляются только при подготовке")
            task["artifacts"][role] = artifact
            if role in {"specification", "plan"}:
                task["artifacts"].pop("plan_review", None)
                task["artifacts"].pop("execution_package", None)
                task["prepared_source_revision"] = None
                if task["status"] == "ready":
                    task["status"] = "preparing"
            return {"role": role, "ref": ref}

        return self._mutate(task_id, expected_version, "artifact_attached", change)

    def attach_execution_package(self, task_id: str, expected_version: int, *, ref: str,
                                 plan_sha256: str, prepared_source_revision: str,
                                 specification_sha256: str | None = None) -> dict[str, Any]:
        metadata = {
            "plan_sha256": _required(plan_sha256, "plan_sha256"),
            "prepared_source_revision": _required(prepared_source_revision, "prepared_source_revision"),
        }
        # Legacy callers may still provide this value. It is retained as metadata
        # but is no longer required for readiness.
        if specification_sha256 is not None:
            metadata["specification_sha256"] = _required(specification_sha256, "specification_sha256")
        return self.attach_artifact(
            task_id, expected_version, role="execution_package", ref=ref,
            metadata=metadata,
        )

    def _ready_guard(self, task: dict[str, Any]) -> None:
        if any(item["status"] == "open" and item["blocking"] for item in task["blockers"]):
            raise TaskError("guard_failed", "Есть открытый блокирующий фактор")
        artifacts = task["artifacts"]
        for role in ("plan", "plan_review", "execution_package"):
            if role not in artifacts:
                raise TaskError("guard_failed", f"Нет артефакта {role}")
        document = artifacts["plan"]
        try:
            candidate = self._artifact_path(task["id"], document["path"])
        except TaskError as exc:
            raise TaskError("guard_failed", "Документ plan недоступен") from exc
        if _artifact_digest(candidate, "guard_failed") != document["sha256"]:
            raise TaskError("guard_failed", "Документ plan изменился")
        plan_hash = artifacts["plan"]["sha256"]
        review = artifacts["plan_review"]["metadata"]
        package = artifacts["execution_package"]["metadata"]
        for binding in (review, package):
            if binding.get("plan_sha256") != plan_hash:
                raise TaskError("guard_failed", "Одобрение или пакет привязаны к другой версии plan")
        if review.get("status") != "approved":
            raise TaskError("guard_failed", "План не одобрен")
        _required(package.get("prepared_source_revision"), "prepared_source_revision")

    def mark_ready(self, task_id: str, expected_version: int, *, operation_id: str | None = None,
                   event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "preparing":
                raise TaskError("invalid_transition", "В ready можно перейти только из preparing")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Сначала завершите запуск подготовки")
            self._ready_guard(task)
            task["status"] = "ready"
            task["prepared_source_revision"] = task["artifacts"]["execution_package"]["metadata"]["prepared_source_revision"]
            return {"from": "preparing", "to": "ready"}

        return self._mutate(task_id, expected_version, "status_changed", change,
                            operation_id=operation_id, operation_payload={"to": "ready"},
                            event_context=event_context)

    def claim_task(self, task_id: str, expected_version: int, *, worker_ref: str,
                   lease_seconds: int = 900, operation_id: str | None = None,
                   event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        worker_ref = _required(worker_ref, "worker_ref")
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 30 <= lease_seconds <= 86400:
            raise TaskError("validation_failed", "lease_seconds должен быть в диапазоне 30..86400")
        now = _utc(self.clock())
        claim_ref = f"CLAIM-{task_id}-{uuid.uuid4().hex[:12]}"

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "ready" or task["active_claim"] is not None:
                raise TaskError("task_not_ready", "Задача уже занята или не готова")
            self._ready_guard(task)
            task["status"] = "active"
            task["active_claim"] = {
                "ref": claim_ref, "worker_ref": worker_ref,
                "lease_until": _stamp(now + timedelta(seconds=lease_seconds)),
                "execution_package_ref": task["artifacts"]["execution_package"]["ref"],
            }
            return {"from": "ready", "to": "active", "claim_ref": claim_ref, "worker_ref": worker_ref}

        return self._mutate(task_id, expected_version, "task_claimed", change,
                            operation_id=operation_id,
                            operation_payload={"worker_ref": worker_ref, "lease_seconds": lease_seconds},
                            event_context=event_context)

    def renew_claim(self, task_id: str, expected_version: int, *, claim_ref: str,
                    lease_seconds: int = 900) -> dict[str, Any]:
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 30 <= lease_seconds <= 86400:
            raise TaskError("validation_failed", "Некорректная длительность lease")
        now = _utc(self.clock())

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            if not claim or claim["ref"] != claim_ref:
                raise TaskError("claim_conflict", "Закрепление не найдено")
            if _utc(datetime.fromisoformat(claim["lease_until"])) <= now:
                raise TaskError("claim_expired", "Срок закрепления истёк")
            claim["lease_until"] = _stamp(now + timedelta(seconds=lease_seconds))
            return {"claim_ref": claim_ref, "lease_until": claim["lease_until"]}

        return self._mutate(task_id, expected_version, "claim_renewed", change)

    def release_claim(self, task_id: str, expected_version: int, *, claim_ref: str,
                      target_status: str, reason: str) -> dict[str, Any]:
        reason = _required(reason, "reason")
        if not isinstance(target_status, str) or target_status not in {"ready", "preparing", "blocked", "awaiting_input"}:
            raise TaskError("validation_failed", "Недопустимый статус после освобождения")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            current_status = task["status"]
            if current_status not in {"active", "blocked", "awaiting_input"} or not claim or claim["ref"] != claim_ref:
                raise TaskError("claim_conflict", "Закрепление не принадлежит задаче")
            if current_status in {"blocked", "awaiting_input"} and target_status != current_status:
                raise TaskError("invalid_transition", "При паузе сохраняйте её статус до возобновления")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Сначала завершите связанный запуск графа")
            if target_status == "ready":
                self._ready_guard(task)
            if target_status == "blocked" and current_status != "blocked" and not any(
                item["blocking"] and item["status"] == "open" for item in task["blockers"]
            ):
                raise TaskError("guard_failed", "Для blocked нужен открытый блокер")
            task["active_claim"] = None
            task["status"] = target_status
            if current_status == "active" and target_status in {"blocked", "awaiting_input"}:
                task["resume_status"] = "ready"
            if target_status == "preparing":
                task["artifacts"].pop("plan_review", None)
                task["artifacts"].pop("execution_package", None)
                task["prepared_source_revision"] = None
            return {"claim_ref": claim_ref, "to": target_status, "reason": reason}

        return self._mutate(task_id, expected_version, "claim_released", change)

    def recover_expired_claim(self, task_id: str, expected_version: int) -> dict[str, Any]:
        now = _utc(self.clock())

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            if not claim or _utc(datetime.fromisoformat(claim["lease_until"])) > now:
                raise TaskError("claim_conflict", "Нет истёкшего закрепления")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Связанный запуск требует ручной проверки")
            if task["status"] == "active":
                self._ready_guard(task)
            task["active_claim"] = None
            if task["status"] == "active":
                task["status"] = "ready"
            return {"claim_ref": claim["ref"], "to": task["status"]}

        return self._mutate(task_id, expected_version, "claim_recovered", change)

    def link_workflow_run(self, task_id: str, expected_version: int, *, run_ref: str,
                          relation: str, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        run_ref = _required(run_ref, "run_ref")
        if not isinstance(relation, str) or relation not in {"active", "finished"}:
            raise TaskError("validation_failed", "Неизвестное отношение запуска")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if relation == "active":
                if task["status"] not in {"preparing", "active"} or task["active_run_ref"]:
                    raise TaskError("guard_failed", "Нельзя привязать второй активный запуск")
                task["active_run_ref"] = run_ref
                if run_ref not in task["workflow_runs"]:
                    task["workflow_runs"].append(run_ref)
            elif task["active_run_ref"] != run_ref:
                raise TaskError("guard_failed", "Активный запуск не совпадает")
            else:
                task["active_run_ref"] = None
            return {"run_ref": run_ref, "relation": relation}

        return self._mutate(task_id, expected_version, "workflow_run_linked", change,
                            operation_id=operation_id, operation_payload={"run_ref": run_ref, "relation": relation},
                            event_context=event_context)

    def add_blocker(self, task_id: str, expected_version: int, *, blocker_type: str,
                    summary: str, evidence_refs: list[str] | None = None,
                    blocking: bool = True) -> dict[str, Any]:
        blocker_type = _required(blocker_type, "blocker_type")
        summary = _required(summary, "summary")
        evidence_refs = _string_list(evidence_refs, "evidence_refs")
        if type(blocking) is not bool:
            raise TaskError("validation_failed", "blocking должен быть boolean")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя блокировать")
            blocker_id = f"BLOCK-{len(task['blockers']) + 1:02d}"
            task["blockers"].append({"id": blocker_id, "type": blocker_type, "summary": summary,
                                     "blocking": blocking, "status": "open",
                                     "evidence_refs": evidence_refs})
            if blocking and task["status"] != "blocked":
                task["resume_status"] = "ready" if task["status"] == "active" else task["status"]
                task["status"] = "blocked"
            return {"blocker_ref": blocker_id, "blocking": blocking}

        return self._mutate(task_id, expected_version, "blocker_added", change)

    def resolve_blocker(self, task_id: str, expected_version: int, *, blocker_ref: str,
                        resolution: str) -> dict[str, Any]:
        resolution = _required(resolution, "resolution")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            blocker = next((item for item in task["blockers"] if item["id"] == blocker_ref), None)
            if not blocker or blocker["status"] != "open":
                raise TaskError("validation_failed", "Открытый блокер не найден")
            blocker["status"] = "resolved"
            blocker["resolution"] = resolution
            return {"blocker_ref": blocker_ref, "resolution": resolution}

        return self._mutate(task_id, expected_version, "blocker_resolved", change)

    def record_user_decision(self, task_id: str, expected_version: int, *, decision_type: str,
                             value: str, artifact_ref: str | None = None,
                             candidate_revision: str | None = None,
                             operation_id: str | None = None,
                             event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        decision_type = _required(decision_type, "decision_type")
        value = _required(value, "value")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя изменить")
            if decision_type == "acceptance" and task["status"] != "awaiting_acceptance":
                raise TaskError("invalid_transition", "Решение о приёмке фиксируется только на этапе приёмки")
            decision = {"type": decision_type, "value": value,
                        "artifact_ref": artifact_ref, "candidate_revision": candidate_revision}
            task["user_decisions"].append(decision)
            return decision

        return self._mutate(task_id, expected_version, "user_decision_recorded", change,
                            operation_id=operation_id,
                            operation_payload={"decision_type": decision_type, "value": value,
                                                "artifact_ref": artifact_ref, "candidate_revision": candidate_revision},
                            event_context=event_context)

    def transition_status(self, task_id: str, expected_version: int, *, to: str,
                          reason: str, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            before = task["status"]
            if to == "awaiting_input" and before in {"preparing", "active"}:
                task["resume_status"] = "ready" if before == "active" else before
                task["pending_decision_count"] = len(task["user_decisions"])
            elif to == "blocked" and before in {"preparing", "ready", "active"}:
                if not any(item["blocking"] and item["status"] == "open" for item in task["blockers"]):
                    raise TaskError("guard_failed", "Для blocked нужен открытый блокер")
                task["resume_status"] = "ready" if before == "active" else before
            elif before in {"awaiting_input", "blocked"} and to == task["resume_status"]:
                if task["active_claim"] or task["active_run_ref"]:
                    raise TaskError("guard_failed", "Сначала завершите запуск и освободите закрепление")
                if before == "blocked" and any(
                    item["blocking"] and item["status"] == "open" for item in task["blockers"]
                ):
                    raise TaskError("guard_failed", "Не все блокеры разрешены")
                if before == "awaiting_input" and len(task["user_decisions"]) <= (task["pending_decision_count"] or 0):
                    raise TaskError("guard_failed", "Нет решения пользователя")
                if to == "ready":
                    self._ready_guard(task)
                task["pending_decision_count"] = None
                task["resume_status"] = None
            else:
                raise TaskError("invalid_transition", f"Переход {before} → {to} запрещён")
            task["status"] = to
            return {"from": before, "to": to, "reason": reason}

        return self._mutate(task_id, expected_version, "status_changed", change,
                            operation_id=operation_id, operation_payload={"to": to, "reason": reason},
                            event_context=event_context)

    def mark_awaiting_acceptance(self, task_id: str, expected_version: int) -> dict[str, Any]:
        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "active":
                raise TaskError("invalid_transition", "Приёмка возможна только после исполнения")
            readiness = task["artifacts"].get("readiness", {}).get("metadata", {})
            if readiness.get("status") != "ready" or "acceptance_package" not in task["artifacts"]:
                raise TaskError("guard_failed", "Нет свидетельства готовности или пакета приёмки")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Активный запуск ещё не завершён")
            task["status"] = "awaiting_acceptance"
            task["active_claim"] = None
            return {"from": "active", "to": "awaiting_acceptance"}

        return self._mutate(task_id, expected_version, "status_changed", change)

    def complete_task(self, task_id: str, expected_version: int, *, completion_decision_ref: str,
                      operation_id: str | None = None,
                      event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        completion_decision_ref = _required(completion_decision_ref, "completion_decision_ref")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            self._complete(task, completion_decision_ref)
            return {"to": "completed", "completion_decision_ref": completion_decision_ref}

        return self._mutate(task_id, expected_version, "task_completed", change,
                            operation_id=operation_id,
                            operation_payload={"completion_decision_ref": completion_decision_ref},
                            event_context=event_context)

    def _complete(self, task: dict[str, Any], completion_decision_ref: str) -> None:
        allowed = {"awaiting_acceptance"} if self.acceptance_required else {"active", "awaiting_acceptance"}
        if task["status"] not in allowed:
            raise TaskError("invalid_transition", "Задача не находится в состоянии завершения")
        if any(item["blocking"] and item["status"] == "open" for item in task["blockers"]):
            raise TaskError("guard_failed", "Открытый блокер мешает завершению")
        readiness = task["artifacts"].get("readiness", {}).get("metadata", {})
        if readiness.get("status") != "ready":
            raise TaskError("guard_failed", "Нет подтверждённой готовности")
        if self.acceptance_required:
            revision = readiness.get("candidate_revision")
            if not revision or not any(
                decision["type"] == "acceptance" and decision["value"] == "approved"
                and decision["candidate_revision"] == revision for decision in task["user_decisions"]
            ):
                raise TaskError("guard_failed", "Нет приёмки текущей ревизии пользователем")
        if task["active_run_ref"]:
            raise TaskError("guard_failed", "Запуск графа ещё активен")
        task["status"] = "completed"
        task["active_claim"] = None
        task["terminal_at"] = _stamp(self.clock())
        task["artifacts"]["completion_decision"] = {"ref": completion_decision_ref}

    def accept_task(self, task_id: str, expected_version: int, *, candidate_revision: str,
                    completion_decision_ref: str, artifact_ref: str | None = None,
                    operation_id: str | None = None,
                    event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Register explicit user acceptance and complete in one snapshot/event commit."""
        candidate_revision = _required(candidate_revision, "candidate_revision")
        completion_decision_ref = _required(completion_decision_ref, "completion_decision_ref")
        if artifact_ref is not None:
            artifact_ref = _required(artifact_ref, "artifact_ref")
        decision = {"type": "acceptance", "value": "approved", "artifact_ref": artifact_ref,
                    "candidate_revision": candidate_revision}

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "awaiting_acceptance":
                raise TaskError("invalid_transition", "accept доступен только в awaiting_acceptance")
            readiness = task["artifacts"].get("readiness", {}).get("metadata", {})
            if readiness.get("candidate_revision") != candidate_revision:
                raise TaskError("guard_failed", "Приёмка относится к другой ревизии",
                                expected=readiness.get("candidate_revision"), actual=candidate_revision)
            if "acceptance_package" not in task["artifacts"]:
                raise TaskError("guard_failed", "Нет пакета приёмки")
            task["user_decisions"].append(decision)
            self._complete(task, completion_decision_ref)
            return {"to": "completed", "completion_decision_ref": completion_decision_ref,
                    "user_decision": decision}

        return self._mutate(task_id, expected_version, "task_completed", change,
                            operation_id=operation_id,
                            operation_payload={"candidate_revision": candidate_revision,
                                               "completion_decision_ref": completion_decision_ref,
                                               "artifact_ref": artifact_ref}, event_context=event_context)

    def cancel_task(self, task_id: str, expected_version: int, *, reason: str) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Задача уже завершена")
            if task["active_run_ref"] or task["active_claim"]:
                raise TaskError("guard_failed", "Сначала остановите запуск и освободите закрепление")
            task["status"] = "cancelled"
            task["terminal_at"] = _stamp(self.clock())
            return {"to": "cancelled", "reason": reason}

        return self._mutate(task_id, expected_version, "task_cancelled", change)

    def _terminal_time(self, task: dict[str, Any]) -> datetime:
        raw = task.get("terminal_at")
        if raw:
            return datetime.fromisoformat(raw)
        history = self.get_history(task["id"])
        terminal_event = next(
            (event for event in reversed(history) if event["type"] in {"task_completed", "task_cancelled"}),
            None,
        )
        if terminal_event is not None:
            return datetime.fromisoformat(terminal_event["at"])
        return datetime.fromisoformat(task["updated_at"])

    def archive_task(self, task_id: str, expected_version: int, *, reason: str,
                     actor_ref: str | None = None, operation_id: str | None = None,
                     event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")
        actor_ref = _required(actor_ref, "actor_ref") if actor_ref is not None else None
        current = self.get_task(task_id)
        terminal_at = _stamp(self._terminal_time(current))
        archived_at = _stamp(self.clock())

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] not in TERMINAL:
                raise TaskError("invalid_transition", "Архивировать можно только completed или cancelled")
            if task.get("active_run_ref") or task.get("active_claim"):
                raise TaskError("guard_failed", "Сначала остановите запуск и освободите закрепление")
            if task.get("archive"):
                raise TaskError("invalid_transition", "Задача уже архивирована")
            task["archive"] = {"archived_at": archived_at, "archived_by": actor_ref,
                                "reason": reason, "terminal_at": terminal_at}
            return {"archived_at": archived_at, "terminal_at": terminal_at, "reason": reason}

        return self._mutate(task_id, expected_version, "task_archived", change,
                            operation_id=operation_id,
                            operation_payload={"reason": reason, "actor_ref": actor_ref},
                            event_context=event_context)

    def unarchive_task(self, task_id: str, expected_version: int, *, reason: str,
                       operation_id: str | None = None,
                       event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            archive = task.get("archive")
            if not archive:
                raise TaskError("invalid_transition", "Задача не архивирована")
            task["archive"] = None
            return {"reason": reason}

        return self._mutate(task_id, expected_version, "task_unarchived", change,
                            operation_id=operation_id,
                            operation_payload={"reason": reason}, event_context=event_context)

    def purge_task(self, task_id: str, expected_version: int, *, reason: str,
                   actor_ref: str | None = None, operation_id: str | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")
        actor_ref = _required(actor_ref, "actor_ref") if actor_ref is not None else None
        _task_id(task_id)
        _version(expected_version)
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        fingerprint = self._operation_fingerprint("task_purged", task_id, expected_version, reason, actor_ref)
        if operation_id is not None:
            replay = self.repository.replay_operation(operation_id, fingerprint)
            if replay is not None:
                return replay
        task = self.get_task(task_id)
        if task["status"] not in TERMINAL:
            raise TaskError("invalid_transition", "Физически удалять можно только завершённые или отменённые задачи")
        archive = task.get("archive")
        if not archive:
            raise TaskError("guard_failed", "Сначала архивируйте задачу")
        if task.get("active_run_ref") or task.get("active_claim"):
            raise TaskError("guard_failed", "Активный запуск или claim блокирует удаление")
        terminal_at = _utc(datetime.fromisoformat(archive["terminal_at"]))
        eligible_at = _add_months(terminal_at, RETENTION_MONTHS)
        now = _utc(self.clock())
        if now < eligible_at:
            raise TaskError("retention_not_elapsed", "Срок хранения ещё не истёк",
                            eligible_at=_stamp(eligible_at), terminal_at=_stamp(terminal_at))
        return self.repository.purge(
            task_id, expected_version, terminal_at=_stamp(terminal_at),
            archived_at=_required(archive["archived_at"], "archived_at"), purged_at=_stamp(now),
            reason=reason, actor_ref=actor_ref, operation_id=operation_id, fingerprint=fingerprint,
        )

    def register_external_link(self, task_id: str, expected_version: int, *, tracker: str,
                               external_ref: str) -> dict[str, Any]:
        link = {"tracker": _required(tracker, "tracker"),
                "external_ref": _required(external_ref, "external_ref"), "relation": "projection"}

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if link not in task["external_links"]:
                task["external_links"].append(link)
            return link

        return self._mutate(task_id, expected_version, "external_link_registered", change)
