from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from orchestrator import AgentPreparation, AgentExecution, ExecutionPreflight, PreparationError, ArtifactError
from orchestrator_task_manager import TaskManagerService


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
