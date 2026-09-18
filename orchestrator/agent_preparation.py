"""Явная агентная подготовка; semantic решения не выполняются ядром."""
from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Mapping

from orchestrator_task_manager import TaskError, TaskManagerService

from .agent_runtime import AgentGraphRuntime, _UNSET, _json_copy
from .artifact_repository import ArtifactError, ArtifactRepository
from .preparation_primitives import PreparationError, PreparationPrimitives, _Session, _graph, _text, _json_bytes
from .runtime_contracts import Graph
from .task_effects import TaskEffectSync


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


@dataclass
class _AgentSession(_Session):
    uncertain: dict[str, Any] | None = None
    recovered: dict[str, Any] | None = None


class AgentPreparation(TaskEffectSync, PreparationPrimitives):
    """Фиксированный root, отдельный AgentGraphRuntime, только явные actions.

    Результат принимается до синхронизации; при ошибке следующий action
    запрещён. Неопределённая task mutation требует сверки публичной истории.
    """

    def __init__(self, project_root: Path, *, max_review_cycles: int = 2,
                 max_context_expansions: int = 2, max_results: int = 100) -> None:
        for name, value in (("max_review_cycles", max_review_cycles),
                            ("max_context_expansions", max_context_expansions), ("max_results", max_results)):
            if type(value) is not int or value < 1:
                raise PreparationError("contract_violation", "Лимит должен быть положительным целым", field=name)
        self.repository = ArtifactRepository(project_root)
        self.service = TaskManagerService(self.repository.project_root)
        self.runtime = AgentGraphRuntime()
        self.max_review_cycles = max_review_cycles
        self.max_context_expansions = max_context_expansions
        self.max_results = max_results
        self._sessions: dict[str, _AgentSession] = {}
        self._lock = threading.RLock()

    @_locked
    def start(self, task_id: str, *, expected_task_version: int, prepared_source_revision: str,
              project_profile: Mapping[str, Any] | None = None):
        revision = _text(prepared_source_revision, "prepared_source_revision")
        if project_profile is not None and not isinstance(project_profile, Mapping):
            raise PreparationError("contract_violation", "project_profile должен быть объектом")
        profile = _json_copy(dict(project_profile or {}))
        task = self.service.get_task(task_id)
        self._task_guard(task, expected_task_version)
        if task["status"] not in {"created", "preparing"} or task["active_run_ref"] or task["active_claim"]:
            raise PreparationError("invalid_state", "Нужна created/preparing без active run/claim")
        policy = _graph()
        graph = Graph("agent-development-preparation-v1", 1, policy.entry_node, policy.nodes)
        run = self.runtime.create_run(graph, {}, task_ref=task_id,
            task_definition_version=task["definition_version"], phase="preparation", max_results=self.max_results)
        session = _AgentSession(task, profile, revision, "PREP-" + uuid.uuid4().hex)
        method = "start_preparation" if task["status"] == "created" else "link_workflow_run"
        options = {"run_ref": run.run_id}
        if method == "link_workflow_run":
            options["relation"] = "active"
        session.actions = [lambda: self._call(session, method, **options)]
        session.pending = True
        self._sessions[run.run_id] = session
        try:
            self.synchronize(run.run_id)
        except PreparationError as exc:
            exc.details["run_id"] = run.run_id
            raise
        return self.runtime.inspect_run(run.run_id)

    @_locked
    def inspect(self, run_id: str) -> dict[str, Any]:
        snapshot = super().inspect(run_id)
        snapshot["unknown_effect"] = copy.deepcopy(self._session(run_id).uncertain)
        return snapshot

    @_locked
    def available_actions(self, run_id: str) -> dict[str, Any]:
        session = self._session(run_id)
        actions = self.runtime.available_actions(run_id)
        actions["actions"] = ["submit" if action == "submit_result" else action for action in actions["actions"]]
        if session.pending:
            actions["actions"] = ["reconcile_effect"] if session.uncertain else ["synchronize", "reconcile"]
        else:
            actual = self.service.get_task(session.task["id"])
            if actual["version"] != session.task["version"]:
                actions["actions"] = ["reconcile"]
                if "cancel" in self.runtime.available_actions(run_id)["actions"]:
                    actions["actions"].append("cancel")
        actions["task_version"] = session.task["version"]
        actions["sync_pending"] = session.pending
        return actions

    @_locked
    def request(self, run_id: str) -> dict[str, Any]:
        session = self._session(run_id)
        run = self.runtime.inspect_run(run_id)
        actions = self.available_actions(run_id)
        return {"contract": actions["node"]["input_contract"] if actions["node"] else None,
                "actions": actions, "task": self.service.get_task(session.task["id"]),
                "project_profile": copy.deepcopy(session.profile),
                "previous": copy.deepcopy(run.results), "resumed_wait": copy.deepcopy(run.resumed_wait),
                "artifacts": {role: record.to_dict() for role, record in session.records.items()}}

    @_locked
    def submit(self, run_id: str, envelope: Mapping[str, Any], *, expected_revision: int,
               expected_task_version: int):
        session, run = self._action_guard(run_id, expected_revision, expected_task_version)
        if session.task["status"] != "preparing" or session.task["active_run_ref"] != run_id:
            raise PreparationError("invalid_state", "Задача не принадлежит активной подготовке")
        if "submit_result" not in self.runtime.available_actions(run_id)["actions"]:
            raise PreparationError("invalid_state", "submit недоступен")
        if not isinstance(envelope, Mapping):
            raise PreparationError("contract_violation", "envelope должен быть объектом")
        raw = _json_copy(dict(envelope))
        node = _graph().nodes[run.current_node]
        if node.node_id in {"package", "ready"} and raw == {"outcome": "success"}:
            result = self._gate_result(session, node.node_id)
        elif node.node_id in {"package", "ready"} and raw.get("outcome") not in {"needs_input", "blocked", "failure"}:
            raise PreparationError("contract_violation", "Gate требует только outcome=success; payload формирует primitive")
        else:
            result = self._prepare_result(session, node, run, raw)
        accepted = self.runtime.submit_result(run_id, result, expected_revision=expected_revision,
                                              task_definition_version=session.task["definition_version"])
        self._queue(run_id)
        self.synchronize(run_id)
        return accepted

    @_locked
    def resume_wait(self, run_id: str, *, expected_revision: int, expected_task_version: int,
                    wait_id: str, node_id: str, answer: Any = _UNSET, resolution: str | None = None):
        session, run = self._action_guard(run_id, expected_revision, expected_task_version)
        if run.wait is None:
            raise PreparationError("invalid_state", "Нет активного ожидания")
        kind = run.wait.kind
        expected_status = "awaiting_input" if kind == "user_input" else "blocked"
        if session.task["status"] != expected_status or session.task["active_run_ref"] or (kind == "blocker" and not session.blocker):
            raise PreparationError("invalid_state", "Wait не соответствует Task Manager")
        accepted = self.runtime.resume_wait(run_id, expected_revision=expected_revision,
            task_definition_version=session.task["definition_version"], wait_id=wait_id, node_id=node_id,
            answer=answer, resolution=resolution)
        if kind == "user_input":
            actions = [lambda: self._call(session, "record_user_decision", decision_type="clarification",
                                           value=_json_bytes(accepted.resumed_wait["answer"]).decode("utf-8"))]
        else:
            actions = [lambda: self._call(session, "resolve_blocker", blocker_ref=session.blocker, resolution=resolution)]
        actions.extend([lambda: self._call(session, "transition_status", to="preparing", reason="Возобновление подготовки"),
                        lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="active")])
        session.actions, session.cursor, session.pending = actions, 0, True
        self.synchronize(run_id)
        return accepted

    @_locked
    def cancel(self, run_id: str, *, expected_revision: int, expected_task_version: int, reason: str):
        session = self._session(run_id)
        if session.pending:
            raise PreparationError("sync_pending", "Сначала разрешите pending effects")
        task = self.service.get_task(session.task["id"])
        self._task_guard(task, expected_task_version)
        if task["active_claim"] or task["active_run_ref"] not in {None, run_id}:
            raise PreparationError("invalid_state", "Нельзя закрывать чужой запуск/claim")
        run = self.runtime.inspect_run(run_id)
        accepted = self.runtime.cancel(run_id, reason, expected_revision=expected_revision,
                                       task_definition_version=run.task_definition_version)
        # Cleanup допустим после definition drift, но не сертифицирует новую задачу.
        session.task = task
        session.actions = ([lambda: self._call(session, "link_workflow_run", run_ref=run_id, relation="finished")]
                           if task["active_run_ref"] == run_id else [])
        session.cursor, session.pending = 0, True
        self.synchronize(run_id)
        return accepted





    def _call(self, session: _AgentSession, method: str, **kwargs: Any) -> None:
        if method == "mark_ready" and not session.recovered:
            self._verify_ready_artifacts(session)
        super()._call(session, method, **kwargs)


    def _gate_result(self, session: _AgentSession, stage: str):
        if stage == "ready":
            self._verify_ready_artifacts(session)
        return super()._gate_result(session, stage)

    def _verify_ready_artifacts(self, session: _AgentSession) -> None:
        try:
            for role in ("plan", "plan_review", "execution_package"):
                record = session.records[role]
                self.repository.verify(record.ref, record.role, record.version)
            self.service.get_document(session.task["id"], "plan")
        except (ArtifactError, TaskError) as exc:
            raise PreparationError(exc.code, str(exc), **exc.details) from exc

    def _action_guard(self, run_id, expected_revision, expected_task_version):
        session = self._session(run_id)
        self._before_step(session)
        self._task_guard(session.task, expected_task_version)
        run = self.runtime.inspect_run(run_id)
        if type(expected_revision) is not int or run.revision != expected_revision:
            raise PreparationError("run_revision_conflict", "Process revision изменилась")
        if session.task["definition_version"] != run.task_definition_version:
            raise PreparationError("stale_preparation", "Definition изменилась; нужен новый run")
        return session, run

    @staticmethod
    def _task_guard(task, expected):
        if type(expected) is not int or task["version"] != expected:
            raise PreparationError("task_version_conflict", "Нужна прочитанная task version", actual=task["version"])


__all__ = ["AgentPreparation"]
