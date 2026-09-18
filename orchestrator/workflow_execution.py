"""Явное исполнение одного узла; host adapters остаются вне Graph Runtime."""
from __future__ import annotations

import copy
import json
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .agent_runtime import AgentGraphRuntime
from .artifact_repository import ArtifactRepository
from .runtime_contracts import Graph, NodeResult, WaitState
from .workflow_builder import ResolvedWorkflow, canonical, digest, validate_value


class WorkflowExecutionError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def reject(code, message):
    raise WorkflowExecutionError(code, message)


@dataclass(frozen=True)
class ModelAdapter:
    """Один вызов модели, без subagents. Identity проверяется по ответу transport.

    invoke(request) -> {result: {outcome, outputs, wait?}, provider, model}.
    available(profile) -> bool проверяет именно provider/model/reasoning.
    Регистрация callable — доверенная операция host, TOML не загружает Python.
    """

    executor_ref: str
    provider: str
    available: Callable
    invoke: Callable


class ExecutorRegistry:
    def __init__(self):
        self._models, self._capabilities = {}, {}

    def register_model(self, adapter: ModelAdapter):
        if (not isinstance(adapter, ModelAdapter) or not isinstance(adapter.executor_ref, str)
                or not adapter.executor_ref.strip() or not isinstance(adapter.provider, str) or not adapter.provider.strip()
                or not callable(adapter.available) or not callable(adapter.invoke)
                or adapter.provider in self._models):
            reject("invalid_adapter", "Нужен уникальный provider и корректный single-agent adapter")
        self._models[adapter.provider] = adapter

    def register_capability(self, capability: str, invoke: Callable, *, executor_ref: str):
        if (not isinstance(capability, str) or not capability.strip() or capability in self._capabilities
                or not isinstance(executor_ref, str) or not executor_ref.strip() or not callable(invoke)):
            reject("invalid_adapter", "Нужна уникальная capability и доверенный callable")
        self._capabilities[capability] = (executor_ref, invoke)

    def select(self, execution, profiles, fallbacks):
        if execution["kind"] != "agent":
            capability = execution["capability"]
            if capability not in self._capabilities:
                reject("capability_unavailable", "Capability не зарегистрирована: " + capability)
            ref, invoke = self._capabilities[capability]
            return invoke, {"kind": execution["kind"], "executor_ref": ref, "capability": capability}
        requested = execution["model_profile"]
        for name in [requested] + fallbacks.get(requested, []):
            profile = profiles[name]
            adapter = self._models.get(profile["provider"])
            if adapter is None:
                continue
            try:
                available = adapter.available(copy.deepcopy(profile))
            except Exception as exc:
                reject("availability_failed", "Host не смог проверить доступность модели: " + type(exc).__name__)
            if type(available) is not bool:
                reject("invalid_adapter", "available должен возвращать bool")
            if available:
                return adapter.invoke, {"kind": "agent", "executor_ref": adapter.executor_ref,
                    "requested_profile": requested, "executed_profile": name, "provider": profile["provider"],
                    "model": profile["model"], "reasoning": profile.get("reasoning"),
                    "fallback_reason": "requested_model_unavailable" if name != requested else None,
                    "policy": "single_agent"}
        reject("model_unavailable", "Нет доступной модели для профиля " + requested)


