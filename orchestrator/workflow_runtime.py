"""Минимальный in-memory Graph Runtime для одной real-time сессии."""
from __future__ import annotations

import copy
import re
import uuid
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping

TERMINAL_STATES = frozenset({"succeeded", "failed", "cancelled"})
TERMINAL_TRANSITIONS = frozenset({"succeeded", "failed", "cancelled"})
_UNSET = object()


class RuntimeError(Exception):
    """Структурированная ошибка проверки или выполнения runtime."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        result = {"code": self.code, "message": self.message}
        if self.details:
            result["details"] = copy.deepcopy(self.details)
        return result


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError("contract_violation", f"{field_name} должен быть непустой строкой", field=field_name)
    return value


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError("contract_violation", f"{field_name} должен быть объектом", field=field_name)
    return dict(value)


@dataclass(frozen=True)
class Node:
    node_id: str
    input_contract: str
    output_contract: str
    outcomes: tuple[str, ...]
    transitions: Mapping[str, str]
    required_outputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        node_id = _required_text(self.node_id, "node_id")
        input_contract = _required_text(self.input_contract, "input_contract")
        output_contract = _required_text(self.output_contract, "output_contract")
        if not isinstance(self.outcomes, (tuple, list)):
            raise RuntimeError("contract_violation", "outcomes узла должны быть списком строк", node_id=node_id)
        outcomes = tuple(self.outcomes)
        if not outcomes or any(not isinstance(item, str) or not item for item in outcomes):
            raise RuntimeError("contract_violation", "Узел должен иметь непустые outcomes", node_id=node_id)
        if len(set(outcomes)) != len(outcomes):
            raise RuntimeError("contract_violation", "outcomes узла должны быть уникальны", node_id=node_id)
        if not isinstance(self.transitions, Mapping):
            raise RuntimeError("contract_violation", "transitions узла должны быть объектом", node_id=node_id)
        transitions = dict(self.transitions)
        if set(transitions) != set(outcomes):
            raise RuntimeError("contract_violation", "Для каждого outcome нужен переход", node_id=node_id)
        if any(not isinstance(key, str) or not isinstance(value, str) or not value for key, value in transitions.items()):
            raise RuntimeError("contract_violation", "Переходы узла должны быть строками", node_id=node_id)
        if not isinstance(self.required_outputs, (tuple, list)):
            raise RuntimeError("contract_violation", "required_outputs должны быть списком строк", node_id=node_id)
        required_outputs = tuple(self.required_outputs)
        if any(not isinstance(item, str) or not item for item in required_outputs):
            raise RuntimeError("contract_violation", "required_outputs должны быть строками", node_id=node_id)
        object.__setattr__(self, "node_id", node_id)
        object.__setattr__(self, "input_contract", input_contract)
        object.__setattr__(self, "output_contract", output_contract)
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "transitions", MappingProxyType(transitions))
        object.__setattr__(self, "required_outputs", required_outputs)


@dataclass(frozen=True)
class Graph:
    graph_id: str
    version: int
    entry_node: str
    nodes: Mapping[str, Node]

    def __post_init__(self) -> None:
        graph_id = _required_text(self.graph_id, "graph_id")
        if isinstance(self.version, bool) or not isinstance(self.version, int) or self.version < 1:
            raise RuntimeError("contract_violation", "version графа должен быть положительным целым числом")
        entry_node = _required_text(self.entry_node, "entry_node")
        raw_nodes = _mapping(self.nodes, "nodes")
        if not raw_nodes or entry_node not in raw_nodes:
            raise RuntimeError("contract_violation", "entry_node должен ссылаться на существующий узел")
        normalized: dict[str, Node] = {}
        for key, node in raw_nodes.items():
            if not isinstance(key, str) or not isinstance(node, Node) or key != node.node_id:
                raise RuntimeError("contract_violation", "Ключи nodes должны совпадать с node_id")
            normalized[key] = node
        for node in normalized.values():
            for target in node.transitions.values():
                if target not in normalized and target not in TERMINAL_TRANSITIONS:
                    raise RuntimeError("contract_violation", "Переход ссылается на неизвестный узел", node_id=node.node_id, target=target)
        object.__setattr__(self, "graph_id", graph_id)
        object.__setattr__(self, "entry_node", entry_node)
        object.__setattr__(self, "nodes", MappingProxyType(normalized))

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Graph":
        raw = _mapping(value, "graph")
        nodes_raw = raw.get("nodes")
        if isinstance(nodes_raw, list):
            normalized_list: dict[str, Mapping[str, Any]] = {}
            for index, item in enumerate(nodes_raw):
                if not isinstance(item, Mapping):
                    raise RuntimeError("contract_violation", "Элемент graph.nodes должен быть объектом", index=index)
                node_id = item.get("node_id")
                if not isinstance(node_id, str) or not node_id.strip():
                    raise RuntimeError("contract_violation", "Элемент graph.nodes должен иметь node_id", index=index)
                if node_id in normalized_list:
                    raise RuntimeError("contract_violation", "node_id в graph.nodes должен быть уникальным", node_id=node_id)
                normalized_list[node_id] = dict(item)
            nodes_raw = normalized_list
        if not isinstance(nodes_raw, Mapping):
            raise RuntimeError("contract_violation", "graph.nodes должен быть объектом или списком")
        nodes: dict[str, Node] = {}
        for key, node in nodes_raw.items():
            if isinstance(node, Node):
                nodes[key] = node
                continue
            if not isinstance(node, Mapping):
                raise RuntimeError("contract_violation", "Описание узла должно быть объектом", node_id=key)
            node_data = dict(node)
            nodes[key] = Node(
                node_id=node_data.get("node_id", key), input_contract=node_data.get("input_contract"),
                output_contract=node_data.get("output_contract"), outcomes=node_data.get("outcomes", ()),
                transitions=node_data.get("transitions", {}), required_outputs=node_data.get("required_outputs", ()),
            )
        return cls(raw.get("graph_id"), raw.get("version"), raw.get("entry_node"), nodes)


@dataclass(frozen=True)
class WaitState:
    wait_id: str
    node_id: str
    kind: str
    question: str | None = None
    reason: str | None = None
    answer: Any = None

    def __post_init__(self) -> None:
        _required_text(self.wait_id, "wait_id")
        _required_text(self.node_id, "node_id")
        if not isinstance(self.kind, str) or self.kind not in {"user_input", "blocker"}:
            raise RuntimeError("contract_violation", "Неизвестный вид ожидания", kind=self.kind)
        if self.question is not None and not isinstance(self.question, str):
            raise RuntimeError("contract_violation", "question должен быть строкой или null")
        if self.reason is not None and not isinstance(self.reason, str):
            raise RuntimeError("contract_violation", "reason должен быть строкой или null")

    def to_dict(self) -> dict[str, Any]:
        return {"wait_id": self.wait_id, "node_id": self.node_id, "kind": self.kind,
                "question": self.question, "reason": self.reason, "answer": copy.deepcopy(self.answer)}


@dataclass(frozen=True)
class NodeResult:
    node_id: str
    outcome: str
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    data: Mapping[str, Any] = field(default_factory=dict)
    error: Any = None
    wait: WaitState | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"node_id": self.node_id, "outcome": self.outcome,
                "artifacts": copy.deepcopy(dict(self.artifacts)), "data": copy.deepcopy(dict(self.data)),
                "error": copy.deepcopy(self.error), "wait": self.wait.to_dict() if self.wait else None}


def validate_node_result(node: Node, result: NodeResult) -> None:
    """Общая структурная проверка; не проверяет семантику или тела в repository."""
    if not isinstance(result, NodeResult):
        raise RuntimeError("contract_violation", "Результат должен быть NodeResult", node_id=node.node_id)
    if result.node_id != node.node_id:
        raise RuntimeError("node_mismatch", "Результат относится к другому узлу", expected=node.node_id, actual=result.node_id)
    if not isinstance(result.outcome, str) or result.outcome not in node.outcomes:
        raise RuntimeError("unknown_outcome", "Исход не объявлен узлом", node_id=node.node_id, outcome=result.outcome)
    if not isinstance(result.data, Mapping) or not isinstance(result.artifacts, Mapping):
        raise RuntimeError("contract_violation", "data и artifacts результата должны быть объектами", node_id=node.node_id)
    _validate_result_artifacts(result.artifacts, node.node_id)
    missing = [key for key in node.required_outputs if key not in result.data and key not in result.artifacts]
    if missing:
        raise RuntimeError("contract_violation", "В результате отсутствуют обязательные выходы", node_id=node.node_id, missing=missing)


def _validate_result_artifacts(artifacts: Mapping[str, Any], node_id: str) -> None:
    for artifact_key, artifact in artifacts.items():
        if not isinstance(artifact_key, str) or not artifact_key.strip():
            raise RuntimeError("contract_violation", "Ключ артефакта должен быть непустой строкой", node_id=node_id)
        if not isinstance(artifact, Mapping):
            raise RuntimeError("contract_violation", "Артефакт должен быть объектом", node_id=node_id, artifact=artifact_key)
        payload = dict(artifact)
        for field_name in ("ref", "contract", "role", "sha256"):
            if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
                raise RuntimeError("contract_violation", "Артефакт содержит некорректное поле", node_id=node_id,
                                   artifact=artifact_key, field=field_name)
        if re.fullmatch(r"[0-9a-fA-F]{64}", payload["sha256"]) is None:
            raise RuntimeError("contract_violation", "sha256 артефакта должен быть 64-значной hex-строкой",
                               node_id=node_id, artifact=artifact_key)
        if "value" not in payload and "uri" not in payload:
            raise RuntimeError("contract_violation", "Артефакт должен содержать value или uri",
                               node_id=node_id, artifact=artifact_key)
        if "uri" in payload and (not isinstance(payload["uri"], str) or not payload["uri"].strip()):
            raise RuntimeError("contract_violation", "uri артефакта должен быть непустой строкой",
                               node_id=node_id, artifact=artifact_key)


@dataclass
class WorkflowRun:
    run_id: str
    task_ref: str | None
    graph_ref: str
    graph_version: int
    phase: str
    state: str
    current_node: str | None
    inputs: dict[str, Any]
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    wait: WaitState | None = None
    last_result: NodeResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"run_id": self.run_id, "task_ref": self.task_ref, "graph_ref": self.graph_ref,
                "graph_version": self.graph_version, "phase": self.phase, "state": self.state,
                "current_node": self.current_node, "inputs": copy.deepcopy(self.inputs),
                "results": copy.deepcopy(self.results), "wait": self.wait.to_dict() if self.wait else None,
                "last_result": self.last_result.to_dict() if self.last_result else None}


Executor = Callable[[Node, Mapping[str, Any], WorkflowRun], NodeResult | WaitState]


class GraphRuntime:
    """Детерминированный движок одного in-memory запуска."""

    def __init__(self) -> None:
        self._runs: dict[str, tuple[Graph, WorkflowRun]] = {}
        self._wait_sequence = 0

    def create_run(self, graph: Graph | Mapping[str, Any], inputs: Mapping[str, Any], *, task_ref: str | None = None,
                   run_id: str | None = None, phase: str = "request") -> WorkflowRun:
        graph = graph if isinstance(graph, Graph) else Graph.from_dict(graph)
        input_data = copy.deepcopy(_mapping(inputs, "inputs"))
        if task_ref is not None:
            _required_text(task_ref, "task_ref")
        run_id = run_id or f"RUN-{uuid.uuid4().hex[:12]}"
        _required_text(run_id, "run_id")
        if not isinstance(phase, str) or phase not in {"request", "preparation", "execution"}:
            raise RuntimeError("contract_violation", "Неизвестная phase запуска")
        if run_id in self._runs:
            raise RuntimeError("contract_violation", "run_id уже существует", run_id=run_id)
        run = WorkflowRun(run_id, task_ref, graph.graph_id, graph.version, phase, "created", graph.entry_node, input_data)
        self._runs[run_id] = (graph, run)
        return self.inspect_run(run_id)

    def inspect_run(self, run_id: str) -> WorkflowRun:
        _, run = self._get(run_id)
        return copy.deepcopy(run)

    def step(self, run_id: str, executor: Executor) -> NodeResult | WaitState:
        graph, run = self._get(run_id)
        self._ensure_callable(executor)
        if run.state in TERMINAL_STATES or run.state in {"waiting_input", "blocked"}:
            raise RuntimeError("invalid_state", "Запуск нельзя обработать в текущем состоянии", state=run.state)
        node = graph.nodes.get(run.current_node)
        if node is None:
            raise RuntimeError("contract_violation", "Текущий узел не найден", node_id=run.current_node)
        return self._execute(graph, run, node, executor)

    def resume(self, run_id: str, answer: Any, executor: Executor, *, wait_id: str | None = None,
               node_id: str | None = None) -> NodeResult | WaitState:
        graph, run = self._get(run_id)
        self._ensure_callable(executor)
        if run.state != "waiting_input" or run.wait is None:
            raise RuntimeError("invalid_state", "Возобновить можно только waiting_input", state=run.state)
        if wait_id is not None and wait_id != run.wait.wait_id:
            raise RuntimeError("stale_wait", "Ожидание уже изменилось", expected=run.wait.wait_id, actual=wait_id)
        if node_id is not None and node_id != run.wait.node_id:
            raise RuntimeError("node_mismatch", "Ответ относится к другому узлу", expected=run.wait.node_id, actual=node_id)
        node = graph.nodes.get(run.wait.node_id)
        if node is None:
            raise RuntimeError("contract_violation", "Узел ожидания не найден", node_id=run.wait.node_id)
        return self._execute(graph, run, node, executor, wait_answer=answer)

    def resume_blocked(self, run_id: str, executor: Executor, *, wait_id: str | None = None,
                       node_id: str | None = None, answer: Any = None) -> NodeResult | WaitState:
        """Повторно запускает узел после устранения внешней причины блокировки."""
        graph, run = self._get(run_id)
        self._ensure_callable(executor)
        if run.state != "blocked" or run.wait is None or run.wait.kind != "blocker":
            raise RuntimeError("invalid_state", "Возобновить можно только blocked-запуск с blocker wait", state=run.state)
        if wait_id is not None and wait_id != run.wait.wait_id:
            raise RuntimeError("stale_wait", "Ожидание уже изменилось", expected=run.wait.wait_id, actual=wait_id)
        if node_id is not None and node_id != run.wait.node_id:
            raise RuntimeError("node_mismatch", "Ответ относится к другому узлу", expected=run.wait.node_id, actual=node_id)
        node = graph.nodes.get(run.wait.node_id)
        if node is None:
            raise RuntimeError("contract_violation", "Узел блокировки не найден", node_id=run.wait.node_id)
        return self._execute(graph, run, node, executor, wait_answer=answer)

    def cancel(self, run_id: str, reason: str) -> WorkflowRun:
        _, run = self._get(run_id)
        _required_text(reason, "reason")
        if run.state in TERMINAL_STATES:
            raise RuntimeError("invalid_state", "Терминальный запуск нельзя отменить", state=run.state)
        run.state = "cancelled"
        run.wait = None
        return self.inspect_run(run_id)

    def _execute(self, graph: Graph, run: WorkflowRun, node: Node, executor: Executor, *,
                 wait_answer: Any = _UNSET) -> NodeResult | WaitState:
        working_run = copy.deepcopy(run)
        working_run.state = "running"
        if wait_answer is not _UNSET and working_run.wait is not None:
            wait = working_run.wait
            working_run.wait = WaitState(wait.wait_id, wait.node_id, wait.kind, wait.question, wait.reason, wait_answer)
        try:
            result = executor(node, copy.deepcopy(working_run.inputs), copy.deepcopy(working_run))
        except RuntimeError:
            raise
        except Exception as exc:
            run.state = "failed"
            run.wait = None
            raise RuntimeError("execution_failure", "Исполнитель узла завершился ошибкой", node_id=node.node_id, error=type(exc).__name__) from exc
        if isinstance(result, WaitState):
            result = NodeResult(node.node_id, "needs_input", data={}, wait=result)
        if not isinstance(result, NodeResult):
            run.state = "failed"
            run.wait = None
            raise RuntimeError("contract_violation", "Исполнитель должен вернуть NodeResult или WaitState", node_id=node.node_id)
        self._validate_result(node, result)
        working_run.last_result = copy.deepcopy(result)
        working_run.results[node.node_id] = result.to_dict()
        if result.outcome == "needs_input":
            if result.wait is None:
                raise RuntimeError("contract_violation", "needs_input требует wait", node_id=node.node_id)
            working_run.wait = self._normalize_wait(node, result.wait, "user_input")
            working_run.state = "waiting_input"
            self._commit(run, working_run)
            return copy.deepcopy(working_run.wait)
        working_run.wait = None
        if result.outcome == "blocked":
            wait = result.wait or WaitState(self._next_wait_id(), node.node_id, "blocker", reason="Узел заблокирован")
            working_run.wait = self._normalize_wait(node, wait, "blocker")
            working_run.state = "blocked"
            self._commit(run, working_run)
            return copy.deepcopy(result)
        target = node.transitions[result.outcome]
        if target in TERMINAL_TRANSITIONS:
            working_run.current_node = None
            working_run.state = target
        else:
            working_run.current_node = target
            working_run.state = "running"
        self._commit(run, working_run)
        return copy.deepcopy(result)

    def _validate_result(self, node: Node, result: NodeResult) -> None:
        validate_node_result(node, result)

    @staticmethod
    def _validate_artifacts(artifacts: Mapping[str, Any], node_id: str) -> None:
        _validate_result_artifacts(artifacts, node_id)

    def _normalize_wait(self, node: Node, wait: WaitState, kind: str) -> WaitState:
        if wait.node_id != node.node_id:
            raise RuntimeError("node_mismatch", "Ожидание относится к другому узлу", expected=node.node_id, actual=wait.node_id)
        if wait.kind != kind:
            raise RuntimeError("contract_violation", "Неверный вид ожидания для исхода узла", expected=kind, actual=wait.kind)
        return WaitState(wait.wait_id or self._next_wait_id(), node.node_id, kind, wait.question, wait.reason,
                         copy.deepcopy(wait.answer))

    @staticmethod
    def _commit(target: WorkflowRun, source: WorkflowRun) -> None:
        target.state = source.state
        target.current_node = source.current_node
        target.inputs = copy.deepcopy(source.inputs)
        target.results = copy.deepcopy(source.results)
        target.wait = copy.deepcopy(source.wait)
        target.last_result = copy.deepcopy(source.last_result)

    def _next_wait_id(self) -> str:
        self._wait_sequence += 1
        return f"WAIT-{self._wait_sequence:04d}"

    def _get(self, run_id: str) -> tuple[Graph, WorkflowRun]:
        if not isinstance(run_id, str) or run_id not in self._runs:
            raise RuntimeError("run_not_found", "Запуск не найден", run_id=run_id)
        return self._runs[run_id]

    @staticmethod
    def _ensure_callable(executor: Any) -> None:
        if not callable(executor):
            raise RuntimeError("contract_violation", "executor должен быть вызываемым объектом")


__all__ = ["Graph", "GraphRuntime", "Node", "NodeResult", "RuntimeError", "WaitState", "WorkflowRun", "validate_node_result"]
