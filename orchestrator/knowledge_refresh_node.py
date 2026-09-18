"""Reusable Workflow Graph node for explicit Project Knowledge refresh policy."""
from __future__ import annotations

import copy
import uuid
from dataclasses import asdict, dataclass
from types import SimpleNamespace
from typing import Any, Mapping

from .knowledge_contracts import KnowledgeError, KnowledgeRefreshResult
from .knowledge_service import ProjectKnowledgeService
from .runtime_contracts import Graph, Node, NodeResult, WaitState


_MODES = {"auto", "incremental", "full"}
_AUTHORIZATION = {"required", "automatic"}
_PURPOSES = {"pre_commit", "maintenance", "recovery"}
_OUTCOMES = ("not_required", "success", "degraded", "stale", "failed", "fallback_required", "needs_input")


@dataclass(frozen=True)
class KnowledgeRefreshPolicy:
    mode: str = "auto"
    authorization: str = "required"
    purpose: str = "pre_commit"
    trusted: bool = False

    def __post_init__(self) -> None:
        if self.mode not in _MODES:
            raise KnowledgeError("validation_failed", "Неизвестный knowledge refresh mode")
        if self.authorization not in _AUTHORIZATION:
            raise KnowledgeError("validation_failed", "Неизвестная authorization policy")
        if self.purpose not in _PURPOSES:
            raise KnowledgeError("validation_failed", "Неизвестный knowledge refresh purpose")
        if type(self.trusted) is not bool:
            raise KnowledgeError("validation_failed", "trusted должен быть bool")
        if self.authorization == "automatic" and not self.trusted:
            raise KnowledgeError("validation_failed", "automatic разрешён только trusted node")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeRefreshRequest:
    policy: KnowledgeRefreshPolicy = KnowledgeRefreshPolicy()
    expected_source_revision: str | None = None
    expected_graph_version: str | None = None
    explicit_decision_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.policy, KnowledgeRefreshPolicy):
            raise KnowledgeError("validation_failed", "policy должен быть KnowledgeRefreshPolicy")
        for value, name in ((self.expected_source_revision, "expected_source_revision"),
                            (self.expected_graph_version, "expected_graph_version"),
                            (self.explicit_decision_ref, "explicit_decision_ref")):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise KnowledgeError("validation_failed", f"{name} должен быть непустой строкой или null")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["policy"] = self.policy.to_dict()
        return value


def knowledge_refresh_graph(*, next_node: str = "succeeded") -> Graph:
    """Return a reusable single-node graph definition for host orchestration."""
    if not isinstance(next_node, str) or not next_node.strip():
        raise KnowledgeError("validation_failed", "next_node должен быть непустой строкой")
    transitions = {outcome: next_node for outcome in _OUTCOMES}
    transitions["needs_input"] = "knowledge_refresh"
    nodes = {
        "knowledge_refresh": Node("knowledge_refresh", "knowledge-refresh-request/v1",
                                   "knowledge-refresh-node/v1", _OUTCOMES, transitions,
                                   required_outputs=("result",))
    }
    if next_node not in {"succeeded", "failed", "cancelled", "knowledge_refresh"}:
        nodes[next_node] = Node(next_node, "knowledge-refresh-next/v1", "knowledge-refresh-next/v1",
                                ("success",), {"success": "succeeded"})
    return Graph("knowledge-refresh-v1", 1, "knowledge_refresh", nodes)


class _LegacyKnowledgeServiceAdapter:
    """Keep TASK-0020's minimal precommit service doubles/source compatible."""

    def __init__(self, service: Any):
        self._service = service

    def status(self):
        return self._service.status()

    def snapshot(self):
        current = self.status().current_snapshot or {}
        return SimpleNamespace(digest=current.get("digest"))

    def refresh_incremental(self, *, allow_full_fallback=True):
        if allow_full_fallback is False:
            # The legacy surface cannot promise strict fallback semantics; the
            # caller still receives its structured result and must inspect it.
            return self._service.precommit_refresh()
        return self._service.precommit_refresh()

    def refresh(self, **kwargs):
        raise KnowledgeError("fallback_required", "Legacy service не поддерживает explicit full refresh")


