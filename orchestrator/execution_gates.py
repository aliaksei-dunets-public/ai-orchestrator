"""Структурированный post-work-unit pipeline execution gates.

Модуль содержит только контракт графа и детерминированную валидацию envelopes.
Semantic review, запуск тестов и написание документации выполняет вызывающий агент.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from .preparation_primitives import PreparationError, _json_bytes, _strings, _text
from .runtime_contracts import Graph, Node


GATE_NODES = ("code_review", "testing", "documentation", "knowledge_refresh", "final_validation")


def execution_gates_graph() -> Graph:
    """Возвращает immutable graph definition для post-implementation gates."""
    review = ("approved", "changes_required", "replanning_required", "reanalysis_required",
              "more_context_required", "user_input_required", "blocked", "failure")
    testing = ("passed", "passed_with_warnings", "failed", "blocked", "inconclusive")
    documentation = ("success", "no_change", "needs_context", "implementation_change_required",
                     "needs_input", "blocked", "failure")
    knowledge = ("not_required", "success", "degraded", "stale", "failed", "fallback_required",
                 "needs_input")
    final = ("ready", "not_ready", "blocked")
    nodes = {
        "code_review": Node("code_review", "code-review-request/v1", "code-review-result/v1",
                             review, {outcome: "testing" if outcome == "approved" else "failed" for outcome in review}),
        "testing": Node("testing", "testing-request/v1", "testing-result/v1", testing,
                         {outcome: "documentation" if outcome in {"passed", "passed_with_warnings"} else "failed"
                          for outcome in testing}),
        "documentation": Node("documentation", "documentation-request/v1", "documentation-result/v1",
                               documentation, {outcome: "knowledge_refresh" if outcome in {"success", "no_change"}
                                               else "failed" for outcome in documentation}),
        "knowledge_refresh": Node("knowledge_refresh", "knowledge-refresh-request/v1",
                                   "knowledge-refresh-node/v1", knowledge,
                                   {outcome: "knowledge_refresh" if outcome == "needs_input" else
                                    "final_validation" if outcome in {"not_required", "success", "degraded"}
                                    else "failed" for outcome in knowledge}),
        "final_validation": Node("final_validation", "final-validation-request/v1",
                                  "readiness-result/v1", final,
                                  {"ready": "succeeded", "not_ready": "failed", "blocked": "failed"}),
    }
    return Graph("execution-gates-v1", 1, "code_review", nodes)


def candidate_revision() -> str:
    """Создаёт непрозрачный, но безопасный ID acceptance candidate."""
    # UUID не является evidence; он только отделяет acceptance attempt от предыдущих.
    import uuid
    return "CANDIDATE-" + uuid.uuid4().hex


def candidate_fingerprint(*, task_id: str, definition_version: int, package_ref: str,
                          source_revision: str) -> str:
    """Детерминированный fingerprint исходной стороны candidate."""
    value = {"task_ref": task_id, "definition_version": definition_version,
             "package_ref": package_ref, "source_revision": source_revision}
    return "CANDIDATE-" + hashlib.sha256(_json_bytes(value)).hexdigest()


def _payload(envelope: Mapping[str, Any], *, outcome: str) -> dict[str, Any]:
    if set(envelope) != {"outcome", "payload"} or envelope.get("outcome") != outcome:
        raise PreparationError("contract_violation", "Gate envelope должен содержать outcome и payload")
    value = envelope.get("payload")
    if not isinstance(value, Mapping):
        raise PreparationError("contract_violation", "payload gate должен быть объектом")
    return dict(value)


def _revision_fields(payload: Mapping[str, Any], *, candidate: str, source: str,
                     names: tuple[str, ...] = ("implementation_revision",)) -> None:
    for name in names:
        if payload.get(name) != source:
            raise PreparationError("stale_evidence", f"{name} не совпадает с текущей source revision",
                                   expected=source, actual=payload.get(name))
    if "candidate_revision" in payload and payload["candidate_revision"] != candidate:
        raise PreparationError("stale_evidence", "Evidence относится к другой candidate revision",
                               expected=candidate, actual=payload.get("candidate_revision"))


def validate_gate_envelope(node_id: str, envelope: Mapping[str, Any], *, candidate: str,
                           source: str, acceptance_criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """Проверяет agent-provided gate result без semantic interpretation."""
    if not isinstance(envelope, Mapping):
        raise PreparationError("contract_violation", "Gate envelope должен быть объектом")
    raw = dict(envelope)
    if set(raw) - {"outcome", "payload"}:
        raise PreparationError("contract_violation", "Неизвестные поля gate envelope")
    outcome = raw.get("outcome")
    payload = raw.get("payload")
    if not isinstance(outcome, str) or not isinstance(payload, Mapping):
        raise PreparationError("contract_violation", "Gate envelope имеет неверную форму")
    payload = dict(payload)
    _text(payload.get("summary"), "summary")
    if node_id == "code_review":
        if outcome not in execution_gates_graph().nodes[node_id].outcomes:
            raise PreparationError("unknown_outcome", "Неизвестный outcome code review")
        _revision_fields(payload, candidate=candidate, source=source)
        findings = payload.get("findings")
        if not isinstance(findings, list) or any(not isinstance(item, Mapping) for item in findings):
            raise PreparationError("contract_violation", "findings review должны быть списком объектов")
        for finding in findings:
            _text(finding.get("id"), "finding.id")
            _text(finding.get("summary"), "finding.summary")
            if finding.get("severity") not in {"info", "minor", "major", "critical"}:
                raise PreparationError("contract_violation", "Неизвестная severity finding")
            if finding.get("status", "open") not in {"open", "resolved", "accepted_risk", "obsolete"}:
                raise PreparationError("contract_violation", "Неизвестный status finding")
            if finding.get("severity") in {"major", "critical"}:
                _strings(finding.get("evidence_refs"), "finding.evidence_refs", nonempty=True)
        _strings(payload.get("evidence_refs"), "evidence_refs", nonempty=True)
        if outcome == "approved" and any(item.get("severity") in {"major", "critical"}
                                         and item.get("status", "open") == "open" for item in findings):
            raise PreparationError("blocking_finding", "Одобренный review содержит открытый major/critical finding")
    elif node_id == "testing":
        if outcome not in execution_gates_graph().nodes[node_id].outcomes:
            raise PreparationError("unknown_outcome", "Неизвестный outcome testing")
        _revision_fields(payload, candidate=candidate, source=source)
        totals = payload.get("totals")
        if not isinstance(totals, Mapping):
            raise PreparationError("contract_violation", "testing.totals должен быть объектом")
        for name in ("checks", "passed", "failed", "skipped"):
            if type(totals.get(name)) is not int or totals[name] < 0:
                raise PreparationError("contract_violation", f"testing.totals.{name} должен быть числом")
        _strings(payload.get("evidence_refs"), "evidence_refs", nonempty=True)
        if outcome in {"passed", "passed_with_warnings"} and totals["failed"] != 0:
            raise PreparationError("contract_violation", "passed testing не может иметь failed checks")
    elif node_id == "documentation":
        if outcome not in execution_gates_graph().nodes[node_id].outcomes:
            raise PreparationError("unknown_outcome", "Неизвестный outcome documentation")
        _revision_fields(payload, candidate=candidate, source=source)
        if type(payload.get("impacted")) is not bool or type(payload.get("source_adjacent_changed")) is not bool:
            raise PreparationError("contract_violation", "documentation flags должны быть bool")
        _strings(payload.get("evidence_refs"), "evidence_refs", nonempty=True)
        if outcome == "no_change" and payload["impacted"]:
            raise PreparationError("contract_violation", "no_change не может иметь impacted=true")
    elif node_id == "final_validation":
        if outcome not in execution_gates_graph().nodes[node_id].outcomes:
            raise PreparationError("unknown_outcome", "Неизвестный outcome final validation")
        _revision_fields(payload, candidate=candidate, source=source,
                         names=("implementation_revision", "reviewed_revision", "tested_revision",
                                "documented_revision"))
        if payload.get("candidate_revision") != candidate:
            raise PreparationError("stale_evidence", "Final validation относится к другой candidate")
        criteria = payload.get("criteria")
        expected = {item["id"] for item in acceptance_criteria}
        if not isinstance(criteria, list) or {item.get("id") for item in criteria if isinstance(item, Mapping)} != expected:
            raise PreparationError("contract_violation", "Final validation не покрывает все acceptance criteria")
        for item in criteria:
            if not isinstance(item, Mapping) or item.get("status") != "satisfied":
                raise PreparationError("not_ready", "Acceptance criterion не подтверждён")
            _strings(item.get("evidence_refs"), "criterion.evidence_refs", nonempty=True)
        _strings(payload.get("evidence_refs"), "evidence_refs", nonempty=True)
        if payload.get("blocking_findings") != []:
            raise PreparationError("not_ready", "Открытые blocking findings запрещают readiness")
        if type(payload.get("knowledge_required")) is not bool:
            raise PreparationError("contract_violation", "knowledge_required должен быть bool")
        if payload.get("knowledge_status") not in {"not_required", "success", "degraded", "stale", "failed",
                                                    "fallback_required", "awaiting_confirmation"}:
            raise PreparationError("contract_violation", "Неизвестный knowledge_status")
        if payload["knowledge_required"] and payload["knowledge_status"] not in {"not_required", "success"}:
            raise PreparationError("not_ready", "Required knowledge policy не подтверждена")
        package = payload.get("acceptance_package")
        if not isinstance(package, Mapping):
            raise PreparationError("contract_violation", "Нужен acceptance_package")
        _text(package.get("summary"), "acceptance_package.summary")
        scenarios = package.get("scenarios")
        if not isinstance(scenarios, list) or not scenarios:
            raise PreparationError("contract_violation", "Acceptance package требует scenarios")
        for scenario in scenarios:
            if not isinstance(scenario, Mapping):
                raise PreparationError("contract_violation", "Scenario должен быть объектом")
            for name in ("id", "title", "action", "expected"):
                _text(scenario.get(name), f"scenario.{name}")
        _strings(package.get("automated_evidence"), "automated_evidence", nonempty=True)
        if outcome == "ready" and payload.get("knowledge_status") in {"stale", "failed", "fallback_required",
                                                                        "awaiting_confirmation"}:
            raise PreparationError("not_ready", "Knowledge evidence запрещает readiness")
    else:
        raise PreparationError("invalid_state", "Этот узел не принимает agent envelope")
    return {"outcome": outcome, "payload": payload}


def validate_knowledge_policy(status: str, *, required: bool) -> None:
    if status not in {"not_required", "success", "degraded", "stale", "failed", "fallback_required",
                      "awaiting_confirmation"}:
        raise PreparationError("contract_violation", "Неизвестный knowledge status")
    if status in {"stale", "failed", "fallback_required", "awaiting_confirmation"}:
        raise PreparationError("knowledge_not_ready", "Knowledge gate не подтвердил свежий graph", status=status)
    if required and status not in {"not_required", "success"}:
        raise PreparationError("knowledge_required", "Required knowledge policy не допускает degraded", status=status)


__all__ = ["GATE_NODES", "candidate_fingerprint", "candidate_revision", "execution_gates_graph",
           "validate_gate_envelope", "validate_knowledge_policy"]
