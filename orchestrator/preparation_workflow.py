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


from .preparation_primitives import (
    PreparationError, PreparationPrimitives, _Session, _graph, _text, _json_bytes,
)

Adapter = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class PreparationWorkflow(PreparationPrimitives):
    """Legacy callback preparation; новый агентный путь — AgentPreparation."""

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
        return self._prepare_result(session, node, run, raw)

__all__ = ["PreparationWorkflow", "PreparationError"]
