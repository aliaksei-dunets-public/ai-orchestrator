"""Доверенные роли: компоненты дают результаты, фасады сохраняют guards."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from .runtime_contracts import Graph
from .workflow_binding import read_binding
from .workflow_builder import ResolvedWorkflow, WorkflowBuilder, canonical, digest
from .workflow_execution import WorkflowExecutor, reject
import json


@dataclass(frozen=True)
class ComponentRole:
    role: str
    phase: str
    instance_id: str
    inputs: dict
    outputs: dict
    outcomes: dict
    handler: Callable


class WorkflowRoleRegistry:
    def __init__(self):
        self._roles = {}

    def register(self, role: ComponentRole):
        allowed = {"preparation": {"context", "analysis", "planning", "plan_review"},
                   "execution": {"code_review", "testing", "documentation", "final_validation"}}
        if (not isinstance(role, ComponentRole) or role.role not in allowed.get(role.phase, set())
                or not role.instance_id or not callable(role.handler)
                or (role.phase, role.role) in self._roles):
            reject("invalid_role", "Нужна уникальная разрешённая роль; lifecycle guards не заменяются")
        # Схемы caller-а не должны меняться после регистрации.
        self._roles[role.phase, role.role] = ComponentRole(role.role, role.phase, role.instance_id,
            copy.deepcopy(role.inputs), copy.deepcopy(role.outputs), copy.deepcopy(role.outcomes), role.handler)

    def get(self, phase, role):
        if (phase, role) not in self._roles:
            reject("role_unavailable", "Для этапа не зарегистрирован handler")
        return self._roles[phase, role]


def component_workflow(workflow, instance_id):
    snapshot = workflow.to_dict()
    matches = [n for n in WorkflowBuilder._walk(snapshot["tree"]) if n["id"] == instance_id]
    if len(matches) != 1 or matches[0] is snapshot["tree"]:
        reject("unknown_component", "Нужен qualified ID экземпляра компонента")
    node = copy.deepcopy(matches[0])
    definition = node["definition"]
    terminals = {o: "failed" if o in {"failed", "failure", "changes_required"} else "succeeded"
                 for o in definition["outcomes"] if o not in {"needs_input", "blocked"}}
    # Wait outcomes нужны runtime узлу, но не внешнему exit standalone wrapper.
    if "children" in node:
        if set(terminals) != set(definition["outcomes"]):
            reject("invalid_role", "Composite wait должен оставаться внутри компонента")
        tree = node
        tree["inputs"], tree["transitions"] = {}, {}
        tree["definition"]["component"]["kind"] = "workflow"
    else:
        name = instance_id.rsplit(".", 1)[-1]
        node["inputs"] = {p: "input:" + p for p in definition.get("inputs", {})}
        node["transitions"] = {o: name if o in {"needs_input", "blocked"} else "exit:" + o
                               for o in definition["outcomes"]}
        tree = {"id": "role-wrapper", "ref": "internal/role-wrapper@1", "inputs": {}, "transitions": {},
            "children": {name: node}, "effects": node["effects"], "config": {}, "execution": {},
            "provenance": {}, "definition": {"component": {"id": "internal/role-wrapper", "version": 1,
                "kind": "workflow", "entry": name}, "inputs": definition.get("inputs", {}),
                "outputs": definition.get("outputs", {}),
                "outcomes": {o: definition["outcomes"][o] for o in terminals},
                "exits": {o: {p: name + "." + p for p in definition["outcomes"][o]} for o in terminals}}}
    flat, leaves = {}, {}
    WorkflowBuilder(None)._compile(tree, terminals, flat, leaves)
    graph = Graph("component/" + instance_id, 1, WorkflowBuilder._entry(tree), flat)
    data = {"graph_id": graph.graph_id, "version": graph.version, "entry_node": graph.entry_node,
            "nodes": {k: {"node_id": n.node_id, "input_contract": n.input_contract,
                "output_contract": n.output_contract, "outcomes": list(n.outcomes),
                "transitions": dict(n.transitions),
                "required_outputs_by_outcome": {o: list(p) for o, p in n.required_outputs_by_outcome.items()}}
                      for k, n in flat.items()}}
    snapshot.pop("digest")
    parent_digest = workflow.digest
    snapshot.update(tree=tree, graph=data, leaves=leaves,
                    component_binding={"parent_digest": parent_digest, "instance_id": instance_id})
    snapshot["runtime"]["node_limits"] = {k: v for k, v in snapshot["runtime"]["node_limits"].items() if k in flat}
    snapshot["digest"] = "workflow/v1:" + digest(snapshot)
    return ResolvedWorkflow(graph, canonical(snapshot)), definition


@dataclass
class RoleExecution:
    executor: WorkflowExecutor
    role: ComponentRole
    parent_digest: str
    owner: str
    request: dict


def start_role(repository, binding, roles, role_name, phase, executors, inputs, guard, fallbacks, request, owner):
    frozen = read_binding(repository, binding)
    role = roles.get(phase, role_name)
    resolved, definition = component_workflow(frozen, role.instance_id)
    if any(getattr(role, key) != definition.get(key, {}) for key in ("inputs", "outputs", "outcomes")):
        reject("role_contract_mismatch", "Компонент несовместим с зарегистрированным role contract")
    if resolved.to_dict()["tree"]["effects"].get("writes_task_manager"):
        reject("invalid_role", "Task Manager effects принадлежат guarded facade, не role executor")
    executor = WorkflowExecutor(repository.project_root, resolved, executors, guard=guard, fallbacks=fallbacks)
    executor.start(inputs, task_ref=request["task"]["id"],
                   task_definition_version=request["task"]["definition_version"], phase=phase)
    return RoleExecution(executor, role, frozen.digest, owner, copy.deepcopy(request))


def role_envelope(component, registered, owner, role, phase, binding):
    if (not isinstance(component, RoleExecution) or registered.get(id(component)) is not component
            or component.owner != owner or component.role.role != role or component.role.phase != phase
            or binding is None or component.parent_digest != binding["digest"]):
        reject("role_binding_mismatch", "Компонент не принадлежит текущему этапу/snapshot")
    component.executor.guard()
    state = component.executor.inspect()
    if state["pending_effect"] or state["run"]["state"] not in {"succeeded", "failed"} or state["result"] is None:
        reject("component_incomplete", "Сначала завершите и сверьте исполнение компонента")
    return component.role.handler(copy.deepcopy(state["result"]), copy.deepcopy(component.request),
                                  copy.deepcopy(state["evidence"]))


def testing_gate_handler(repository):
    """Мост учебного core/testing@1 в полный gate: totals берутся из tool evidence."""
    def handle(result, request, evidence):
        records = [json.loads(repository.get(r["ref"], r["role"], r["version"]).content) for r in evidence]
        executions = [v["outputs"]["execution_record"] for v in records
                      if "execution_record" in v["outputs"] and v["receipt"]["kind"] in {"tool", "deterministic"}
                      and v["output_artifacts"]["execution_record"]["contract"] == "test-execution-record/v1"]
        if not executions:
            reject("missing_testing_evidence", "Нужен фактический execution_record, summary недостаточен")
        execution = executions[-1]
        if execution["passed"] + execution["failed"] < 1:
            reject("missing_testing_evidence", "Пустой test execution не подтверждает passed testing")
        summary = result["outputs"]["result"]
        outcome = result["outcome"]
        expected = "failed" if execution["failed"] else "passed"
        if outcome != expected or summary["status"] != expected:
            reject("inconsistent_testing_evidence", "Summary скрывает фактический результат tool")
        refs = [f'{r["ref"]}:{r["role"]}:{r["version"]}' for r in evidence]
        return {"outcome": outcome, "payload": {"summary": summary["summary"],
            "implementation_revision": request["source_revision"], "candidate_revision": request["candidate_revision"],
            "totals": {"checks": execution["passed"] + execution["failed"], "passed": execution["passed"],
                       "failed": execution["failed"], "skipped": 0}, "evidence_refs": refs}}
    return handle


def documentation_gate_handler(repository, *, source_adjacent_changed: bool):
    """Caller явно сообщает source-adjacent влияние; no_change сверяется с impact."""
    if type(source_adjacent_changed) is not bool:
        reject("invalid_role", "source_adjacent_changed должен быть явным bool")
    def handle(result, request, evidence):
        records = [json.loads(repository.get(r["ref"], r["role"], r["version"]).content) for r in evidence]
        impacts = [v["outputs"]["impact"] for v in records if "impact" in v["outputs"]]
        if not impacts:
            reject("missing_documentation_evidence", "Нужен фактический impact")
        impact = impacts[-1]
        summary = result["outputs"]["result"]
        outcome = result["outcome"]
        if outcome != summary["status"] or (outcome == "no_change" and impact["impacted"]):
            reject("inconsistent_documentation_evidence", "Documentation summary противоречит impact")
        return {"outcome": outcome, "payload": {"summary": summary["summary"],
            "implementation_revision": request["source_revision"], "candidate_revision": request["candidate_revision"],
            "impacted": impact["impacted"], "source_adjacent_changed": source_adjacent_changed,
            "targets": impact["targets"],
            "evidence_refs": [f'{r["ref"]}:{r["role"]}:{r["version"]}' for r in evidence]}}
    return handle


__all__ = ["ComponentRole", "WorkflowRoleRegistry", "RoleExecution", "testing_gate_handler", "documentation_gate_handler"]