class KnowledgeRefreshNode:
    """Execute one policy-controlled refresh and return a runtime NodeResult.

    AgentGraphRuntime remains executor-free: the host agent calls ``execute``
    and submits the returned result with normal revision/wait guards.
    """

    contract = "knowledge-refresh-node/v1"

    def __init__(self, service: ProjectKnowledgeService, *, next_node: str = "succeeded"):
        if not callable(getattr(service, "status", None)):
            raise KnowledgeError("validation_failed", "Нужен ProjectKnowledgeService-compatible service")
        if not all(callable(getattr(service, name, None)) for name in ("snapshot", "refresh", "refresh_incremental")):
            if callable(getattr(service, "precommit_refresh", None)):
                service = _LegacyKnowledgeServiceAdapter(service)
            else:
                raise KnowledgeError("validation_failed", "Нужен ProjectKnowledgeService-compatible service")
        self.service = service
        self.graph = knowledge_refresh_graph(next_node=next_node)

    @staticmethod
    def request_from(value: KnowledgeRefreshRequest | Mapping[str, Any]) -> KnowledgeRefreshRequest:
        if isinstance(value, KnowledgeRefreshRequest):
            return value
        if not isinstance(value, Mapping):
            raise KnowledgeError("validation_failed", "Knowledge refresh request должен быть объектом")
        raw_policy = value.get("policy", {})
        if isinstance(raw_policy, KnowledgeRefreshPolicy):
            policy = raw_policy
        elif isinstance(raw_policy, Mapping):
            policy = KnowledgeRefreshPolicy(**dict(raw_policy))
        else:
            raise KnowledgeError("validation_failed", "policy должен быть объектом")
        return KnowledgeRefreshRequest(policy=policy,
            expected_source_revision=value.get("expected_source_revision"),
            expected_graph_version=value.get("expected_graph_version"),
            explicit_decision_ref=value.get("explicit_decision_ref"))

    def execute(self, request: KnowledgeRefreshRequest | Mapping[str, Any], *,
                decision: Mapping[str, Any] | None = None) -> NodeResult:
        request = self.request_from(request)
        policy = request.policy
        status = self.service.status()
        current_revision = self.service.snapshot().digest
        current_graph_version = status.graph.get("version") if status.graph else None
        if request.expected_source_revision and request.expected_source_revision != current_revision:
            return self._result("stale", request, current_revision, current_graph_version,
                                error={"code": "source_drift", "message": "Source revision отличается от ожидаемой"})
        if request.expected_graph_version and request.expected_graph_version != current_graph_version:
            return self._result("stale", request, current_revision, current_graph_version,
                                error={"code": "graph_conflict", "message": "Graph version отличается от ожидаемой"})
        if policy.mode == "full" and policy.authorization == "required":
            approved = isinstance(decision, Mapping) and decision.get("approved") is True
            decision_ref = request.explicit_decision_ref or (decision.get("ref") if isinstance(decision, Mapping) else None)
            if not approved or not isinstance(decision_ref, str) or not decision_ref.strip():
                wait = WaitState("WAIT-KNOWLEDGE-" + uuid.uuid4().hex, "knowledge_refresh", "user_input",
                                  question="Разрешить полную переиндексацию Project Knowledge Graph?", reason=None)
                result = {"status": "awaiting_confirmation", "effective_mode": "full",
                          "commit_allowed": False, "decision_ref": decision_ref,
                          "request": request.to_dict(), "graph_status": status.to_dict()}
                return NodeResult("knowledge_refresh", "needs_input", data={"result": result}, wait=wait)
        if policy.mode == "full":
            refreshed = self.service.refresh(_mode="full-rebuild")
        else:
            refreshed = self.service.refresh_incremental(allow_full_fallback=False)
        return self._map_refresh(refreshed, request, decision)

    def _map_refresh(self, refreshed: KnowledgeRefreshResult, request: KnowledgeRefreshRequest,
                     decision: Mapping[str, Any] | None) -> NodeResult:
        status = self.service.status()
        current_revision = self.service.snapshot().digest
        graph_version = status.graph.get("version") if status.graph else None
        if refreshed.status == "not_required":
            outcome, allowed = "not_required", status.state == "fresh"
        elif refreshed.status == "fallback_required":
            outcome, allowed = "fallback_required", False
        elif refreshed.status == "failed":
            outcome, allowed = ("stale" if status.state == "stale" else "failed"), False
        elif status.state != "fresh":
            outcome, allowed = "stale", False
        elif refreshed.mode == "full-rebuild-fallback":
            outcome, allowed = "degraded", True
        else:
            outcome, allowed = "success", True
        result = {"status": outcome, "effective_mode": refreshed.mode,
                  "commit_allowed": allowed, "source_revision": current_revision,
                  "graph_version": graph_version, "refresh": refreshed.to_dict(),
                  "graph_status": status.to_dict(), "request": request.to_dict()}
        if decision is not None:
            result["decision"] = copy.deepcopy(dict(decision))
        return NodeResult("knowledge_refresh", outcome, data={"result": result},
                          error=refreshed.error)

    @staticmethod
    def _result(outcome: str, request: KnowledgeRefreshRequest, source_revision: str,
                graph_version: str | None, *, error: dict[str, Any]) -> NodeResult:
        result = {"status": outcome, "effective_mode": request.policy.mode,
                  "commit_allowed": False, "source_revision": source_revision,
                  "graph_version": graph_version, "request": request.to_dict(), "error": error}
        return NodeResult("knowledge_refresh", outcome, data={"result": result}, error=error)


__all__ = ["KnowledgeRefreshPolicy", "KnowledgeRefreshRequest", "KnowledgeRefreshNode", "knowledge_refresh_graph"]
