"""Интеграция подготовки с Graph Runtime и публичным Task Manager API."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from orchestrator_task_manager import TaskError, TaskManagerService

from .artifact_repository import ArtifactRepository, ArtifactRecord, ArtifactError
from .workflow_runtime import Graph, GraphRuntime, Node, NodeResult, RuntimeError, WaitState, WorkflowRun


class PreparationError(RuntimeError):
    """Непринятый результат адаптера или незавершённая синхронизация."""


Adapter = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PreparationError("contract_violation", "Требуется непустая строка", field=field_name)
    return value


def _strings(value: Any, field_name: str, *, nonempty: bool = False) -> list[str]:
    if (not isinstance(value, list) or (nonempty and not value)
            or any(not isinstance(item, str) or not item.strip() for item in value)):
        raise PreparationError("contract_violation", "Требуется список непустых строк", field=field_name)
    return value


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PreparationError("contract_violation", "Результат должен быть сериализуемым JSON") from exc


def _graph() -> Graph:
    nodes = {}
    for stage, outcome, target in (("context", "success", "analysis"), ("analysis", "success", "planning"),
                                   ("planning", "success", "plan_review"), ("plan_review", "approved", "package"),
                                   ("package", "success", "ready"), ("ready", "success", "succeeded")):
        transitions = {outcome: target, "needs_input": stage, "blocked": stage, "failure": "failed"}
        if stage == "analysis":
            transitions["needs_context"] = "context"
        if stage == "plan_review":
            transitions["changes_required"] = "planning"
        contract = stage.replace("_", "-")
        nodes[stage] = Node(stage, f"{contract}-request/v1", f"{contract}-result/v1", tuple(transitions), transitions)
    return Graph("development-preparation-v1", 1, "context", nodes)


@dataclass
class _Session:
    task: dict[str, Any]
    profile: dict[str, Any]
    revision: str
    ref: str
    records: dict[str, ArtifactRecord] = field(default_factory=dict)
    actions: list[Callable[[], None]] = field(default_factory=list)
    cursor: int = 0
    pending: bool = False
    sequence: int = 0
    review_cycles: int = 0
    expansions: int = 0
    blocker: str | None = None


class PreparationWorkflow:
    """Одна сессия подготовки; никакого автоматического claim/исполнения.

    Принятый runtime-result и его файловые/Task Manager эффекты синхронизируются
    отдельно. До завершения synchronize следующий узел запрещён. После version
    conflict требуется явный reconcile, а не автоматическое перечитывание версии.
    """

    def __init__(self, service: TaskManagerService, repository: ArtifactRepository,
                 adapters: Mapping[str, Adapter], *, runtime: GraphRuntime | None = None,
                 max_review_cycles: int = 2, max_context_expansions: int = 2) -> None:
        if not isinstance(adapters, Mapping):
            raise PreparationError("contract_violation", "adapters должны быть объектом")
        for stage in ("context", "analysis", "planning", "plan_review"):
            if not callable(adapters.get(stage)):
                raise PreparationError("contract_violation", "Не задан адаптер", stage=stage)
        for name, value in (("max_review_cycles", max_review_cycles), ("max_context_expansions", max_context_expansions)):
            if type(value) is not int or value < 1:
                raise PreparationError("contract_violation", "Лимит должен быть положительным целым", field=name)
        # Не используем внутренний repository Task Manager для определения root.
        self.service = service
        self.repository = repository
        self.adapters = dict(adapters)
        self.runtime = runtime or GraphRuntime()
        self.max_review_cycles = max_review_cycles
        self.max_context_expansions = max_context_expansions
        self._sessions: dict[str, _Session] = {}

    def start(self, task_id: str, *, prepared_source_revision: str,
              project_profile: Mapping[str, Any] | None = None) -> WorkflowRun:
        revision = _text(prepared_source_revision, "prepared_source_revision")
        if project_profile is not None and not isinstance(project_profile, Mapping):
            raise PreparationError("contract_violation", "project_profile должен быть объектом")
        profile = copy.deepcopy(dict(project_profile or {}))
        _json_bytes(profile)
        task = self.service.get_task(task_id)
        if task["status"] not in {"created", "preparing"} or task["active_run_ref"] or task["active_claim"]:
            raise PreparationError("invalid_state", "Подготовка требует created/preparing без активного запуска/claim")
        run = self.runtime.create_run(_graph(), {}, task_ref=task_id, phase="preparation")
        session = _Session(task, profile, revision, "PREP-" + uuid.uuid4().hex)
        try:
            if task["status"] == "created":
                self._call(session, "start_preparation", run_ref=run.run_id)
            else:
                self._call(session, "link_workflow_run", run_ref=run.run_id, relation="active")
        except PreparationError:
            self.runtime.cancel(run.run_id, "Не удалось зарегистрировать запуск подготовки")
            raise
        self._sessions[run.run_id] = session
        return run

    def inspect(self, run_id: str) -> dict[str, Any]:
        session = self._session(run_id)
        return {"run": self.runtime.inspect_run(run_id).to_dict(), "task": self.service.get_task(session.task["id"]),
                "sync_pending": session.pending, "sync_cursor": session.cursor,
                "sync_actions": len(session.actions),
                "artifacts": {role: record.to_dict() for role, record in session.records.items()}}

    def step(self, run_id: str) -> NodeResult | WaitState:
        session = self._session(run_id)
        self._before_step(session)
        if session.task["status"] != "preparing" or session.task["active_run_ref"] != run_id:
            raise PreparationError("invalid_state", "Задача не принадлежит активной подготовке")
        result = self.runtime.step(run_id, lambda node, inputs, run: self._execute(session, node, run))
        self._queue(run_id)
        self.synchronize(run_id)
        return result

    def resume(self, run_id: str, answer: Any, *, wait_id: str, node_id: str) -> NodeResult | WaitState:
        session = self._session(run_id)
        self._before_step(session)
        _text(wait_id, "wait_id")
        _text(node_id, "node_id")
        if session.task["status"] != "awaiting_input" or session.task["active_run_ref"]:
            raise PreparationError("invalid_state", "Task Manager должен ожидать ввод без активной ссылки")
        _json_bytes(answer)
        result = self.runtime.resume(run_id, answer, lambda node, inputs, run: self._execute(session, node, run),
                                     wait_id=wait_id, node_id=node_id)
        self._queue(run_id, answer=answer, resumed="user_input")
        self.synchronize(run_id)
        return result

    def resume_blocked(self, run_id: str, *, resolution: str, wait_id: str,
                       node_id: str, answer: Any = None) -> NodeResult | WaitState:
        session = self._session(run_id)
        self._before_step(session)
        _text(wait_id, "wait_id")
        _text(node_id, "node_id")
        if session.task["status"] != "blocked" or session.task["active_run_ref"] or not session.blocker:
            raise PreparationError("invalid_state", "Нужен принадлежащий подготовке blocker без активной ссылки")
        _text(resolution, "resolution")
        _json_bytes(answer)
        result = self.runtime.resume_blocked(run_id, lambda node, inputs, run: self._execute(session, node, run),
                                             wait_id=wait_id, node_id=node_id, answer=answer)
        self._queue(run_id, answer=answer, resumed="blocker", resolution=resolution)
        self.synchronize(run_id)
        return result

    def synchronize(self, run_id: str) -> None:
        session = self._session(run_id)
        try:
            while session.pending and session.cursor < len(session.actions):
                self._assert_version(session)
                session.actions[session.cursor]()
                session.cursor += 1
        except TaskError as exc:
            raise PreparationError(exc.code, str(exc), **exc.details) from exc
        except ArtifactError as exc:
            raise PreparationError(exc.code, exc.message, **exc.details) from exc
        except OSError as exc:
            raise PreparationError("repository_failure", "Файловая синхронизация не завершена") from exc
        session.pending = False

    def reconcile(self, run_id: str, *, expected_version: int) -> None:
        """Явно принять прочитанную caller-ом версию после внешней мутации."""
        session = self._session(run_id)
        task = self.service.get_task(session.task["id"])
        if type(expected_version) is not int or task["version"] != expected_version:
            raise PreparationError("task_version_conflict", "Нужна явно прочитанная актуальная версия")
        if task["definition_version"] != session.task["definition_version"]:
            raise PreparationError("stale_preparation", "Определение изменилось; нужна новая подготовка")
        if task["active_claim"] or task["active_run_ref"] not in {None, run_id} or task["status"] not in {
            "preparing", "awaiting_input", "blocked", "ready"
        }:
            raise PreparationError("invalid_state", "Внешнее состояние несовместимо с этим запуском")
        for role in ("plan", "plan_review", "execution_package"):
            if task["artifacts"].get(role) != session.task["artifacts"].get(role):
                raise PreparationError("stale_preparation", "Артефакт подготовки изменён извне", role=role)
        session.task = task

    def _session(self, run_id: str) -> _Session:
        if run_id not in self._sessions:
            raise PreparationError("run_not_found", "Сессия подготовки не найдена", run_id=run_id)
        return self._sessions[run_id]

    def _assert_version(self, session: _Session) -> None:
        actual = self.service.get_task(session.task["id"])
        if actual["version"] != session.task["version"]:
            raise PreparationError("task_version_conflict", "Задача изменена извне; слепой повтор запрещён",
                                   expected=session.task["version"], actual=actual["version"])

    def _before_step(self, session: _Session) -> None:
        if session.pending:
            raise PreparationError("sync_pending", "Сначала завершите синхронизацию принятого результата")
        self._assert_version(session)

    def _call(self, session: _Session, method: str, **kwargs: Any) -> None:
        try:
            session.task = getattr(self.service, method)(session.task["id"], session.task["version"], **kwargs)
        except TaskError as exc:
            raise PreparationError(exc.code, str(exc), **exc.details) from exc

    def _execute(self, session: _Session, node: Node, run: WorkflowRun) -> NodeResult:
        stage = node.node_id
        if stage == "ready":
            return NodeResult(stage, "success")
        if stage == "package":
            plan, review = session.records["plan"], session.records["plan_review"]
            try:
                self.repository.verify(plan.ref, plan.role, plan.version)
                self.repository.verify(review.ref, review.role, review.version)
            except ArtifactError as exc:
                raise PreparationError(exc.code, exc.message, **exc.details) from exc
            payload = {"task_ref": session.task["id"], "definition_version": session.task["definition_version"],
                       "plan": plan.to_dict(), "plan_review": review.to_dict(),
                       "prepared_source_revision": session.revision, "entrypoint": "execution_preflight"}
            return self._artifact_result(session, stage, "success", payload, "execution_package")
        request = {"contract": node.input_contract, "task": copy.deepcopy(session.task),
                   "project_profile": copy.deepcopy(session.profile),
                   "answer": copy.deepcopy(run.wait.answer) if run.wait else None}
        keys = {"context": ("analysis",), "analysis": ("context",),
                "planning": ("analysis", "planning", "plan_review"),
                "plan_review": ("planning", "plan_review")}[stage]
        request["previous"] = {key: copy.deepcopy(run.results[key]) for key in keys if key in run.results}
        try:
            raw = self.adapters[stage](request)
        except Exception as exc:
            raise PreparationError("adapter_failure", "Адаптер завершился ошибкой", stage=stage,
                                   error=type(exc).__name__) from exc
        if not isinstance(raw, Mapping):
            raise PreparationError("contract_violation", "Адаптер должен вернуть объект", stage=stage)
        raw = copy.deepcopy(dict(raw))
        _json_bytes(raw)
        if set(raw) - {"outcome", "payload", "question", "reason"}:
            raise PreparationError("contract_violation", "Неизвестные поля envelope адаптера", stage=stage)
        outcome = raw.get("outcome")
        if not isinstance(outcome, str) or outcome not in node.outcomes:
            raise PreparationError("unknown_outcome", "Исход не объявлен графом", stage=stage)
        if outcome in {"needs_input", "blocked", "failure"}:
            reason = _text(raw.get("question" if outcome == "needs_input" else "reason"), outcome)
            wait = None if outcome == "failure" else WaitState("WAIT-" + uuid.uuid4().hex, stage,
                    "user_input" if outcome == "needs_input" else "blocker",
                    question=reason if outcome == "needs_input" else None,
                    reason=reason if outcome == "blocked" else None)
            return NodeResult(stage, outcome, data={"reason": reason}, wait=wait)
        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise PreparationError("contract_violation", "payload должен быть объектом", stage=stage)
        if outcome == "needs_context":
            _strings(payload.get("requests"), "requests", nonempty=True)
            if session.expansions >= self.max_context_expansions:
                reason = "Исчерпан лимит расширения context"
                return NodeResult(stage, "blocked", data={"reason": reason},
                                  wait=WaitState("WAIT-" + uuid.uuid4().hex, stage, "blocker", reason=reason))
        elif stage == "context":
            _text(payload.get("summary"), "summary")
            _strings(payload.get("evidence_refs"), "evidence_refs")
        elif stage == "analysis":
            _text(payload.get("objective_interpretation"), "objective_interpretation")
            for name in ("constraints", "invariants", "unknowns"):
                _strings(payload.get(name), name)
        elif stage == "planning":
            document = self._plan_document(payload, session, run)
            return self._artifact_result(session, stage, outcome, payload, "plan", content=document)
        elif stage == "plan_review":
            self._review(payload, outcome, session)
            if outcome == "changes_required" and session.review_cycles + 1 >= self.max_review_cycles:
                return self._artifact_result(session, stage, "blocked", payload, "plan_review",
                                             reason="Исчерпаны review cycles; требуется диагностика и явное решение")
        return self._artifact_result(session, stage, outcome, payload, stage)

    def _artifact_result(self, session: _Session, stage: str, outcome: str, payload: dict[str, Any],
                         role: str, *, content: str | None = None, reason: str | None = None) -> NodeResult:
        value = content if content is not None else payload
        encoded = content.encode("utf-8") if content is not None else _json_bytes(payload)
        artifact = {"ref": session.ref, "role": role, "version": f"v{session.sequence + 1}",
                    "contract": f"{role.replace('_', '-')}/v1", "sha256": hashlib.sha256(encoded).hexdigest(),
                    "media_type": "text/markdown" if content is not None else "application/json", "value": value}
        wait = (WaitState("WAIT-" + uuid.uuid4().hex, stage, "blocker", reason=reason)
                if outcome == "blocked" else None)
        return NodeResult(stage, outcome, artifacts={role: artifact}, data={"payload": payload, "reason": reason}, wait=wait)

    def _plan_document(self, payload: dict[str, Any], session: _Session, run: WorkflowRun) -> str:
        _text(payload.get("goal"), "goal")
        scope = payload.get("scope")
        if not isinstance(scope, dict):
            raise PreparationError("contract_violation", "Нужен явный scope плана")
        _strings(scope.get("in"), "scope.in", nonempty=True)
        _strings(scope.get("out"), "scope.out")
        _strings(payload.get("global_validation"), "global_validation", nonempty=True)
        constraints = _strings(payload.get("global_constraints"), "global_constraints")
        analysis = run.results["analysis"]["data"]["payload"]
        inherited = session.task["constraints"] + analysis["constraints"] + analysis["invariants"]
        if not set(inherited).issubset(constraints):
            raise PreparationError("contract_violation", "План потерял обязательные constraints")
        units = payload.get("work_units")
        if not isinstance(units, list) or not units:
            raise PreparationError("contract_violation", "План должен иметь work_units")
        ids = set()
        for unit in units:
            if not isinstance(unit, dict):
                raise PreparationError("contract_violation", "work_unit должен быть объектом")
            unit_id = _text(unit.get("id"), "id")
            if unit_id in ids:
                raise PreparationError("contract_violation", "work_unit id не уникален")
            ids.add(unit_id)
            _text(unit.get("goal"), "goal")
            for name in ("files_objects", "expected_result", "validation"):
                _strings(unit.get(name), name, nonempty=True)
            _strings(unit.get("depends_on", []), "depends_on")
        completed = set()
        remaining = {unit["id"]: set(unit.get("depends_on", [])) for unit in units}
        while remaining:
            ready = {key for key, deps in remaining.items() if deps.issubset(completed)}
            if not ready:
                raise PreparationError("contract_violation", "Цикл или неизвестная зависимость work_units")
            completed.update(ready)
            remaining = {key: deps for key, deps in remaining.items() if key not in ready}
        # Полный структурированный план сохраняется в человекочитаемой проекции.
        return f"# План {session.task['id']}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n```\n"

    def _review(self, payload: dict[str, Any], outcome: str, session: _Session) -> None:
        findings = payload.get("findings")
        if not isinstance(findings, list) or any(not isinstance(item, dict) for item in findings):
            raise PreparationError("contract_violation", "review findings должны быть списком объектов")
        for finding in findings:
            _text(finding.get("summary"), "finding.summary")
            severity, status = finding.get("severity", "minor"), finding.get("status", "open")
            if (not isinstance(severity, str) or not isinstance(status, str)
                    or severity not in {"info", "minor", "major", "critical"}
                    or status not in {"open", "resolved", "accepted_risk", "obsolete"}):
                raise PreparationError("contract_violation", "Неизвестные severity/status finding")
            if severity in {"major", "critical"}:
                _strings(finding.get("evidence_refs"), "finding.evidence_refs", nonempty=True)
        if outcome == "approved":
            binding = payload.get("approved_binding", {})
            if (not isinstance(binding, dict) or binding.get("plan_sha256") != session.records["plan"].sha256
                    or type(binding.get("definition_version")) is not int
                    or binding.get("definition_version") != session.task["definition_version"]):
                raise PreparationError("stale_review", "Одобрение не связано с актуальным plan/definition")
            covered = _strings(payload.get("criterion_ids"), "criterion_ids", nonempty=True)
            if (set(covered) != {criterion["id"] for criterion in session.task["acceptance_criteria"]}
                    or payload.get("zero_context_executable") is not True
                    or any(item.get("severity") in {"major", "critical"} and item.get("status", "open") == "open"
                           for item in findings)):
                raise PreparationError("contract_violation", "Review не подтверждает исполнимость и полное coverage")
        elif not findings:
            raise PreparationError("contract_violation", "changes_required требует конкретные findings")

    def _publish(self, session: _Session, artifact: Mapping[str, Any]) -> None:
        value = artifact["value"]
        content = value.encode("utf-8") if isinstance(value, str) else _json_bytes(value)
        record = self.repository.put(artifact["ref"], artifact["role"], artifact["version"], content,
                                     contract=artifact["contract"], media_type=artifact["media_type"])
        if record.sha256 != artifact["sha256"]:
            raise PreparationError("integrity_error", "Хеш принятого результата изменился")
        session.records[record.role] = record

    def _queue(self, run_id: str, *, answer: Any = None, resumed: str | None = None,
               resolution: str | None = None) -> None:
        session = self._session(run_id)
        result = self.runtime.inspect_run(run_id).last_result
        assert result is not None
        actions = []
        if resumed:
            if resumed == "user_input":
                actions.append(lambda: self._call(session, "record_user_decision", decision_type="clarification",
                                                  value=_json_bytes(answer).decode("utf-8")))
            else:
                actions.append(lambda: self._call(session, "resolve_blocker", blocker_ref=session.blocker,
                                                  resolution=resolution))
            actions.append(lambda: self._call(session, "transition_status", to="preparing", reason="Возобновление подготовки"))
            actions.append(lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="active"))
        for artifact in result.artifacts.values():
            actions.append(lambda artifact=artifact: self._publish(session, artifact))
        if result.outcome == "needs_input":
            actions.append(lambda: self._call(session, "transition_status", to="awaiting_input", reason=result.data["reason"]))
            actions.append(lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="finished"))
        elif result.outcome in {"blocked", "failure"}:
            def block():
                self._call(session, "add_blocker", blocker_type="preparation", summary=result.data["reason"])
                session.blocker = session.task["blockers"][-1]["id"]
            actions.extend([block, lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="finished")])
        elif result.node_id == "planning":
            actions.append(lambda: self._attach_plan(session))
        elif result.node_id == "plan_review" and result.outcome == "approved":
            def attach_review():
                record = session.records["plan_review"]
                self._call(session, "attach_artifact", role="plan_review", ref=f"{record.ref}:{record.role}:{record.version}",
                           metadata={"status": "approved", "plan_sha256": session.records["plan"].sha256,
                                     "definition_version": session.task["definition_version"], "repository": record.to_dict()})
            actions.append(attach_review)
        elif result.node_id == "package":
            actions.append(lambda: self._call(session, "attach_execution_package",
                ref=f"{session.records['execution_package'].ref}:execution_package:{session.records['execution_package'].version}",
                plan_sha256=session.records["plan"].sha256, prepared_source_revision=session.revision))
        elif result.node_id == "ready":
            actions.append(lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="finished"))
            actions.append(lambda: self._call(session, "mark_ready"))
        if result.outcome == "needs_context":
            session.expansions += 1
        if result.node_id == "plan_review" and result.outcome in {"changes_required", "approved", "blocked"}:
            session.review_cycles += 1
        session.sequence += 1
        session.actions, session.cursor, session.pending = actions, 0, True

    def _attach_plan(self, session: _Session) -> None:
        record = session.records["plan"]
        content = self.repository.get(record.ref, record.role, record.version).content
        destination = self.repository.project_root / ".orchestrator" / "tasks" / session.task["id"] / "plan.md"
        current = self.repository.project_root
        for segment in destination.relative_to(current).parts:
            current = current / segment
            try:
                info = current.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise PreparationError("validation_failed", "Ссылка в пути plan projection запрещена")
        if not destination.resolve(strict=False).is_relative_to(self.repository.project_root):
            raise PreparationError("validation_failed", "Plan projection выходит за проект")
        if destination.exists() and destination.read_bytes() != content:
            previous = session.task["artifacts"].get("plan", {})
            metadata = previous.get("metadata", {}).get("repository", {})
            if (not isinstance(metadata, dict) or not metadata.get("ref") or metadata.get("role") != "plan"
                    or hashlib.sha256(destination.read_bytes()).hexdigest() != previous.get("sha256")):
                raise PreparationError("projection_conflict", "Не перезаписывайте посторонний/изменённый plan.md")
            backed = self.repository.verify(metadata["ref"], "plan", metadata.get("version"))
            if backed.sha256 != previous["sha256"]:
                raise PreparationError("projection_conflict", "Не подтверждена immutable основа прежней проекции")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".plan-", delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self._call(session, "attach_artifact", role="plan", ref=f"{record.ref}:plan:{record.version}",
                   path=destination.relative_to(self.repository.project_root).as_posix(),
                   sha256=record.sha256, metadata={"repository": record.to_dict(),
                                                 "definition_version": session.task["definition_version"]})


__all__ = ["PreparationWorkflow", "PreparationError"]
