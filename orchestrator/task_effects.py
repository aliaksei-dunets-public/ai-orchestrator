"""Общий pending/unknown task-effect protocol явных facade; без reasoning."""
from __future__ import annotations

import copy
from functools import wraps
from typing import Any

from .preparation_primitives import PreparationError


def _locked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


class TaskEffectSync:
    """Mixin над deterministic sync primitives и session.task/actions/cursor."""

    @_locked
    def synchronize(self, run_id: str) -> None:
        session = self._session(run_id)
        if session.uncertain:
            raise PreparationError("effect_outcome_unknown", "Сначала сверка task snapshot/history")
        super().synchronize(run_id)

    @_locked
    def reconcile(self, run_id: str, *, expected_version: int) -> None:
        if self._session(run_id).uncertain:
            raise PreparationError("effect_outcome_unknown", "Используйте reconcile_effect")
        super().reconcile(run_id, expected_version=expected_version)

    @_locked
    def reconcile_effect(self, run_id: str, *, expected_task_version: int, applied: bool) -> None:
        """Только отсутствие мутации или точный единственный successor event.

        Дополнительные внешние события запрещают автоматическое восстановление.
        Принятый applied effect воспроизводит closure без повторной task mutation.
        """
        session = self._session(run_id)
        intent = session.uncertain
        if intent is None or type(applied) is not bool:
            raise PreparationError("invalid_state", "Нужны unknown effect и явный boolean applied")
        task = self.service.get_task(session.task["id"])
        self._task_guard(task, expected_task_version)
        before = intent["before"]
        if not applied:
            if task != before:
                raise PreparationError("effect_evidence_mismatch", "Task изменён; отсутствие записи не подтверждено")
        else:
            events = self.service.get_history(task["id"], after_sequence=before["version"])
            kind, payload = self._expected_event(intent)
            if (task["version"] != before["version"] + 1 or len(events) != 1
                    or events[0]["task_version"] != task["version"]
                    or events[0]["type"] != kind or events[0]["payload"] != payload
                    or task["definition_version"] != before["definition_version"]):
                raise PreparationError("effect_evidence_mismatch", "Нет точного единственного successor event")
            method, args = intent["method"], intent["kwargs"]
            if method in {"attach_artifact", "attach_execution_package"}:
                role = args.get("role", "execution_package")
                expected = {"ref": args["ref"], "path": args.get("path"), "sha256": args.get("sha256"),
                            "metadata": args.get("metadata", {})}
                if method == "attach_execution_package":
                    expected["metadata"] = {"plan_sha256": args["plan_sha256"],
                                            "prepared_source_revision": args["prepared_source_revision"]}
                if task["artifacts"].get(role) != expected:
                    raise PreparationError("effect_evidence_mismatch", "Артефакт не соответствует intent")
            if method == "add_blocker":
                expected = {"id": payload["blocker_ref"], "type": args["blocker_type"], "summary": args["summary"],
                            "blocking": True, "status": "open", "evidence_refs": []}
                if task["blockers"] != before["blockers"] + [expected]:
                    raise PreparationError("effect_evidence_mismatch", "Blocker не соответствует intent")
            session.recovered = {**intent, "task": task}
        session.uncertain = None

    @staticmethod
    def _expected_event(intent):
        method, args, task = intent["method"], intent["kwargs"], intent["before"]
        if method == "start_preparation":
            return "preparation_started", {"from": "created", "to": "preparing", "run_ref": args["run_ref"]}
        if method == "link_workflow_run":
            return "workflow_run_linked", {k: args[k] for k in ("run_ref", "relation")}
        if method in {"attach_artifact", "attach_execution_package"}:
            return "artifact_attached", {"role": args.get("role", "execution_package"), "ref": args["ref"]}
        if method == "add_blocker":
            return "blocker_added", {"blocker_ref": f"BLOCK-{len(task['blockers']) + 1:02d}", "blocking": True}
        if method == "resolve_blocker":
            return "blocker_resolved", {k: args[k] for k in ("blocker_ref", "resolution")}
        if method == "record_user_decision":
            return "user_decision_recorded", {"type": args["decision_type"], "value": args["value"],
                                              "artifact_ref": None, "candidate_revision": None}
        payload = {"from": task["status"], "to": args.get("to", "ready")}
        if method == "transition_status":
            payload["reason"] = args["reason"]
        return "status_changed", payload

    def _call(self, session: Any, method: str, **kwargs: Any) -> None:
        if session.recovered:
            recovery = session.recovered
            if recovery["method"] != method or recovery["kwargs"] != kwargs:
                raise PreparationError("effect_evidence_mismatch", "Closure не совпадает с recovered intent")
            session.task = recovery["task"]
            session.recovered = None
            return
        intent = {"method": method, "kwargs": copy.deepcopy(kwargs), "before": copy.deepcopy(session.task)}
        try:
            super()._call(session, method, **kwargs)
        except PreparationError as exc:
            if exc.code != "repository_failure":
                raise
            session.uncertain = intent
            raise PreparationError("effect_outcome_unknown", "Неизвестен результат task mutation", method=method) from exc
        except Exception as exc:
            session.uncertain = intent
            raise PreparationError("effect_outcome_unknown", "Неизвестен результат task mutation", method=method) from exc

    def _assert_version(self, session: Any) -> None:
        if session.recovered:
            actual = self.service.get_task(session.task["id"])
            if actual != session.recovered["task"]:
                raise PreparationError("task_version_conflict", "Task изменён после сверки unknown effect")
        else:
            super()._assert_version(session)

