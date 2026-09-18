"""Явные агентские действия и детерминированное состояние процесса в памяти."""
from __future__ import annotations

import copy
import json
import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from .runtime_contracts import (
    Graph, Node, NodeResult, RuntimeError, WaitState, WorkflowRun,
    TERMINAL_STATES, TERMINAL_TRANSITIONS, validate_node_result,
)

_UNSET = object()


def _text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("contract_violation", f"{field_name} должен быть непустой строкой")
    return value


def _positive(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 1:
        raise RuntimeError("contract_violation", f"{field_name} должен быть положительным целым числом")
    return value


def _json_copy(value: Any) -> Any:
    try:
        normalized = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
        if normalized != value:
            raise ValueError("Нормализация меняет значение")
        return normalized
    except (TypeError, ValueError, RecursionError) as exc:
        raise RuntimeError("contract_violation", "Значение должно соответствовать JSON без преобразования ключей/типов") from exc


@dataclass
class AgentWorkflowRun(WorkflowRun):
    revision: int = 1
    task_definition_version: int | None = None
    max_results: int = 100
    node_limits: dict[str, int] = field(default_factory=dict)
    result_counts: dict[str, int] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    resumed_wait: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {**super().to_dict(), "revision": self.revision,
                "task_definition_version": self.task_definition_version, "max_results": self.max_results,
                "node_limits": dict(self.node_limits), "result_counts": dict(self.result_counts),
                "history": copy.deepcopy(self.history), "resumed_wait": copy.deepcopy(self.resumed_wait)}


class AgentGraphRuntime:
    """Не вызывает исполнителей; один снимок каждого процесса и локальный CAS."""

    def __init__(self) -> None:
        self._runs: dict[str, tuple[Graph, AgentWorkflowRun]] = {}
        self._lock = threading.RLock()

    def create_run(self, graph: Graph | Mapping[str, Any], inputs: Mapping[str, Any], *,
                   task_ref: str | None = None, task_definition_version: int | None = None,
                   run_id: str | None = None, phase: str = "request", max_results: int = 100,
                   node_limits: Mapping[str, int] | None = None) -> AgentWorkflowRun:
        with self._lock:
            graph = graph if isinstance(graph, Graph) else Graph.from_dict(graph)
            if set(graph.nodes) & TERMINAL_TRANSITIONS:
                raise RuntimeError("contract_violation", "node_id не должен совпадать с терминальным исходом")
            if not isinstance(inputs, Mapping):
                raise RuntimeError("contract_violation", "inputs должен быть объектом")
            input_data = _json_copy(dict(inputs))
            if task_ref is not None:
                _text(task_ref, "task_ref")
                _positive(task_definition_version, "task_definition_version")
            elif task_definition_version is not None:
                raise RuntimeError("contract_violation", "task_definition_version требует task_ref")
            _positive(max_results, "max_results")
            if node_limits is not None and not isinstance(node_limits, Mapping):
                raise RuntimeError("contract_violation", "node_limits должен быть объектом")
            limits = dict(node_limits or {})
            for node_id, limit in limits.items():
                if node_id not in graph.nodes:
                    raise RuntimeError("contract_violation", "Лимит относится к неизвестному узлу")
                _positive(limit, "node_limit")
            if not isinstance(phase, str) or phase not in {"request", "preparation", "execution"}:
                raise RuntimeError("contract_violation", "Неизвестная phase запуска")
            run_id = f"RUN-{uuid.uuid4().hex}" if run_id is None else _text(run_id, "run_id")
            if run_id in self._runs:
                raise RuntimeError("contract_violation", "run_id уже существует", run_id=run_id)
            run = AgentWorkflowRun(run_id, task_ref, graph.graph_id, graph.version, phase, "created",
                                   graph.entry_node, input_data, task_definition_version=task_definition_version,
                                   max_results=max_results, node_limits=limits)
            self._runs[run_id] = (graph, run)
            return copy.deepcopy(run)

    def inspect_run(self, run_id: str) -> AgentWorkflowRun:
        with self._lock:
            return copy.deepcopy(self._get(run_id)[1])

    def available_actions(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            graph, run = self._get(run_id)
            remaining = self._remaining(run)
            actions: list[str] = []
            if run.state not in TERMINAL_STATES:
                if run.state in {"waiting_input", "blocked"}:
                    actions.append("resume_wait")
                elif remaining > 0:
                    actions.append("submit_result")
                actions.append("cancel")
            node = graph.nodes.get(run.current_node)
            return {"run_id": run_id, "revision": run.revision, "state": run.state,
                    "task_definition_version": run.task_definition_version,
                    "actions": actions, "remaining_results": remaining,
                    "node": None if node is None else {
                        "node_id": node.node_id, "input_contract": node.input_contract,
                        "output_contract": node.output_contract, "required_outputs": list(node.required_outputs),
                        "outcomes": list(node.outcomes), "transitions": dict(node.transitions)},
                    "wait": run.wait.to_dict() if run.wait else None}

    def submit_result(self, run_id: str, result: NodeResult, *, expected_revision: int,
                      task_definition_version: int | None = None) -> AgentWorkflowRun:
        with self._lock:
            graph, run = self._guard(run_id, expected_revision, task_definition_version)
            if run.state not in {"created", "running"}:
                raise RuntimeError("invalid_state", "Результат нельзя принять в текущем состоянии", state=run.state)
            node = graph.nodes[run.current_node]
            result = copy.deepcopy(result)
            validate_node_result(node, result)
            if self._remaining(run) < 1:
                raise RuntimeError("result_limit_exceeded", "Исчерпан лимит принятых результатов", node_id=node.node_id)
            self._validate_wait(run, node, result)
            payload = _json_copy(result.to_dict())
            accepted = NodeResult(result.node_id, result.outcome, payload["artifacts"], payload["data"],
                                  payload["error"], copy.deepcopy(result.wait))
            working = self._working_copy(run)
            working.last_result = accepted
            working.results[node.node_id] = payload
            working.result_counts[node.node_id] = run.result_counts.get(node.node_id, 0) + 1
            working.resumed_wait = None
            if result.outcome in {"needs_input", "blocked"}:
                working.wait = copy.deepcopy(result.wait)
                working.state = "waiting_input" if result.outcome == "needs_input" else "blocked"
            else:
                working.wait = None
                target = node.transitions[result.outcome]
                working.current_node = None if target in TERMINAL_TRANSITIONS else target
                working.state = target if target in TERMINAL_TRANSITIONS else "running"
            return self._publish(graph, working, "submit_result", result=payload)

    def resume_wait(self, run_id: str, *, expected_revision: int, wait_id: str, node_id: str,
                    answer: Any = _UNSET, resolution: str | None = None,
                    task_definition_version: int | None = None) -> AgentWorkflowRun:
        with self._lock:
            graph, run = self._guard(run_id, expected_revision, task_definition_version)
            if run.state not in {"waiting_input", "blocked"} or run.wait is None:
                raise RuntimeError("invalid_state", "Нет активного ожидания")
            _text(wait_id, "wait_id")
            _text(node_id, "node_id")
            if wait_id != run.wait.wait_id:
                raise RuntimeError("stale_wait", "Ожидание уже изменилось")
            if node_id != run.wait.node_id:
                raise RuntimeError("node_mismatch", "Ответ относится к другому узлу")
            if run.wait.kind == "user_input":
                if answer is _UNSET or resolution is not None:
                    raise RuntimeError("contract_violation", "user_input требует answer, без resolution")
                response = {"answer": _json_copy(answer)}
            else:
                if answer is not _UNSET:
                    raise RuntimeError("contract_violation", "blocker требует resolution, без answer")
                response = {"resolution": _text(resolution, "resolution")}
            working = self._working_copy(run)
            working.resumed_wait = {**run.wait.to_dict(), **response}
            working.wait = None
            working.state = "running"
            return self._publish(graph, working, "resume_wait", wait=working.resumed_wait)

    def cancel(self, run_id: str, reason: str, *, expected_revision: int,
               task_definition_version: int | None = None) -> AgentWorkflowRun:
        with self._lock:
            graph, run = self._guard(run_id, expected_revision, task_definition_version)
            _text(reason, "reason")
            if run.state in TERMINAL_STATES:
                raise RuntimeError("invalid_state", "Терминальный запуск нельзя отменить")
            working = self._working_copy(run)
            working.state = "cancelled"
            working.wait = None
            working.resumed_wait = None
            return self._publish(graph, working, "cancel", reason=reason)

    def _get(self, run_id: str) -> tuple[Graph, AgentWorkflowRun]:
        _text(run_id, "run_id")
        if run_id not in self._runs:
            raise RuntimeError("run_not_found", "Запуск не найден", run_id=run_id)
        return self._runs[run_id]

    def _guard(self, run_id: str, revision: int, definition: int | None) -> tuple[Graph, AgentWorkflowRun]:
        graph, run = self._get(run_id)
        _positive(revision, "expected_revision")
        if revision != run.revision:
            raise RuntimeError("run_revision_conflict", "Процесс изменился", expected=revision, actual=run.revision)
        if definition is not None:
            _positive(definition, "task_definition_version")
        if definition != run.task_definition_version:
            raise RuntimeError("stale_definition", "Определение задачи изменилось или не передано",
                               expected=run.task_definition_version, actual=definition)
        return graph, run

    @staticmethod
    def _remaining(run: AgentWorkflowRun) -> int:
        remaining = run.max_results - sum(run.result_counts.values())
        if run.current_node in run.node_limits:
            remaining = min(remaining, run.node_limits[run.current_node] - run.result_counts.get(run.current_node, 0))
        return max(0, remaining)

    @staticmethod
    def _validate_wait(run: AgentWorkflowRun, node: Node, result: NodeResult) -> None:
        if result.outcome not in {"needs_input", "blocked"}:
            if result.wait is not None:
                raise RuntimeError("contract_violation", "Этот outcome не допускает wait")
            return
        wait = result.wait
        kind = "user_input" if result.outcome == "needs_input" else "blocker"
        if not isinstance(wait, WaitState) or wait.kind != kind:
            raise RuntimeError("contract_violation", "Ожидание отсутствует или имеет неверный kind")
        if wait.node_id != node.node_id:
            raise RuntimeError("node_mismatch", "Ожидание относится к другому узлу")
        _text(wait.question if kind == "user_input" else wait.reason, kind)
        if wait.answer is not None:
            raise RuntimeError("contract_violation", "Ответ принимается только через resume_wait")
        if any(event.get("result", {}).get("wait", {}).get("wait_id") == wait.wait_id
               for event in run.history if event.get("result", {}).get("wait") is not None):
            raise RuntimeError("stale_wait", "wait_id уже использован в этом запуске")

    @staticmethod
    def _working_copy(run: AgentWorkflowRun) -> AgentWorkflowRun:
        # Уже принятые payload принадлежат runtime и больше не изменяются.
        # Копируем только контейнеры, которые меняет новое действие; наружу
        # по-прежнему возвращаем полный deepcopy в _publish/inspect_run.
        working = copy.copy(run)
        working.results = dict(run.results)
        working.result_counts = dict(run.result_counts)
        working.history = list(run.history)
        return working

    def _publish(self, graph: Graph, run: AgentWorkflowRun, action: str, **details: Any) -> AgentWorkflowRun:
        run.revision += 1
        run.history.append({"revision": run.revision, "action": action, **copy.deepcopy(details)})
        snapshot = copy.deepcopy(run)
        self._runs[run.run_id] = (graph, run)
        return snapshot


__all__ = ["AgentGraphRuntime", "AgentWorkflowRun"]
