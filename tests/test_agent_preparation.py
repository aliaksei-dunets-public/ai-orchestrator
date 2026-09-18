from __future__ import annotations

import copy
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from orchestrator import AgentPreparation, ArtifactError, PreparationError, RuntimeError
from orchestrator_task_manager import TaskError, TaskManagerService


class AgentPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.flow = AgentPreparation(self.root)
        self.service = self.flow.service
        self.task = self.service.create_task(title="Fix", task_type="implementation", objective="Fix API",
            original_request="Fix API", acceptance_criteria=["Pass tests"], constraints=["Keep API"])
        self.run = self.flow.start(self.task["id"], expected_task_version=self.task["version"], prepared_source_revision="source-v1")
        self.rid = self.run.run_id

    def snapshot(self):
        return self.flow.inspect(self.rid)

    def submit(self, raw):
        s = self.snapshot()
        return self.flow.submit(self.rid, raw, expected_revision=s["run"]["revision"], expected_task_version=s["task"]["version"])

    def raw(self, stage):
        payloads = {
            "context": {"summary": "Project inspected", "evidence_refs": ["src/api.py:1"]},
            "analysis": {"objective_interpretation": "Fix", "constraints": [], "invariants": [], "unknowns": []},
            "planning": {"goal": "Fix", "scope": {"in": ["API"], "out": ["Other changes"]},
                "global_constraints": ["Keep API"], "global_validation": ["Run tests"],
                "work_units": [{"id": "WU-1", "goal": "Fix", "files_objects": ["src/api.py"],
                                "expected_result": ["API works"], "validation": ["Run tests"], "depends_on": []}]},
        }
        if stage in {"package", "ready"}:
            return {"outcome": "success"}
        if stage == "plan_review":
            s = self.snapshot()
            return {"outcome": "approved", "payload": {"findings": [], "criterion_ids": ["AC-01"],
                "zero_context_executable": True, "approved_binding": {"plan_sha256": s["artifacts"]["plan"]["sha256"],
                "definition_version": s["task"]["definition_version"]}}}
        return {"outcome": "success", "payload": copy.deepcopy(payloads[stage])}

    def reach(self, stage):
        for _ in range(15):
            current = self.snapshot()["run"]["current_node"]
            if current == stage:
                return
            self.submit(self.raw(current))
        self.fail("Did not reach stage")

    def finish(self):
        self.reach("ready")
        self.submit(self.raw("ready"))
        return self.snapshot()

    def resume(self, **kwargs):
        s = self.snapshot()
        w = s["run"]["wait"]
        return self.flow.resume_wait(self.rid, expected_revision=s["run"]["revision"],
            expected_task_version=s["task"]["version"], wait_id=w["wait_id"], node_id=w["node_id"], **kwargs)

    def test_explicit_ready_without_claim_and_real_artifacts(self):
        self.assertFalse(hasattr(self.flow, "step"))
        self.assertFalse(hasattr(self.flow, "adapters"))
        s = self.finish()
        self.assertEqual(s["task"]["status"], "ready")
        self.assertIsNone(s["task"]["active_claim"])
        self.assertIsNone(s["task"]["active_run_ref"])
        self.assertEqual(s["run"]["state"], "succeeded")
        self.assertFalse(s["sync_pending"])
        self.assertNotIn("specification", s["task"]["artifacts"])
        for record in s["artifacts"].values():
            self.flow.repository.verify(record["ref"], record["role"], record["version"])
        plan = s["artifacts"]["plan"]
        self.assertEqual(self.service.get_document(self.task["id"], "plan").encode(),
                         self.flow.repository.get(plan["ref"], "plan", plan["version"]).content)
        self.assertEqual(self.service.health_check(), [])

    def test_invalid_and_stale_actions_atomic(self):
        before = self.snapshot()
        for raw in ({"outcome": "success", "payload": {}}, {"outcome": "other"},
                    {"outcome": "success", "payload": {"summary": "x", "evidence_refs": []}, "route": "ready"},
                    {"outcome": "needs_input", "question": ""}, {"outcome": "success", "payload": {"x": float("nan")}}):
            with self.assertRaises(RuntimeError):
                self.submit(raw)
            self.assertEqual(before, self.snapshot())
        for rv, tv in ((0, before["task"]["version"]), (1, 99), (True, before["task"]["version"])):
            with self.assertRaises(RuntimeError):
                self.flow.submit(self.rid, self.raw("context"), expected_revision=rv, expected_task_version=tv)
            self.assertEqual(before, self.snapshot())
        self.submit(self.raw("context"))
        after = self.snapshot()
        with self.assertRaises(RuntimeError):
            self.flow.submit(self.rid, self.raw("context"), expected_revision=1, expected_task_version=before["task"]["version"])
        self.assertEqual(after, self.snapshot())

    def test_wait_resume_is_separate_and_answer_survives_bad_submit(self):
        self.submit({"outcome": "needs_input", "question": "Which API?"})
        s = self.snapshot()
        self.assertEqual(s["task"]["status"], "awaiting_input")
        with self.assertRaises(RuntimeError):
            self.flow.resume_wait(self.rid, expected_revision=s["run"]["revision"], expected_task_version=s["task"]["version"],
                                  wait_id="wrong", node_id="context", answer=None)
        self.assertEqual(s, self.snapshot())
        self.resume(answer=None)
        resumed = self.snapshot()
        self.assertIsNone(resumed["run"]["resumed_wait"]["answer"])
        self.assertEqual(resumed["run"]["current_node"], "context")
        self.assertEqual(resumed["task"]["status"], "preparing")
        self.assertEqual(len(resumed["task"]["user_decisions"]), 1)
        with self.assertRaises(RuntimeError):
            self.submit({"outcome": "success", "payload": {}})
        self.assertEqual(resumed, self.snapshot())
        self.assertEqual(self.flow.request(self.rid)["resumed_wait"], resumed["run"]["resumed_wait"])
        self.finish()

    def test_blocker_resolution_without_reasoning_dispatch(self):
        self.submit({"outcome": "blocked", "reason": "No access"})
        self.assertEqual(self.snapshot()["task"]["status"], "blocked")
        with self.assertRaises(RuntimeError):
            self.resume(answer="no", resolution="Fixed")
        self.resume(resolution="Access granted")
        self.assertEqual(self.snapshot()["run"]["resumed_wait"]["resolution"], "Access granted")
        self.assertEqual(self.finish()["task"]["blockers"][0]["status"], "resolved")

    def test_invalid_plan_constraints_dependencies_and_validation_do_not_publish(self):
        self.reach("planning")
        before = self.snapshot()
        variants = [self.raw("planning") for _ in range(4)]
        variants[0]["payload"]["global_constraints"] = []
        variants[1]["payload"]["work_units"][0]["depends_on"] = ["WU-1"]
        variants[2]["payload"]["work_units"][0]["validation"] = []
        variants[3]["payload"]["work_units"][0]["depends_on"] = ["missing"]
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(PreparationError):
                self.submit(raw)
            self.assertEqual(before, self.snapshot())
        self.assertNotIn("plan", before["task"]["artifacts"])

    def test_review_coverage_binding_and_malformed_findings_do_not_publish(self):
        self.reach("plan_review")
        before = self.snapshot()
        variants = [self.raw("plan_review") for _ in range(7)]
        variants[0]["payload"]["approved_binding"]["definition_version"] = True
        variants[1]["payload"]["criterion_ids"] = ["AC-unknown"]
        variants[2]["payload"]["findings"] = [{"summary": "Invalid", "severity": "unknown"}]
        variants[3]["payload"]["findings"] = [{"summary": "Invalid", "severity": []}]
        variants[4]["payload"]["findings"] = [{"summary": "Critical", "severity": "critical", "status": "open", "evidence_refs": ["src/api.py"]}]
        variants[5]["payload"]["findings"] = [{"summary": "Missing evidence", "severity": "major"}]
        variants[6]["route"] = "ready"
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(PreparationError):
                self.submit(raw)
            self.assertEqual(before, self.snapshot())
        self.assertNotIn("plan_review", before["task"]["artifacts"])

    def test_wait_is_supported_at_each_semantic_stage_and_gate(self):
        for stage in ("context", "analysis", "planning", "plan_review", "package", "ready"):
            with self.subTest(stage=stage):
                self.task = self.service.create_task(title="Wait", task_type="implementation", objective="Wait",
                    original_request="Wait", acceptance_criteria=["Pass"], constraints=["Keep API"])
                self.run = self.flow.start(self.task["id"], expected_task_version=self.task["version"], prepared_source_revision="src")
                self.rid = self.run.run_id
                self.reach(stage)
                previous = self.snapshot()["run"]["results"]
                self.submit({"outcome": "needs_input", "question": "Clarify"})
                self.assertEqual(self.snapshot()["task"]["status"], "awaiting_input")
                self.resume(answer="confirmed")
                resumed = self.snapshot()
                with self.assertRaises(PreparationError):
                    self.submit({"outcome": "unknown"})
                self.assertEqual(resumed, self.snapshot())
                self.assertEqual(resumed["run"]["resumed_wait"]["answer"], "confirmed")
                self.assertEqual(resumed["run"]["current_node"], stage)
                for earlier, result in previous.items():
                    if earlier != stage:
                        self.assertEqual(resumed["run"]["results"][earlier], result)
                self.assertEqual(self.finish()["task"]["status"], "ready")

    def test_projection_io_failure_retries_sync_without_another_submit(self):
        self.reach("planning")
        original = os.replace
        def fail_projection(source, target):
            if Path(target).name == "plan.md":
                raise PermissionError("injected projection failure")
            return original(source, target)
        with patch("orchestrator.preparation_primitives.os.replace", side_effect=fail_projection):
            with self.assertRaises(PreparationError) as error:
                self.submit(self.raw("planning"))
        self.assertEqual(error.exception.code, "repository_failure")
        accepted = self.snapshot()
        self.assertTrue(accepted["sync_pending"])
        self.assertNotIn("plan", accepted["task"]["artifacts"])
        self.flow.synchronize(self.rid)
        self.assertEqual(accepted["run"], self.snapshot()["run"])
        self.assertEqual(self.finish()["task"]["status"], "ready")

    def test_external_blocker_is_not_adopted_as_owned_preparation(self):
        task = self.service.get_task(self.task["id"])
        blocked = self.service.add_blocker(task["id"], task["version"], blocker_type="external", summary="Stop")
        with self.assertRaises(PreparationError):
            self.submit(self.raw("context"))
        self.flow.reconcile(self.rid, expected_version=blocked["version"])
        with self.assertRaises(PreparationError) as error:
            self.submit(self.raw("context"))
        self.assertEqual(error.exception.code, "invalid_state")
        self.assertEqual(self.service.get_task(task["id"]), blocked)

    def test_review_revisions_binding_and_limits(self):
        self.reach("plan_review")
        before = self.snapshot()
        raw = self.raw("plan_review")
        raw["payload"]["approved_binding"]["plan_sha256"] = "0" * 64
        with self.assertRaises(PreparationError):
            self.submit(raw)
        self.assertEqual(before, self.snapshot())
        self.submit({"outcome": "changes_required", "payload": {"findings": [{"summary": "Add regression"}]}})
        raw = self.raw("planning")
        raw["payload"]["work_units"][0]["validation"].append("Regression")
        self.submit(raw)
        self.assertNotEqual(before["artifacts"]["plan"]["sha256"], self.snapshot()["artifacts"]["plan"]["sha256"])
        self.assertEqual(self.finish()["task"]["status"], "ready")

    def test_review_cycle_exhaustion_blocks_and_preserves_review(self):
        self.reach("plan_review")
        raw = {"outcome": "changes_required", "payload": {"findings": [{"summary": "Not executable"}]}}
        self.submit(raw)
        self.submit(self.raw("planning"))
        self.submit(raw)
        s = self.snapshot()
        self.assertEqual(s["run"]["state"], "blocked")
        self.assertEqual(s["task"]["status"], "blocked")
        self.assertIn("plan_review", s["artifacts"])
        self.assertNotIn("execution_package", s["task"]["artifacts"])

    def test_context_and_global_limits(self):
        self.flow.max_context_expansions = 1
        self.reach("analysis")
        raw = {"outcome": "needs_context", "payload": {"requests": ["More consumers"]}}
        self.submit(raw)
        self.submit(self.raw("context"))
        self.submit(raw)
        self.assertEqual(self.snapshot()["task"]["status"], "blocked")
        with tempfile.TemporaryDirectory() as other:
            flow = AgentPreparation(Path(other), max_results=1)
            t = flow.service.create_task(title="x",task_type="implementation",objective="x",original_request="x",acceptance_criteria=["x"])
            r = flow.start(t["id"],expected_task_version=1,prepared_source_revision="x")
            flow.submit(r.run_id,self.raw("context"),expected_revision=1,expected_task_version=2)
            self.assertNotIn("submit",flow.available_actions(r.run_id)["actions"])

    def test_partial_publication_can_retry_but_not_advance(self):
        with patch.object(self.flow.repository,"put",side_effect=ArtifactError("repository_failure","disk")):
            with self.assertRaises(PreparationError):
                self.submit(self.raw("context"))
        s = self.snapshot()
        self.assertEqual(s["run"]["current_node"],"analysis")
        self.assertTrue(s["sync_pending"])
        with self.assertRaises(PreparationError):
            self.submit(self.raw("analysis"))
        self.flow.synchronize(self.rid)
        self.assertEqual(self.snapshot()["run"],s["run"])
        self.finish()

    def test_projection_conflict_preserves_user_file(self):
        path=self.root/".orchestrator"/"tasks"/self.task["id"]/"plan.md"
        path.parent.mkdir(parents=True)
        path.write_text("User plan",encoding="utf-8")
        self.reach("planning")
        with self.assertRaises(PreparationError) as error:
            self.submit(self.raw("planning"))
        self.assertEqual(error.exception.code,"projection_conflict")
        self.assertEqual(path.read_text(),"User plan")
        self.assertTrue(self.snapshot()["sync_pending"])

    def test_version_reconcile_and_definition_drift_cleanup(self):
        t=self.service.get_task(self.task["id"])
        t=self.service.update_metadata(t["id"],t["version"],title="New title")
        with self.assertRaises(PreparationError):
            self.submit(self.raw("context"))
        self.flow.reconcile(self.rid,expected_version=t["version"])
        self.submit(self.raw("context"))
        t=self.service.get_task(t["id"])
        t=self.service.refine_task_definition(t["id"],t["version"],objective="Other")
        with self.assertRaises(PreparationError) as error:
            self.flow.reconcile(self.rid,expected_version=t["version"])
        self.assertEqual(error.exception.code,"stale_preparation")
        r=self.flow.cancel(self.rid,expected_revision=self.snapshot()["run"]["revision"],expected_task_version=t["version"],reason="New definition")
        self.assertEqual(r.state,"cancelled")
        self.assertIsNone(self.service.get_task(t["id"])["active_run_ref"])
        self.assertEqual(self.service.get_task(t["id"])["status"],"preparing")

    def test_unknown_applied_artifact_is_not_repeated(self):
        self.reach("planning")
        original=self.service.attach_artifact
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError("Lost response")
        with patch.object(self.service,"attach_artifact",side_effect=lost):
            with self.assertRaises(PreparationError) as error:
                self.submit(self.raw("planning"))
        self.assertEqual(error.exception.code,"effect_outcome_unknown")
        s=self.snapshot()
        history=len(self.service.get_history(self.task["id"]))
        with self.assertRaises(PreparationError):
            self.flow.synchronize(self.rid)
        self.flow.reconcile_effect(self.rid,expected_task_version=s["task"]["version"],applied=True)
        self.flow.synchronize(self.rid)
        self.assertEqual(history,len(self.service.get_history(self.task["id"])))
        self.finish()

    def test_unknown_unapplied_effect_requires_exact_snapshot(self):
        with patch.object(self.service,"transition_status",side_effect=TimeoutError("No response")):
            with self.assertRaises(PreparationError):
                self.submit({"outcome":"needs_input","question":"Question?"})
        s=self.snapshot()
        with self.assertRaises(PreparationError):
            self.flow.reconcile(self.rid,expected_version=s["task"]["version"])
        with self.assertRaises(PreparationError):
            self.flow.reconcile_effect(self.rid,expected_task_version=s["task"]["version"],applied=True)
        self.flow.reconcile_effect(self.rid,expected_task_version=s["task"]["version"],applied=False)
        self.flow.synchronize(self.rid)
        self.assertEqual(self.snapshot()["task"]["status"],"awaiting_input")

    def test_unknown_with_additional_external_event_is_not_auto_recovered(self):
        original=self.service.add_blocker
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError()
        with patch.object(self.service,"add_blocker",side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit({"outcome":"blocked","reason":"No access"})
        t=self.service.get_task(self.task["id"])
        t=self.service.update_metadata(t["id"],t["version"],title="External")
        with self.assertRaises(PreparationError):
            self.flow.reconcile_effect(self.rid,expected_task_version=t["version"],applied=True)
        self.assertIsNotNone(self.snapshot()["unknown_effect"])

    def test_unknown_blocker_recovers_owned_identity(self):
        original=self.service.add_blocker
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError()
        with patch.object(self.service,"add_blocker",side_effect=lost):
            with self.assertRaises(PreparationError):
                self.submit({"outcome":"blocked","reason":"No access"})
        self.flow.reconcile_effect(self.rid,expected_task_version=self.snapshot()["task"]["version"],applied=True)
        self.flow.synchronize(self.rid)
        self.resume(resolution="Fixed")
        self.finish()

    def test_failed_result_blocks_task_and_cancel_does_not_cancel_task(self):
        self.submit({"outcome":"failure","reason":"Invalid project"})
        self.assertEqual(self.snapshot()["run"]["state"],"failed")
        self.assertEqual(self.snapshot()["task"]["status"],"blocked")
        self.assertIsNone(self.snapshot()["task"]["active_run_ref"])

    def test_gate_cannot_forge_package_or_ignore_plan_drift(self):
        self.reach("package")
        before=self.snapshot()
        with self.assertRaises(PreparationError):
            self.submit({"outcome":"success","payload":{"plan":"forged"}})
        self.assertEqual(before,self.snapshot())
        self.submit(self.raw("package"))
        path=self.root/self.snapshot()["task"]["artifacts"]["plan"]["path"]
        path.write_text("Changed",encoding="utf-8")
        with self.assertRaises(PreparationError):
            self.submit(self.raw("ready"))
        self.assertNotEqual(self.snapshot()["task"]["status"],"ready")
        self.assertFalse(self.snapshot()["sync_pending"])

    def test_fixed_root_and_request_copy_isolation(self):
        request=self.flow.request(self.rid)
        request["task"]["constraints"].clear()
        request["project_profile"]["x"]=1
        self.assertEqual(self.flow.request(self.rid)["task"]["constraints"],["Keep API"])
        with tempfile.TemporaryDirectory() as other:
            service=TaskManagerService(Path(other))
            t=service.create_task(title="Other",task_type="implementation",objective="Other",original_request="Other",acceptance_criteria=["Other"])
            self.submit(self.raw("context"))
            self.assertEqual(service.get_task(t["id"])["version"],1)

    def test_concurrent_duplicate_submit_accepts_only_one(self):
        s=self.snapshot()
        barrier=Barrier(2)
        def submit():
            barrier.wait()
            try:
                self.flow.submit(self.rid,self.raw("context"),expected_revision=s["run"]["revision"],expected_task_version=s["task"]["version"])
                return "accepted"
            except RuntimeError as exc:
                return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:submit(),range(2)))
        self.assertEqual(results.count("accepted"),1)
        self.assertEqual(len(self.snapshot()["run"]["history"]),1)

    def test_unknown_effect_recovery_at_each_task_boundary(self):
        for method, stage, raw in (
            ("transition_status", "context", {"outcome":"needs_input","question":"API?"}),
            ("link_workflow_run", "context", {"outcome":"needs_input","question":"API?"}),
            ("attach_artifact", "plan_review", None),
            ("attach_execution_package", "package", None),
            ("mark_ready", "ready", None),
        ):
            with self.subTest(method=method,stage=stage), tempfile.TemporaryDirectory() as root:
                previous=(self.flow,self.service,self.task,self.rid)
                try:
                    self.flow=AgentPreparation(Path(root))
                    self.service=self.flow.service
                    self.task=self.service.create_task(title="Fix",task_type="implementation",objective="Fix",original_request="Fix",
                        acceptance_criteria=["Pass"],constraints=["Keep API"])
                    r=self.flow.start(self.task["id"],expected_task_version=1,prepared_source_revision="source")
                    self.rid=r.run_id
                    self.reach(stage)
                    original=getattr(self.service,method)
                    def lost(*args,**kwargs):
                        original(*args,**kwargs)
                        raise TimeoutError()
                    with patch.object(self.service,method,side_effect=lost):
                        with self.assertRaises(PreparationError):
                            self.submit(raw or self.raw(stage))
                    count=len(self.service.get_history(self.task["id"]))
                    self.flow.reconcile_effect(self.rid,expected_task_version=self.snapshot()["task"]["version"],applied=True)
                    self.flow.synchronize(self.rid)
                    # link_workflow_run has no subsequent mutations here; others may
                    # have their remaining pending effects, but never repeat intent.
                    events=self.service.get_history(self.task["id"])
                    self.assertGreaterEqual(len(events),count)
                    self.assertFalse(self.snapshot()["sync_pending"])
                    self.assertIsNone(self.snapshot()["unknown_effect"])
                finally:
                    self.flow,self.service,self.task,self.rid=previous

    def test_unknown_resume_decision_and_resolution_recover_without_duplicate(self):
        for kind, method in (("user_input","record_user_decision"),("blocker","resolve_blocker")):
            with self.subTest(kind=kind):
                self.submit({"outcome":"needs_input","question":"API?"} if kind=="user_input" else {"outcome":"blocked","reason":"Access"})
                original=getattr(self.service,method)
                def lost(*args,**kwargs):
                    original(*args,**kwargs)
                    raise TimeoutError()
                with patch.object(self.service,method,side_effect=lost):
                    with self.assertRaises(PreparationError):
                        self.resume(**({"answer":"v1"} if kind=="user_input" else {"resolution":"Fixed"}))
                self.flow.reconcile_effect(self.rid,expected_task_version=self.snapshot()["task"]["version"],applied=True)
                self.flow.synchronize(self.rid)
                self.assertEqual(self.snapshot()["task"]["status"],"preparing")
                self.assertEqual(len(self.snapshot()["task"]["user_decisions"]),1)

    def test_start_unknown_response_preserves_recoverable_run(self):
        flow=AgentPreparation(self.root)
        t=self.service.create_task(title="Other",task_type="implementation",objective="Other",original_request="Other",acceptance_criteria=["Pass"])
        original=flow.service.start_preparation
        def lost(*args,**kwargs):
            original(*args,**kwargs)
            raise TimeoutError()
        with patch.object(flow.service,"start_preparation",side_effect=lost):
            with self.assertRaises(PreparationError) as error:
                flow.start(t["id"],expected_task_version=1,prepared_source_revision="source")
        rid=error.exception.details["run_id"]
        flow.reconcile_effect(rid,expected_task_version=flow.inspect(rid)["task"]["version"],applied=True)
        flow.synchronize(rid)
        self.assertEqual(flow.available_actions(rid)["actions"],["submit","cancel"])

    def test_corrupt_repository_prevents_ready_without_mutation(self):
        self.reach("ready")
        s=self.snapshot()
        path=self.root/s["artifacts"]["plan_review"]["path"]
        path.write_bytes(b"Corrupt")
        with self.assertRaises(PreparationError):
            self.submit(self.raw("ready"))
        self.assertEqual(s,self.snapshot())

    def test_ready_partial_sync_rechecks_artifacts_and_does_not_false_complete(self):
        self.reach("ready")
        # A definite failure after the close is recoverable at mark_ready.
        with patch.object(self.service,"mark_ready",side_effect=TaskError("guard_failed","Temporary guard")):
            with self.assertRaises(PreparationError):
                self.submit(self.raw("ready"))
        s=self.snapshot()
        self.assertEqual(s["run"]["state"],"succeeded")
        self.assertEqual(s["task"]["status"],"preparing")
        self.assertIsNone(s["task"]["active_run_ref"])
        self.assertTrue(s["sync_pending"])
        self.flow.synchronize(self.rid)
        self.assertEqual(self.snapshot()["task"]["status"],"ready")


if __name__ == "__main__":
    unittest.main()
