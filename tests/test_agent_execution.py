from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from orchestrator import (AgentPreparation, AgentExecution, ExecutionPreflight, PreparationError,
                          ArtifactError, GraphStatus, KnowledgeRefreshResult, RuntimeError as ProcessError)
from orchestrator.knowledge_contracts import KnowledgeError
from orchestrator_task_manager import TaskManagerService
from tests.test_knowledge_refresh_node import FakeKnowledgeService


class AgentExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "orchestrator").mkdir()
        self.code = self.root / "orchestrator" / "entry.py"
        self.code.write_text("VALUE = 1\n", encoding="utf-8")
        self.flow = AgentExecution(self.root)
        self.service = self.flow.service
        self.task = self.prepare()

    def prepare(self, *, units=None, source=None):
        prep = AgentPreparation(self.root)
        task = prep.service.create_task(title="Change", task_type="implementation", objective="Change code",
            original_request="Change code", acceptance_criteria=["Pass checks"])
        run = prep.start(task["id"], expected_task_version=task["version"],
            prepared_source_revision=source or self.flow.source_revision())
        units = units or [self.unit("WU-1"), self.unit("WU-2", ["WU-1"])]
        payloads = {
            "context": {"summary": "Inspected", "evidence_refs": ["orchestrator/entry.py:1"]},
            "analysis": {"objective_interpretation": "Change", "constraints": [], "invariants": [], "unknowns": []},
            "planning": {"goal": "Change", "scope": {"in": ["Code"], "out": ["Other"]},
                "global_constraints": [], "global_validation": ["Checks"], "work_units": units},
        }
        for _ in range(6):
            state = prep.inspect(run.run_id)
            stage = state["run"]["current_node"]
            if stage == "plan_review":
                raw = {"outcome": "approved", "payload": {"findings": [], "criterion_ids": ["AC-01"],
                    "zero_context_executable": True, "approved_binding": {
                        "plan_sha256": state["artifacts"]["plan"]["sha256"], "definition_version": 1}}}
            elif stage in {"package", "ready"}:
                raw = {"outcome": "success"}
            else:
                raw = {"outcome": "success", "payload": payloads[stage]}
            prep.submit(run.run_id, raw, expected_revision=state["run"]["revision"],
                        expected_task_version=state["task"]["version"])
        return prep.service.get_task(task["id"])

    @staticmethod
    def unit(uid, deps=None, scope="orchestrator"):
        return {"id": uid, "goal": "Change", "files_objects": [scope], "expected_result": ["Done"],
                "validation": ["Checks"], "depends_on": deps or []}

    def start(self):
        run = self.flow.start(self.task["id"], expected_task_version=self.task["version"], worker_ref="worker")
        self.rid = run.run_id
        return self.snapshot()

    def snapshot(self):
        return self.flow.inspect(self.rid)

    def submit(self, envelope):
        state = self.snapshot()
        return self.flow.submit(self.rid, envelope, expected_revision=state["run"]["revision"],
                                expected_task_version=state["task"]["version"])

    def success(self, uid="WU-1", change=True):
        before = self.snapshot()["checkpoint_revision"]
        if change:
            self.code.write_text("VALUE = " + str(len(self.snapshot()["completed_units"]) + 2) + "\n", encoding="utf-8")
        return {"outcome": "success", "payload": {"unit_id": uid, "summary": "Done",
            "source_before": before, "source_after": self.flow.source_revision(),
            "changed_files": ["orchestrator/entry.py"] if change else [], "evidence_refs": ["check-output"],
            "validation": {"status": "passed", "checks_run": ["unit checks"], "failed": []}, "unresolved": []}}

    def resume(self, **kwargs):
        state = self.snapshot(); wait = state["run"]["wait"]
        return self.flow.resume_wait(self.rid, expected_revision=state["run"]["revision"],
            expected_task_version=state["task"]["version"], wait_id=wait["wait_id"], node_id=wait["node_id"], **kwargs)

    def test_readonly_preflight_and_explicit_work_units_handoff(self):
        before = self.service.get_task(self.task["id"])
        result = ExecutionPreflight(self.root).check(self.task["id"], expected_task_version=before["version"])
        self.assertEqual(result["status"], "fresh")
        self.assertEqual(before, self.service.get_task(self.task["id"]))
        state = self.start()
        self.assertFalse(hasattr(self.flow, "step"))
        self.assertEqual(state["task"]["active_run_ref"], self.rid)
        self.assertEqual([u["id"] for u in self.flow.request(self.rid)["available_units"]], ["WU-1"])
        self.submit(self.success())
        self.assertEqual([u["id"] for u in self.flow.request(self.rid)["available_units"]], ["WU-2"])
        self.submit(self.success("WU-2"))
        self.submit({"outcome": "handoff"})
        state = self.snapshot()
        self.assertEqual(state["run"]["state"], "succeeded")
        self.assertEqual(state["task"]["status"], "active")
        self.assertIsNone(state["task"]["active_run_ref"])
        self.assertIsNotNone(state["task"]["active_claim"])
        self.assertEqual(state["completed_units"], ["WU-1", "WU-2"])
        self.assertEqual(self.service.health_check(), [])
        record = state["artifacts"]["implementation"]
        self.flow.repository.verify(record["ref"], record["role"], record["version"])

    def test_precommit_gate_delegates_refresh_and_allows_fresh_candidate(self):
        class Knowledge:
            def precommit_refresh(self):
                return KnowledgeRefreshResult("indexed", {"digest": "a"}, {"version": "v1"},
                                              1, 0, mode="incremental", details={"changed": []})

            def status(self):
                return GraphStatus("fresh", {"digest": "a"}, {"digest": "a"},
                                   {"version": "v1"}, {"package": "graphifyy"})

        self.flow.knowledge_service = Knowledge()
        self.start()
        self.submit(self.success())
        self.submit(self.success("WU-2"))
        state = self.snapshot()
        result = self.flow.precommit_gate(self.rid, expected_revision=state["run"]["revision"],
                                          expected_task_version=state["task"]["version"])
        self.assertEqual(result["contract"], "knowledge-precommit-gate/v1")
        self.assertEqual(result["status"], "success")
        self.assertTrue(result["commit_allowed"])
        self.assertEqual(self.snapshot()["knowledge_gate"]["status"], "success")

    def test_precommit_gate_denies_stale_candidate(self):
        class Knowledge:
            def precommit_refresh(self):
                return KnowledgeRefreshResult("failed", None, None,
                                              error={"code": "provider_timeout"}, mode="incremental")

            def status(self):
                return GraphStatus("stale", {"digest": "b"}, {"digest": "a"},
                                   {"version": "v1"}, {"package": "graphifyy"})

        self.flow.knowledge_service = Knowledge()
        self.start()
        self.submit(self.success())
        self.submit(self.success("WU-2"))
        state = self.snapshot()
        result = self.flow.precommit_gate(self.rid, expected_revision=state["run"]["revision"],
                                          expected_task_version=state["task"]["version"])
        self.assertEqual(result["status"], "stale")
        self.assertFalse(result["commit_allowed"])

    def _gate_success_payloads(self, state, *, docs_adjacent=False):
        source = state["source_revision"]
        candidate = state["candidate_revision"]
        return {
            "code_review": {"outcome": "approved", "payload": {
                "summary": "Review completed", "implementation_revision": source,
                "findings": [], "evidence_refs": ["review-output"], "candidate_revision": candidate}},
            "testing": {"outcome": "passed", "payload": {
                "summary": "Tests passed", "implementation_revision": source,
                "totals": {"checks": 3, "passed": 3, "failed": 0, "skipped": 0},
                "evidence_refs": ["test-output"], "candidate_revision": candidate}},
            "documentation": {"outcome": "success", "payload": {
                "summary": "Documentation checked", "implementation_revision": source,
                "impacted": True, "source_adjacent_changed": docs_adjacent,
                "targets": ["docs/guides/agent-execution.md"], "evidence_refs": ["docs-output"],
                "candidate_revision": candidate}},
        }

    def _finish_work_units_for_gates(self):
        self.start()
        self.submit(self.success())
        self.submit(self.success("WU-2"))
        self.submit({"outcome": "handoff"})
        state = self.snapshot()
        return self.flow.start_gates(self.rid, expected_revision=state["run"]["revision"],
                                     expected_task_version=state["task"]["version"])

    def _submit_gate_payload(self, gate_id, payload):
        state = self.flow.gate_inspect(gate_id)
        return self.flow.submit_gate(gate_id, payload, expected_revision=state["run"]["revision"],
                                     expected_task_version=state["task"]["version"])

    def test_execution_gates_publish_evidence_and_enter_acceptance(self):
        class Knowledge:
            def precommit_refresh(self):
                return KnowledgeRefreshResult("indexed", {"digest": "a"}, {"version": "v1"},
                                              1, 0, mode="incremental", details={"changed": []})

            def status(self):
                return GraphStatus("fresh", {"digest": "a"}, {"digest": "a"},
                                   {"version": "v1"}, {"package": "graphifyy"})

        self.flow.knowledge_service = Knowledge()
        gate = self._finish_work_units_for_gates()
        gid = gate["run"]["run_id"]
        payloads = self._gate_success_payloads(gate)
        for node in ("code_review", "testing", "documentation"):
            self._submit_gate_payload(gid, payloads[node])
        state = self.flow.gate_inspect(gid)
        self.flow.refresh_knowledge(gid, expected_revision=state["run"]["revision"],
                                    expected_task_version=state["task"]["version"])
        state = self.flow.gate_inspect(gid)
        candidate = state["candidate_revision"]
        source = state["source_revision"]
        final = {"outcome": "ready", "payload": {
            "summary": "All gates passed", "candidate_revision": candidate,
            "implementation_revision": source, "reviewed_revision": source,
            "tested_revision": source, "documented_revision": source,
            "knowledge_required": False, "knowledge_status": "success",
            "criteria": [{"id": "AC-01", "status": "satisfied", "evidence_refs": ["test-output"]}],
            "blocking_findings": [], "evidence_refs": ["review-output", "test-output"],
            "acceptance_package": {"summary": "Проверить gates", "scenarios": [{
                "id": "UAT-01", "title": "Пройти gates", "action": "Запустить сценарий",
                "expected": "Все gates проходят"}], "automated_evidence": ["test-output"],
                "known_warnings": [], "known_limitations": []}}}
        self._submit_gate_payload(gid, final)
        task = self.flow.service.get_task(self.task["id"])
        self.assertEqual(task["status"], "awaiting_acceptance")
        self.assertIsNone(task["active_claim"])
        self.assertIsNone(task["active_run_ref"])
        self.assertEqual(task["artifacts"]["readiness"]["metadata"]["status"], "ready")
        self.assertIn("acceptance_package", task["artifacts"])
        finished = self.flow.gate_inspect(gid)
        self.assertIsNotNone(self.flow.repository.verify(finished["artifacts"]["code_review"]["ref"], "code_review", "v1"))
        accepted = self.flow.service.accept_task(self.task["id"], task["version"],
            candidate_revision=candidate, completion_decision_ref="completion:TASK-0017",
            artifact_ref=task["artifacts"]["acceptance_package"]["ref"])
        self.assertEqual(accepted["status"], "completed")

    def _full_knowledge_gate(self):
        self.flow.knowledge_service = FakeKnowledgeService(KnowledgeRefreshResult(
            "indexed", {"digest": "a" * 64}, {"version": "v2"}, 1, 0, mode="full-rebuild"))
        gate = self._finish_work_units_for_gates()
        gid = gate["run"]["run_id"]
        for payload in self._gate_success_payloads(gate).values():
            self._submit_gate_payload(gid, payload)
        return gid

    def _refresh_gate(self, gid, **kwargs):
        state = self.flow.gate_inspect(gid)
        return self.flow.refresh_knowledge(gid, expected_revision=state["run"]["revision"],
                                           expected_task_version=state["task"]["version"], **kwargs)

    def test_knowledge_gate_confirmation_preserves_policy_and_versions(self):
        gid = self._full_knowledge_gate()
        request = {"policy": {"mode": "full", "authorization": "required"}}
        run = self._refresh_gate(gid, request=request)
        self.assertEqual(run.state, "waiting_input")
        first = self.flow.gate_inspect(gid)["artifacts"]["knowledge_refresh"]
        before = self.flow.gate_inspect(gid)
        with self.assertRaises(PreparationError) as caught:
            self._refresh_gate(gid, request={"policy": {"mode": "auto"}}, decision={"approved": True, "ref": "user:1"})
        self.assertEqual(caught.exception.code, "stale_request")
        self.assertEqual(self.flow.gate_inspect(gid), before)
        for kwargs, error in (({"request": {"policy": {"mode": "invalid"}}}, KnowledgeError),
                              ({"decision": {"approved": True, "ref": ("bad",)}}, ProcessError),
                              ({}, PreparationError)):
            with self.subTest(kwargs=kwargs), self.assertRaises(error):
                self._refresh_gate(gid, **kwargs)
            self.assertEqual(self.flow.gate_inspect(gid), before)
            self.assertEqual(self.flow.knowledge_service.full_calls, 0)
        records = [first]
        for decision in ({"approved": False, "ref": "user:denial"}, {"approved": True}):
            run = self._refresh_gate(gid, decision=decision)
            self.assertEqual(run.state, "waiting_input")
            self.assertEqual(self.flow.knowledge_service.full_calls, 0)
            records.append(self.flow.gate_inspect(gid)["artifacts"]["knowledge_refresh"])
        run = self._refresh_gate(gid, decision={"approved": True, "ref": "user:approval"})
        self.assertEqual(run.state, "running")
        self.assertEqual(run.current_node, "final_validation")
        self.assertEqual(self.flow.knowledge_service.full_calls, 1)
        state = self.flow.gate_inspect(gid)
        self.assertEqual(state["knowledge"]["request"]["policy"]["mode"], "full")
        self.assertEqual(state["knowledge"]["status"], "success")
        records.append(state["artifacts"]["knowledge_refresh"])
        self.assertEqual(len({r["version"] for r in records}), 4)
        for record in records:
            self.flow.repository.verify(record["ref"], record["role"], record["version"])
        candidate, source = state["candidate_revision"], state["source_revision"]
        self._submit_gate_payload(gid, {"outcome": "ready", "payload": {
            "summary": "Full refresh подтверждён, gates проверены", "candidate_revision": candidate,
            "implementation_revision": source, "reviewed_revision": source,
            "tested_revision": source, "documented_revision": source,
            "knowledge_required": False, "knowledge_status": "success",
            "criteria": [{"id": "AC-01", "status": "satisfied", "evidence_refs": ["test:confirmation"]}],
            "blocking_findings": [], "evidence_refs": ["test:confirmation"],
            "acceptance_package": {"summary": "Проверить confirmation", "scenarios": [{
                "id": "UAT-01", "title": "Подтверждение", "action": "Одобрить full refresh",
                "expected": "Readiness после refresh"}], "automated_evidence": ["test:confirmation"],
                "known_warnings": [], "known_limitations": []}}})
        task = self.service.get_task(self.task["id"])
        self.assertEqual(task["status"], "awaiting_acceptance")
        self.assertIsNone(task["active_claim"])

    def test_knowledge_gate_exhausted_wait_does_not_resume_or_refresh(self):
        gid = self._full_knowledge_gate()
        self._refresh_gate(gid, request={"policy": {"mode": "full", "authorization": "required"}})
        for _ in range(6):
            self._refresh_gate(gid, decision={"approved": False, "ref": "user:denial"})
        before = self.flow.gate_inspect(gid)
        self.assertEqual(self.flow.runtime.available_actions(gid)["remaining_results"], 0)
        with self.assertRaises(PreparationError) as caught:
            self._refresh_gate(gid, decision={"approved": True, "ref": "user:approval"})
        self.assertEqual(caught.exception.code, "result_limit_exceeded")
        self.assertEqual(self.flow.gate_inspect(gid), before)
        self.assertEqual(self.flow.knowledge_service.full_calls, 0)

    def test_execution_gates_changes_required_never_becomes_ready(self):
        gate = self._finish_work_units_for_gates()
        gid = gate["run"]["run_id"]
        state = self.flow.gate_inspect(gid)
        raw = {"outcome": "changes_required", "payload": {
            "summary": "Fix required", "implementation_revision": state["source_revision"],
            "findings": [{"id": "CR-01", "summary": "Defect", "severity": "major",
                          "status": "open", "evidence_refs": ["review-output"]}],
            "evidence_refs": ["review-output"], "candidate_revision": state["candidate_revision"]}}
        self._submit_gate_payload(gid, raw)
        self.assertEqual(self.flow.gate_inspect(gid)["run"]["state"], "failed")
        task = self.flow.gate_inspect(gid)["task"]
        self.assertEqual(task["status"], "active")
        with self.assertRaises(PreparationError):
            self.flow.submit_gate(gid, raw, expected_revision=self.flow.gate_inspect(gid)["run"]["revision"],
                                  expected_task_version=task["version"])
        released = self.flow.release_gates(gid, expected_task_version=task["version"],
                                           reason="Review changes required")
        self.assertEqual(released["status"], "preparing")

    def test_execution_gates_required_knowledge_rejects_degraded(self):
        class Knowledge:
            def precommit_refresh(self):
                return KnowledgeRefreshResult("indexed", {"digest": "a"}, {"version": "v1"},
                                              1, 0, mode="full-rebuild-fallback", details={"fallback": True})

            def status(self):
                return GraphStatus("fresh", {"digest": "a"}, {"digest": "a"},
                                   {"version": "v1"}, {"package": "graphifyy"})

        self.flow.knowledge_service = Knowledge()
        self.start(); self.submit(self.success()); self.submit(self.success("WU-2")); self.submit({"outcome": "handoff"})
        state = self.snapshot()
        gate = self.flow.start_gates(self.rid, expected_revision=state["run"]["revision"],
                                     expected_task_version=state["task"]["version"], knowledge_required=True)
        gid = gate["run"]["run_id"]
        for node, payload in self._gate_success_payloads(gate).items():
            self._submit_gate_payload(gid, payload)
        state = self.flow.gate_inspect(gid)
        self.flow.refresh_knowledge(gid, expected_revision=state["run"]["revision"],
                                    expected_task_version=state["task"]["version"])
        state = self.flow.gate_inspect(gid)
        source, candidate = state["source_revision"], state["candidate_revision"]
        final = {"outcome": "ready", "payload": {
            "summary": "Should be rejected", "candidate_revision": candidate,
            "implementation_revision": source, "reviewed_revision": source,
            "tested_revision": source, "documented_revision": source,
            "knowledge_required": True, "knowledge_status": "degraded",
            "criteria": [{"id": "AC-01", "status": "satisfied", "evidence_refs": ["test-output"]}],
            "blocking_findings": [], "evidence_refs": ["test-output"],
            "acceptance_package": {"summary": "Package", "scenarios": [{"id": "UAT-01", "title": "Check",
                "action": "Run", "expected": "Pass"}], "automated_evidence": ["test-output"]}}}
        with self.assertRaises(PreparationError) as error:
            self._submit_gate_payload(gid, final)
        self.assertEqual(error.exception.code, "not_ready")
        self.assertNotEqual(self.flow.gate_inspect(gid)["task"]["status"], "awaiting_acceptance")

    def test_stale_code_before_claim(self):
        self.code.write_text("VALUE = 8\n", encoding="utf-8")
        with self.assertRaises(PreparationError):
            self.start()
        self.assertEqual(self.task, self.service.get_task(self.task["id"]))

    def test_opaque_revision_requires_reprepare(self):
        self.task = self.prepare(source="old-source-v1")
        with self.assertRaises(PreparationError) as error:
            self.start()
        self.assertEqual(error.exception.code, "unsupported_source_revision")

    def test_projection_tampering_before_claim(self):
        path = self.root / self.task["artifacts"]["plan"]["path"]
        path.write_text("tampered", encoding="utf-8")
        with self.assertRaises(PreparationError):
            self.start()
        self.assertIsNone(self.service.get_task(self.task["id"])["active_claim"])

    def test_immutable_tampering_before_claim(self):
        record = self.task["artifacts"]["plan_review"]["metadata"]["repository"]
        stored = self.flow.repository.get(record["ref"], record["role"], record["version"])
        (self.root / stored.record.path).write_bytes(b"tampered")
        with self.assertRaises(ArtifactError):
            self.start()

    def test_forbidden_scope_before_claim(self):
        for scope in ("obsolete", ".", "../escape", ".orchestrator"):
            with self.subTest(scope=scope):
                self.task = self.prepare(units=[self.unit("WU-1", scope=scope)])
                with self.assertRaises(Exception):
                    self.start()
                self.assertIsNone(self.service.get_task(self.task["id"])["active_claim"])

    def test_invalid_envelopes_and_cas_do_not_advance(self):
        before = self.start()
        cases = [{"outcome": "handoff"}, {"outcome": "other"}, {"outcome": "success", "payload": {}},
                 {"outcome": "needs_input", "question": ""}, {"outcome": "blocked", "reason": "x", "route": "done"}]
        for raw in cases:
            with self.assertRaises(PreparationError):
                self.submit(raw)
            self.assertEqual(before, self.snapshot())
        for rv, tv in ((0, before["task"]["version"]), (True, before["task"]["version"]), (1, 0)):
            with self.assertRaises(PreparationError):
                self.flow.submit(self.rid, self.success(change=False), expected_revision=rv, expected_task_version=tv)
            self.assertEqual(before, self.snapshot())

    def test_dependency_and_duplicate_units_rejected(self):
        self.start()
        with self.assertRaises(PreparationError):
            self.submit(self.success("WU-2", change=False))
        self.submit(self.success(change=False))
        with self.assertRaises(PreparationError):
            self.submit(self.success(change=False))

    def test_observed_delta_and_scope_are_required(self):
        before = self.start()
        raw = self.success()
        raw["payload"]["changed_files"] = []
        with self.assertRaises(PreparationError):
            self.submit(raw)
        self.assertEqual(before, self.snapshot())
        raw["payload"]["changed_files"] = ["orchestrator/entry.py"]
        raw["payload"]["source_before"] = "wrong"
        with self.assertRaises(PreparationError):
            self.submit(raw)
        raw["payload"]["source_before"] = before["checkpoint_revision"]
        raw["payload"]["changed_files"] = ["tests/escape.py"]
        with self.assertRaises(PreparationError):
            self.submit(raw)

    def test_failed_validation_and_unresolved_are_not_success(self):
        self.start()
        for key, value in (("unresolved", ["todo"]), ("validation", {"status": "failed", "checks_run": ["checks"], "failed": ["test"]})):
            raw = self.success(change=False); raw["payload"][key] = value
            with self.assertRaises(PreparationError):
                self.submit(raw)

    def test_unreported_external_change_blocks_request_and_wait(self):
        self.start(); self.code.write_text("VALUE = 6\n", encoding="utf-8")
        with self.assertRaises(PreparationError):
            self.flow.request(self.rid)
        with self.assertRaises(PreparationError):
            self.submit({"outcome": "needs_input", "question": "Continue?"})

    def test_docs_and_obsolete_are_not_code_fingerprint(self):
        before = self.flow.source_revision()
        (self.root / "docs").mkdir(); (self.root / "docs" / "guide.md").write_text("new", encoding="utf-8")
        (self.root / "obsolete").mkdir(); (self.root / "obsolete" / "old.py").write_text("old", encoding="utf-8")
        self.assertEqual(before, self.flow.source_revision())
        self.start()

    def test_input_pause_releases_and_resume_reclaims(self):
        state = self.start(); old = state["claim_ref"]
        self.submit({"outcome": "needs_input", "question": "Continue?"})
        state = self.snapshot()
        self.assertEqual(state["task"]["status"], "awaiting_input")
        self.assertIsNone(state["task"]["active_claim"])
        self.assertIsNone(state["task"]["active_run_ref"])
        self.assertEqual(self.service.health_check(), [])
        self.resume(answer=None)
        state = self.snapshot()
        self.assertNotEqual(old, state["claim_ref"])
        self.assertEqual(state["task"]["status"], "active")
        self.assertIsNone(state["run"]["resumed_wait"]["answer"])
        self.submit(self.success(change=False))

    def test_blocked_pause_resolves_owned_blocker(self):
        self.start(); self.submit({"outcome": "blocked", "reason": "Access"})
        self.resume(resolution="Granted")
        self.assertEqual(self.snapshot()["task"]["blockers"][0]["status"], "resolved")
        self.assertEqual(self.service.health_check(), [])

    def test_wait_identity_is_cas_and_invalid_resume_atomic(self):
        self.start(); self.submit({"outcome": "needs_input", "question": "Continue?"})
        before = self.snapshot()
        with self.assertRaises(Exception):
            self.flow.resume_wait(self.rid, expected_revision=before["run"]["revision"],
                expected_task_version=before["task"]["version"], wait_id="wrong", node_id="work_unit", answer="yes")
        self.assertEqual(before, self.snapshot())

    def test_failure_is_terminal_and_releases_claim(self):
        self.start(); self.submit({"outcome": "failure", "reason": "Cannot implement"})
        state = self.snapshot()
        self.assertEqual(state["run"]["state"], "failed")
        self.assertEqual(state["task"]["status"], "blocked")
        self.assertIsNone(state["task"]["active_claim"])
        self.assertEqual(self.service.health_check(), [])

    def test_lease_expiry_blocks_work_but_owned_cleanup_allowed(self):
        self.start()
        with patch.object(self.service, "clock", return_value=datetime.now(timezone.utc)+timedelta(days=2)):
            with self.assertRaises(PreparationError) as error:
                self.submit(self.success(change=False))
            self.assertEqual(error.exception.code, "claim_expired")
            state = self.snapshot()
            self.flow.cancel(self.rid, expected_revision=state["run"]["revision"],
                expected_task_version=state["task"]["version"], reason="Reprepare")
        self.assertEqual(self.snapshot()["task"]["status"], "preparing")
        self.assertEqual(self.service.health_check(), [])

    def test_renew_does_not_advance_process(self):
        before = self.start()
        self.flow.renew_claim(self.rid, expected_revision=before["run"]["revision"],
                             expected_task_version=before["task"]["version"], lease_seconds=1800)
        after = self.snapshot()
        self.assertEqual(before["run"], after["run"])
        self.assertEqual(before["task"]["version"]+1, after["task"]["version"])

    def test_artifact_failure_is_pending_not_second_work_unit(self):
        self.start(); raw = self.success()
        with patch.object(self.flow.repository, "put", side_effect=ArtifactError("repository_failure", "disk")):
            with self.assertRaises(PreparationError):
                self.submit(raw)
        state = self.snapshot()
        self.assertTrue(state["sync_pending"])
        self.assertEqual(state["completed_units"], ["WU-1"])
        with self.assertRaises(PreparationError):
            self.submit(raw)
        self.flow.synchronize(self.rid)
        self.assertFalse(self.snapshot()["sync_pending"])

    def test_unknown_committed_attach_requires_exact_reconciliation(self):
        self.start(); original = self.service.attach_artifact
        def lost(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("lost response")
        with patch.object(self.service, "attach_artifact", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit(self.success(change=False))
        state = self.snapshot()
        self.assertIsNotNone(state["unknown_effect"])
        with self.assertRaises(PreparationError):
            self.flow.synchronize(self.rid)
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.assertFalse(self.snapshot()["sync_pending"])
        self.assertEqual(self.snapshot()["completed_units"], ["WU-1"])

    def test_unknown_uncommitted_attach_can_retry_after_no_change_proof(self):
        self.start()
        with patch.object(self.service, "attach_artifact", side_effect=OSError("before commit")):
            with self.assertRaises(PreparationError):
                self.submit(self.success(change=False))
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=False, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.assertFalse(self.snapshot()["sync_pending"])

    def test_unknown_claim_adopts_without_second_claim(self):
        original = self.service.claim_task
        def lost(*args, **kwargs):
            original(*args, **kwargs); raise OSError("lost")
        with patch.object(self.service, "claim_task", side_effect=lost):
            with self.assertRaises(PreparationError) as error:
                self.start()
        self.rid = error.exception.details["run_id"]
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.assertEqual(self.snapshot()["task"]["active_run_ref"], self.rid)
        self.assertEqual(self.service.health_check(), [])

    def test_unknown_release_adopts_paused_successor(self):
        self.start(); original = self.service.release_claim
        def lost(*args, **kwargs):
            original(*args, **kwargs); raise OSError("lost")
        with patch.object(self.service, "release_claim", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit({"outcome": "blocked", "reason": "Access"})
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.resume(resolution="Granted")
        self.assertEqual(self.service.health_check(), [])

    def test_external_task_version_requires_explicit_reconcile(self):
        state = self.start()
        task = self.service.record_user_decision(self.task["id"], state["task"]["version"], decision_type="clarification", value="note")
        with self.assertRaises(PreparationError):
            self.flow.request(self.rid)
        self.flow.reconcile(self.rid, expected_version=task["version"])
        self.assertIn("submit", self.flow.available_actions(self.rid)["actions"])

    def test_unknown_extra_successor_is_not_reconciled(self):
        self.start(); original = self.service.attach_artifact
        def lost(*args, **kwargs):
            task = original(*args, **kwargs)
            self.service.record_user_decision(task["id"], task["version"], decision_type="clarification", value="external")
            raise OSError("lost")
        with patch.object(self.service, "attach_artifact", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit(self.success(change=False))
        state = self.snapshot()
        with self.assertRaises(PreparationError):
            self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])

    def test_source_add_delete_and_rename_observed(self):
        self.start()
        before = self.snapshot()["checkpoint_revision"]
        new = self.code.with_name("renamed.py")
        self.code.rename(new)
        raw = self.success(change=False)
        raw["payload"].update(source_before=before, changed_files=["orchestrator/entry.py", "orchestrator/renamed.py"])
        self.submit(raw)
        self.assertEqual(self.snapshot()["completed_units"], ["WU-1"])

    def test_cancel_after_partial_edits_invalidates_package_not_files(self):
        state = self.start()
        self.code.write_text("VALUE = 77\n", encoding="utf-8")
        self.flow.cancel(self.rid, expected_revision=state["run"]["revision"],
            expected_task_version=state["task"]["version"], reason="Reprepare partial edits")
        state = self.snapshot()
        self.assertEqual(state["task"]["status"], "preparing")
        self.assertNotIn("execution_package", state["task"]["artifacts"])
        self.assertEqual(self.code.read_text(encoding="utf-8"), "VALUE = 77\n")

    def test_foreign_claim_cannot_be_adopted_or_cleaned(self):
        state = self.start()
        task = self.service.link_workflow_run(self.task["id"], state["task"]["version"], run_ref=self.rid, relation="finished")
        task = self.service.release_claim(task["id"], task["version"], claim_ref=state["claim_ref"], target_status="ready", reason="handoff")
        task = self.service.claim_task(task["id"], task["version"], worker_ref="foreign", lease_seconds=900)
        with self.assertRaises(PreparationError):
            self.flow.reconcile(self.rid, expected_version=task["version"])
        with self.assertRaises(PreparationError):
            self.flow.cancel(self.rid, expected_revision=state["run"]["revision"], expected_task_version=task["version"], reason="stop")

    def test_unknown_renew_adopts_once(self):
        state = self.start(); original = self.service.renew_claim
        def lost(*args, **kwargs):
            original(*args, **kwargs); raise OSError("lost")
        with patch.object(self.service, "renew_claim", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.flow.renew_claim(self.rid, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.assertFalse(self.snapshot()["sync_pending"])

    def test_unknown_resume_claim_preserves_answer(self):
        self.start(); self.submit({"outcome": "needs_input", "question": "Continue?"})
        original = self.service.claim_task
        def lost(*args, **kwargs):
            original(*args, **kwargs); raise OSError("lost")
        with patch.object(self.service, "claim_task", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.resume(answer="yes")
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        self.flow.synchronize(self.rid)
        self.assertEqual(self.snapshot()["run"]["resumed_wait"]["answer"], "yes")
        self.assertEqual(self.service.health_check(), [])

    def test_unknown_link_handoff_does_not_repeat(self):
        self.start(); self.submit(self.success(change=False)); self.submit(self.success("WU-2", change=False))
        original = self.service.link_workflow_run
        def lost(*args, **kwargs):
            original(*args, **kwargs); raise OSError("lost")
        with patch.object(self.service, "link_workflow_run", side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit({"outcome": "handoff"})
        state = self.snapshot()
        self.flow.reconcile_effect(self.rid, applied=True, expected_task_version=state["task"]["version"])
        # Handoff has already removed active_run_ref; recovery is a no-write adoption.
        self.flow.synchronize(self.rid)
        self.assertFalse(self.snapshot()["sync_pending"])

    def test_result_budget_requires_owned_cleanup(self):
        self.flow.max_results = 1
        self.start(); self.submit(self.success(change=False))
        self.assertNotIn("submit", self.flow.available_actions(self.rid)["actions"])
        state = self.snapshot()
        self.flow.cancel(self.rid, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"], reason="budget")
        self.assertEqual(self.service.health_check(), [])

    def test_known_pending_can_be_explicitly_abandoned_not_unknown(self):
        self.start()
        with patch.object(self.flow.repository, "put", side_effect=ArtifactError("repository_failure", "disk")):
            with self.assertRaises(PreparationError):
                self.submit(self.success())
        state = self.snapshot()
        self.flow.cancel(self.rid, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"], reason="Abandon known pending")
        self.assertFalse(self.snapshot()["sync_pending"])
        self.assertEqual(self.snapshot()["task"]["status"], "preparing")


if __name__ == "__main__":
    unittest.main()