class WorkflowExecutor:
    """Один snapshot, in-memory run и scoped артефакты. step вызывается caller-ом.

    Неопределённый/невалидный ответ после вызова запрещает повтор transport;
    recover_result принимает сверенный результат без нового physical effect.
    """

    max_artifact_bytes = 2 * 1024 * 1024

    def __init__(self, project_root: Path, workflow: ResolvedWorkflow, executors: ExecutorRegistry,
                 *, fallbacks=None, guard: Callable | None = None):
        self.repository = ArtifactRepository(project_root)
        self.workflow, self.executors = workflow, executors
        self._snapshot = workflow.to_dict()
        signature = self._snapshot.pop("digest")
        if (signature != "workflow/v1:" + digest(self._snapshot)
                or Graph.from_dict(self._snapshot["graph"]) != workflow.graph):
            reject("integrity_error", "Graph или digest отличаются от workflow snapshot")
        self._snapshot["digest"] = signature
        if len(canonical(self._snapshot)) > self.max_artifact_bytes:
            reject("contract_mismatch", "Snapshot превышает 2 MiB")
        self._fallbacks = copy.deepcopy(fallbacks or {})
        profiles = self._snapshot["model_profiles"]
        if (not isinstance(self._fallbacks, dict) or any(k not in profiles or not isinstance(v, list)
                or any(not isinstance(p, str) or p not in profiles or p == k for p in v)
                or len(v) != len(set(v)) for k, v in self._fallbacks.items())):
            reject("invalid_fallback", "Fallback требует явный список существующих профилей без повторов")
        self.guard = guard or (lambda: None)
        self.runtime = AgentGraphRuntime()
        self._lock = threading.RLock()
        self._run_id = None
        self._ref = "WF-" + uuid.uuid4().hex
        self._frames = []
        self._pending = None
        self._final = None
        self._evidence = []

    def start(self, inputs, *, task_ref=None, task_definition_version=None, phase="execution"):
        with self._lock:
            if self._run_id is not None:
                reject("invalid_state", "Executor уже связан с run")
            self.guard()
            root = self._snapshot["tree"]
            self._validate_ports(inputs, root["definition"].get("inputs", {}))
            self.repository.put_json(self._ref, "workflow_definition", "v1", self._snapshot,
                                     contract="workflow-definition/v1")
            record = self.repository.put_json(self._ref, "workflow_inputs", "v1", {"inputs": inputs,
                "execution_policy": {"mode": "single_agent", "fallbacks": self._fallbacks}},
                                               contract="workflow-inputs/v1")
            root_inputs = {p: self._artifact(self.repository.put_json(self._ref, "input-" + digest(p)[:16],
                "v1", inputs[p], contract=cid), None, p, cid, inputs[p])
                           for p, cid in root["definition"].get("inputs", {}).items()}
            self._frames = [{"node": root, "inputs": root_inputs, "outputs": {}}]
            self._enter(root["definition"]["component"]["entry"], self._frames)
            run = self.runtime.create_run(self.workflow.graph, {"workflow_digest": self._snapshot["digest"]},
                task_ref=task_ref, task_definition_version=task_definition_version,
                phase=phase,
                **self.workflow.runtime_options)
            self._run_id = run.run_id
            return self.inspect()

    def _validate_ports(self, values, contracts):
        if not isinstance(values, dict) or set(values) != set(contracts):
            reject("contract_mismatch", "Нужны ровно объявленные входные порты")
        if len(canonical(values)) > self.max_artifact_bytes:
            reject("contract_mismatch", "Payload превышает 2 MiB")
        for port, cid in contracts.items():
            validate_value(values[port], self._snapshot["contracts"][cid], port)

    @staticmethod
    def _artifact(record, field, port, contract, value):
        return {"ref": record.ref, "role": record.role, "version": record.version,
                "record": record.to_dict(), "field": field, "port": port, "contract": contract,
                "sha256": digest(value), "value": copy.deepcopy(value)}

    def _value(self, artifact):
        record = artifact["record"]
        stored = self.repository.get(record["ref"], record["role"], record["version"])
        value = json.loads(stored.content)
        if artifact["field"] is not None:
            value = value[artifact["field"]][artifact["port"]]
        if stored.record.to_dict() != record or value != artifact["value"] or digest(value) != artifact["sha256"]:
            reject("integrity_error", "Привязанный артефакт изменён")
        return copy.deepcopy(value)

    @staticmethod
    def _resolve(frame, binding):
        if binding.startswith("input:"):
            return frame["inputs"][binding[6:]]
        name, port = binding.split(".")
        try:
            return frame["outputs"][name][port]
        except KeyError:
            reject("unavailable_artifact", "Нет артефакта для binding " + binding)

    def _enter(self, name, frames):
        frame = frames[-1]
        node = frame["node"]["children"][name]
        if "children" in node:
            inputs = {port: self._resolve(frame, binding) for port, binding in node["inputs"].items()}
            # Новый вызов подграфа не использует outputs предыдущего вызова.
            frame["outputs"].pop(name, None)
            frames.append({"node": node, "inputs": inputs, "outputs": {}})
            self._enter(node["definition"]["component"]["entry"], frames)

    def _run(self, expected_revision):
        if self._run_id is None:
            reject("invalid_state", "Сначала start")
        run = self.runtime.inspect_run(self._run_id)
        if type(expected_revision) is not int or run.revision != expected_revision:
            reject("run_revision_conflict", "Нужна текущая process revision")
        return run

    def request(self):
        with self._lock:
            if self._run_id is None:
                reject("invalid_state", "Сначала start")
            run = self.runtime.inspect_run(self._run_id)
            if run.current_node is None:
                reject("invalid_state", "Run завершён")
            frame = self._frames[-1]
            name = run.current_node.rsplit(".", 1)[-1]
            node = frame["node"]["children"][name]
            artifacts = {p: self._resolve(frame, b) for p, b in node["inputs"].items()}
            inputs = {p: self._value(a) for p, a in artifacts.items()}
            self._validate_ports(inputs, node["definition"].get("inputs", {}))
            return {"contract": "workflow-node-request/v1", "run_id": run.run_id, "revision": run.revision,
                    "workflow_digest": self._snapshot["digest"], "node_id": run.current_node,
                    "component_ref": node["ref"], "execution": copy.deepcopy(node["execution"]),
                    "config": copy.deepcopy(node["config"]), "effects": copy.deepcopy(node["effects"]),
                    "inputs": inputs, "input_artifacts": copy.deepcopy(artifacts),
                    "output_contracts": {p: self._snapshot["contracts"][c]
                                         for p, c in node["definition"].get("outputs", {}).items()},
                    "outcomes": copy.deepcopy(node["definition"]["outcomes"]),
                    "resumed_wait": copy.deepcopy(run.resumed_wait)}

    def inspect(self):
        with self._lock:
            return {"run": self.runtime.inspect_run(self._run_id).to_dict() if self._run_id else None,
                    "workflow_digest": self._snapshot["digest"], "pending_effect": copy.deepcopy(self._pending),
                    "execution_policy": {"mode": "single_agent", "fallbacks": copy.deepcopy(self._fallbacks)},
                    "evidence": copy.deepcopy(self._evidence), "result": copy.deepcopy(self._final)}

    def step(self, *, expected_revision):
        with self._lock:
            run = self._run(expected_revision)
            if self._pending:
                reject("unknown_effect", "Сначала сверить принятый/неопределённый physical effect")
            actions = self.runtime.available_actions(run.run_id)
            if run.state in {"created", "running"} and actions["remaining_results"] < 1:
                reject("result_limit_exceeded", "Исчерпан budget")
            if "submit_result" not in actions["actions"]:
                reject("invalid_state", "Сейчас step недоступен")
            if actions["remaining_results"] < 1:
                reject("result_limit_exceeded", "Исчерпан budget")
            self.guard()
            request = self.request()
            invoke, receipt = self.executors.select(request["execution"], self._snapshot["model_profiles"], self._fallbacks)
            request["selected_executor"] = copy.deepcopy(receipt)
            self.guard()
            self._pending = {"request": copy.deepcopy(request), "receipt": receipt}
            try:
                response = invoke(copy.deepcopy(request))
            except Exception as exc:
                raise WorkflowExecutionError("unknown_effect", "Host вызов завершился неопределённо; слепой повтор запрещён") from exc
            return self._accept(response, expected_revision)

    def recover_result(self, response, *, expected_revision, resolution_ref):
        with self._lock:
            self._run(expected_revision)
            if not self._pending or not isinstance(resolution_ref, str) or not resolution_ref.strip():
                reject("invalid_state", "Нужны pending effect и ссылка на сверку результата")
            self._pending["resolution_ref"] = resolution_ref
            return self._accept(response, expected_revision)

    def _advance(self, frames, run, outcome, artifacts):
        name = run.current_node.rsplit(".", 1)[-1]
        frame = frames[-1]
        node = frame["node"]["children"][name]
        frame["outputs"][name] = artifacts  # Удаляет stale optional ports.
        target = node["transitions"][outcome]
        while target.startswith("exit:"):
            exit_outcome = target[5:]
            current = frames[-1]
            bindings = current["node"]["definition"]["exits"][exit_outcome]
            exports = {p: self._resolve(current, b) for p, b in bindings.items()}
            for p, a in exports.items():
                self._value(a)
            scope = frames.pop()["node"]
            if not frames:
                return {"outcome": exit_outcome, "outputs": {p: self._value(a) for p, a in exports.items()},
                        "artifacts": exports}
            name = scope["id"].rsplit(".", 1)[-1]
            frames[-1]["outputs"][name] = exports
            target = scope["transitions"][exit_outcome]
        self._enter(target, frames)
        return None

    def _accept(self, response, expected_revision):
        run = self._run(expected_revision)
        self.guard()
        pending = self._pending
        receipt = pending["receipt"]
        response = json.loads(canonical(response))
        if receipt["kind"] == "agent":
            if (not isinstance(response, dict) or set(response) != {"provider", "model", "result"}
                    or response["provider"] != receipt["provider"] or response["model"] != receipt["model"]):
                reject("executor_mismatch", "Transport не подтвердил выбранные provider/model")
            result = response["result"]
        else:
            result = response
        if not isinstance(result, dict) or set(result) - {"outcome", "outputs", "wait"}:
            reject("contract_mismatch", "Неверный result envelope")
        outcome, outputs = result.get("outcome"), result.get("outputs")
        if not isinstance(outcome, str) or not isinstance(outputs, dict):
            reject("contract_mismatch", "Нужны строковый outcome и объект outputs")
        self.workflow.validate_outputs(run.current_node, outcome, outputs)
        wait = None
        if outcome in {"needs_input", "blocked"}:
            detail = result.get("wait", {})
            if not isinstance(detail, dict) or set(detail) - {"question", "reason"}:
                reject("contract_mismatch", "Неверный wait")
            field = "question" if outcome == "needs_input" else "reason"
            if not isinstance(detail.get(field), str) or not detail[field].strip():
                reject("contract_mismatch", "Нужна причина ожидания")
            wait = WaitState("WAIT-" + uuid.uuid4().hex, run.current_node,
                             "user_input" if outcome == "needs_input" else "blocker", **{field: detail[field]})
        elif "wait" in result:
            reject("contract_mismatch", "wait допустим только для needs_input/blocked")
        value = {"contract": "workflow-node-evidence/v1", "workflow_digest": self._snapshot["digest"],
                 "node_id": run.current_node, "component_ref": pending["request"]["component_ref"],
                 "input_artifacts": pending["request"]["input_artifacts"], "receipt": receipt,
                 "outcome": outcome, "outputs": outputs, "resolution_ref": pending.get("resolution_ref")}
        if len(canonical(value)) > self.max_artifact_bytes:
            reject("contract_mismatch", "Node evidence превышает 2 MiB")
        pending["publication_attempt"] = pending.get("publication_attempt", 0) + 1
        version = "v" + str(run.revision + 1) + "-" + str(pending["publication_attempt"])
        contracts = self._snapshot["leaves"][run.current_node]["outputs"]
        artifacts = {p: self._artifact(self.repository.put_json(self._ref, "output-" + digest(p)[:16],
            version, v, contract=contracts[p]), None, p, contracts[p], v) for p, v in outputs.items()}
        value["output_artifacts"] = {p: a["record"] for p, a in artifacts.items()}
        if len(canonical(value)) > self.max_artifact_bytes:
            reject("contract_mismatch", "Node evidence превышает 2 MiB")
        record = self.repository.put_json(self._ref, "node_evidence", version, value,
                                         contract="workflow-node-evidence/v1")
        frames = copy.deepcopy(self._frames)
        final = self._advance(frames, run, outcome, artifacts) if wait is None else None
        accepted = self.runtime.submit_result(run.run_id, NodeResult(run.current_node, outcome,
            artifacts=artifacts, data={"receipt": receipt, "evidence": record.to_dict()}, wait=wait),
            expected_revision=expected_revision, task_definition_version=run.task_definition_version)
        self._frames, self._final = frames, final
        self._evidence.append(record.to_dict())
        self._pending = None
        return self.inspect()

    def resume_wait(self, *, expected_revision, wait_id, answer=None, resolution=None):
        with self._lock:
            run = self._run(expected_revision)
            if self._pending:
                reject("unknown_effect", "Сначала сверить physical effect")
            self.guard()
            kwargs = {"answer": answer} if run.wait and run.wait.kind == "user_input" else {"resolution": resolution}
            self.runtime.resume_wait(run.run_id, expected_revision=expected_revision,
                task_definition_version=run.task_definition_version, wait_id=wait_id,
                node_id=run.current_node, **kwargs)
            return self.inspect()


__all__ = ["WorkflowExecutor", "ExecutorRegistry", "ModelAdapter", "WorkflowExecutionError"]
