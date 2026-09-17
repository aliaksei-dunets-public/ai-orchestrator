from __future__ import annotations

import copy
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from orchestrator import ArtifactRepository, PreparationWorkflow, PreparationError, WaitState, RuntimeError, Graph, GraphRuntime, Node
from orchestrator_task_manager import TaskManagerService


class PreparationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.service = TaskManagerService(self.root)
        self.repository = ArtifactRepository(self.root)
        self.task = self.service.create_task(title="Test", task_type="implementation", original_request="Test",
            objective="Test", acceptance_criteria=["Passed"], constraints=["Keep API"])
        self.adapters = {"context": self.context, "analysis": self.analysis,
                         "planning": self.planning, "plan_review": self.review}

    @staticmethod
    def context(request):
        return {"outcome": "success", "payload": {"summary": "Current project", "evidence_refs": ["src/example.py"]}}

    @staticmethod
    def analysis(request):
        return {"outcome": "success", "payload": {"objective_interpretation": "Fix test", "constraints": [],
                                                   "invariants": [], "unknowns": []}}

    @staticmethod
    def planning(request):
        return {"outcome": "success", "payload": {"goal": "Fix test", "global_constraints": ["Keep API"],
            "scope": {"in": ["API fix"], "out": ["Unrelated changes"]}, "global_validation": ["Run suite"],
            "work_units": [{"id": "WU-1", "goal": "Implement", "files_objects": ["src/example.py"],
                            "expected_result": ["API works"], "validation": ["Run tests"], "depends_on": []}]}}

    @staticmethod
    def review(request):
        plan = request["previous"]["planning"]["artifacts"]["plan"]
        return {"outcome": "approved", "payload": {"findings": [], "zero_context_executable": True,
            "criterion_ids": ["AC-01"], "approved_binding": {"plan_sha256": plan["sha256"],
            "definition_version": request["task"]["definition_version"]}}}

    def start(self, **options):
        flow = PreparationWorkflow(self.service, self.repository, self.adapters, **options)
        run = flow.start(self.task["id"], prepared_source_revision="source-v1")
        return flow, run.run_id

    def finish(self, flow, run_id, limit=15):
        for _ in range(limit):
            snapshot = flow.inspect(run_id)
            if snapshot["run"]["state"] in {"succeeded", "failed", "blocked", "waiting_input"}:
                return snapshot
            flow.step(run_id)
        self.fail("Workflow did not stop")

    def test_happy_path_crosses_ready_guard_without_execution(self):
        flow, run_id = self.start()
        snapshot = self.finish(flow, run_id)
        task = snapshot["task"]
        self.assertEqual(task["status"], "ready")
        self.assertEqual(snapshot["run"]["phase"], "preparation")
        self.assertFalse(snapshot["sync_pending"])
        self.assertIsNone(task["active_claim"])
        self.assertIsNone(task["active_run_ref"])
        self.assertEqual(task["prepared_source_revision"], "source-v1")
        self.assertEqual(set(snapshot["artifacts"]), {"context", "analysis", "plan", "plan_review", "execution_package"})
        self.assertNotIn("specification", task["artifacts"])
        plan = task["artifacts"]["plan"]["metadata"]["repository"]
        stored = self.repository.get(plan["ref"], plan["role"], plan["version"])
        self.assertEqual(self.service.get_document(task["id"], "plan").encode("utf-8"), stored.content)
        self.assertEqual(snapshot["run"]["state"], "succeeded")
        self.assertEqual(self.service.health_check(), [])

    def test_user_wait_identity_and_resume_do_not_repeat_previous_nodes(self):
        calls = []
        def analysis(request):
            calls.append(request["answer"])
            if request["answer"] is None:
                return {"outcome": "needs_input", "question": "Which API?"}
            return self.analysis(request)
        self.adapters["analysis"] = analysis
        flow, run_id = self.start()
        flow.step(run_id)
        wait = flow.step(run_id)
        self.assertIsInstance(wait, WaitState)
        self.assertEqual(flow.inspect(run_id)["task"]["status"], "awaiting_input")
        version = flow.inspect(run_id)["task"]["version"]
        for invalid in ("stale", None):
            with self.assertRaises(RuntimeError):
                flow.resume(run_id, {"api": "v1"}, wait_id=invalid, node_id=wait.node_id)
        self.assertEqual(flow.inspect(run_id)["task"]["version"], version)
        flow.resume(run_id, {"api": "v1"}, wait_id=wait.wait_id, node_id=wait.node_id)
        snapshot = self.finish(flow, run_id)
        self.assertEqual(snapshot["task"]["status"], "ready")
        self.assertEqual(calls, [None, {"api": "v1"}])
        self.assertEqual(len(snapshot["task"]["user_decisions"]), 1)

    def test_invalid_resume_result_preserves_task_and_runtime_wait(self):
        self.adapters["context"] = lambda request: ({"outcome": "needs_input", "question": "Question"}
            if request["answer"] is None else {"outcome": "success", "payload": {}})
        flow, run_id = self.start()
        wait = flow.step(run_id)
        before = flow.inspect(run_id)
        with self.assertRaises(PreparationError):
            flow.resume(run_id, "answer", wait_id=wait.wait_id, node_id=wait.node_id)
        after = flow.inspect(run_id)
        self.assertEqual(before["task"], after["task"])
        self.assertEqual(before["run"]["wait"], after["run"]["wait"])
        self.assertFalse(after["sync_pending"])

    def test_owned_blocker_is_resolved_before_ready(self):
        self.adapters["analysis"] = lambda request: (self.analysis(request) if request["answer"] == "fixed"
            else {"outcome": "blocked", "reason": "Missing access"})
        flow, run_id = self.start()
        self.finish(flow, run_id)
        snapshot = flow.inspect(run_id)
        wait = snapshot["run"]["wait"]
        self.assertEqual(snapshot["task"]["status"], "blocked")
        self.assertIsNone(snapshot["task"]["active_run_ref"])
        flow.resume_blocked(run_id, resolution="Access granted", answer="fixed", wait_id=wait["wait_id"], node_id=wait["node_id"])
        snapshot = self.finish(flow, run_id)
        self.assertEqual(snapshot["task"]["status"], "ready")
        self.assertTrue(all(item["status"] == "resolved" for item in snapshot["task"]["blockers"]))

    def test_changes_required_revises_plan_and_review_binding(self):
        calls = []
        def review(request):
            calls.append(request["previous"]["planning"]["artifacts"]["plan"]["sha256"])
            if len(calls) == 1:
                return {"outcome": "changes_required", "payload": {"findings": [{"summary": "Add regression"}]}}
            return self.review(request)
        def planning(request):
            result = self.planning(request)
            if "plan_review" in request["previous"]:
                result["payload"]["work_units"][0]["validation"].append("Run regression")
            return result
        self.adapters.update(plan_review=review, planning=planning)
        flow, run_id = self.start()
        snapshot = self.finish(flow, run_id)
        self.assertEqual(snapshot["task"]["status"], "ready")
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0], calls[1])
        self.assertEqual(snapshot["task"]["artifacts"]["plan_review"]["metadata"]["plan_sha256"], calls[-1])

    def test_review_cycle_exhaustion_stops_without_blind_third_cycle(self):
        calls = []
        def review(request):
            calls.append(request)
            return {"outcome": "changes_required", "payload": {"findings": [{"summary": "Still incomplete"}]}}
        self.adapters["plan_review"] = review
        flow, run_id = self.start()
        snapshot = self.finish(flow, run_id)
        self.assertEqual(snapshot["task"]["status"], "blocked")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("execution_package", snapshot["task"]["artifacts"])
        with self.assertRaises(RuntimeError):
            flow.step(run_id)
        self.assertEqual(len(calls), 2)

    def test_context_expansion_limit(self):
        self.adapters["analysis"] = lambda request: {"outcome": "needs_context", "payload": {"requests": ["More consumers"]}}
        flow, run_id = self.start(max_context_expansions=1)
        snapshot = self.finish(flow, run_id)
        self.assertEqual(snapshot["task"]["status"], "blocked")
        self.assertNotIn("plan", snapshot["task"]["artifacts"])

    def test_stale_review_or_incomplete_coverage_cannot_publish_approval(self):
        flow, run_id = self.start()
        for _ in range(3):
            flow.step(run_id)
        for field, value in (("plan_sha256", "0" * 64), ("definition_version", True)):
            def review(request):
                result = self.review(request)
                result["payload"]["approved_binding"][field] = value
                return result
            flow.adapters["plan_review"] = review
            with self.assertRaises(PreparationError) as caught:
                flow.step(run_id)
            self.assertEqual(caught.exception.code, "stale_review")
        flow.adapters["plan_review"] = lambda request: {**self.review(request), "payload": {
            **self.review(request)["payload"], "criterion_ids": ["AC-unknown"]}}
        with self.assertRaises(PreparationError):
            flow.step(run_id)
        self.assertNotIn("plan_review", flow.inspect(run_id)["task"]["artifacts"])
        self.assertEqual(flow.inspect(run_id)["run"]["current_node"], "plan_review")

    def test_modified_plan_fails_real_ready_guard_and_keeps_pending_sync(self):
        flow, run_id = self.start()
        for _ in range(5):
            flow.step(run_id)
        task = flow.inspect(run_id)["task"]
        path = self.root / task["artifacts"]["plan"]["path"]
        original = path.read_bytes()
        path.write_bytes(b"tampered")
        with self.assertRaises(PreparationError) as caught:
            flow.step(run_id)
        self.assertEqual(caught.exception.code, "guard_failed")
        snapshot = flow.inspect(run_id)
        self.assertEqual(snapshot["task"]["status"], "preparing")
        self.assertTrue(snapshot["sync_pending"])
        with self.assertRaises(PreparationError) as caught:
            flow.step(run_id)
        self.assertEqual(caught.exception.code, "sync_pending")
        path.write_bytes(original)
        flow.synchronize(run_id)
        self.assertEqual(flow.inspect(run_id)["task"]["status"], "ready")

    def test_version_conflict_requires_explicit_reconcile_and_does_not_repeat_adapter(self):
        calls = []
        def context(request):
            calls.append(request)
            task = self.service.get_task(self.task["id"])
            self.service.update_metadata(task["id"], task["version"], title="External metadata update")
            return self.context(request)
        self.adapters["context"] = context
        flow, run_id = self.start()
        with self.assertRaises(PreparationError) as caught:
            flow.step(run_id)
        self.assertEqual(caught.exception.code, "task_version_conflict")
        self.assertTrue(flow.inspect(run_id)["sync_pending"])
        self.assertEqual(self.repository.list(), ())
        with self.assertRaises(PreparationError):
            flow.step(run_id)
        task = self.service.get_task(self.task["id"])
        flow.reconcile(run_id, expected_version=task["version"])
        flow.synchronize(run_id)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.finish(flow, run_id)["task"]["status"], "ready")

    def test_definition_change_and_external_blocker_are_not_silently_adopted(self):
        flow, run_id = self.start()
        task = self.service.get_task(self.task["id"])
        changed = self.service.refine_task_definition(task["id"], task["version"], objective="New requirement")
        with self.assertRaises(PreparationError) as caught:
            flow.reconcile(run_id, expected_version=changed["version"])
        self.assertEqual(caught.exception.code, "stale_preparation")
        with self.assertRaises(PreparationError):
            flow.step(run_id)

    def test_external_blocker_prevents_progress_and_ready(self):
        flow, run_id = self.start()
        task = self.service.get_task(self.task["id"])
        blocked = self.service.add_blocker(task["id"], task["version"], blocker_type="external", summary="Access")
        with self.assertRaises(PreparationError):
            flow.step(run_id)
        flow.reconcile(run_id, expected_version=blocked["version"])
        with self.assertRaises(PreparationError) as caught:
            flow.step(run_id)
        self.assertEqual(caught.exception.code, "invalid_state")
        self.assertEqual(flow.inspect(run_id)["task"]["status"], "blocked")

    def test_user_document_is_not_overwritten(self):
        destination = self.root / ".orchestrator" / "tasks" / self.task["id"] / "plan.md"
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"user document")
        flow, run_id = self.start()
        flow.step(run_id)
        flow.step(run_id)
        with self.assertRaises(PreparationError) as caught:
            flow.step(run_id)
        self.assertEqual(caught.exception.code, "projection_conflict")
        self.assertEqual(destination.read_bytes(), b"user document")
        self.assertNotIn("plan", flow.inspect(run_id)["task"]["artifacts"])

    def test_invalid_plan_lost_constraint_or_dependency_does_not_publish(self):
        flow, run_id = self.start()
        flow.step(run_id)
        flow.step(run_id)
        variants = [self.planning({}) for _ in range(3)]
        variants[0]["payload"]["global_constraints"] = []
        variants[1]["payload"]["work_units"][0]["depends_on"] = ["WU-1"]
        variants[2]["payload"]["work_units"][0]["validation"] = []
        for variant in variants:
            flow.adapters["planning"] = lambda request: copy.deepcopy(variant)
            with self.assertRaises(PreparationError):
                flow.step(run_id)
            self.assertFalse(flow.inspect(run_id)["sync_pending"])
        self.assertNotIn("plan", flow.inspect(run_id)["task"]["artifacts"])

    def test_waits_are_supported_at_every_adapter_stage(self):
        for stage in ("context", "analysis", "planning", "plan_review"):
            with self.subTest(stage=stage):
                self.task = self.service.create_task(title="Wait", task_type="implementation", original_request="Wait",
                    objective="Wait", acceptance_criteria=["Passed"], constraints=["Keep API"])
                adapters = {"context": self.context, "analysis": self.analysis, "planning": self.planning, "plan_review": self.review}
                original = adapters[stage]
                adapters[stage] = lambda request: ({"outcome": "needs_input", "question": "Clarify"}
                    if request["answer"] is None else original(request))
                flow = PreparationWorkflow(self.service, self.repository, adapters)
                run = flow.start(self.task["id"], prepared_source_revision="src")
                snapshot = self.finish(flow, run.run_id)
                self.assertEqual(snapshot["task"]["status"], "awaiting_input")
                wait = snapshot["run"]["wait"]
                flow.resume(run.run_id, "confirmed", wait_id=wait["wait_id"], node_id=wait["node_id"])
                self.assertEqual(self.finish(flow, run.run_id)["task"]["status"], "ready")

    def test_projection_io_failure_is_retryable_without_reexecuting_planner(self):
        flow, run_id = self.start()
        flow.step(run_id)
        flow.step(run_id)
        original = os.replace
        def fail_projection(source, target):
            if Path(target).name == "plan.md":
                raise PermissionError("injected projection failure")
            return original(source, target)
        with patch("orchestrator.preparation_workflow.os.replace", side_effect=fail_projection):
            with self.assertRaises(PreparationError) as caught:
                flow.step(run_id)
            self.assertEqual(caught.exception.code, "repository_failure")
        snapshot = flow.inspect(run_id)
        self.assertTrue(snapshot["sync_pending"])
        self.assertNotIn("plan", snapshot["task"]["artifacts"])
        flow.adapters["planning"] = lambda request: self.fail("Planner must not be repeated")
        flow.synchronize(run_id)
        self.assertEqual(self.finish(flow, run_id)["task"]["status"], "ready")

    def test_malformed_finding_and_adapter_route_do_not_advance_runtime(self):
        flow, run_id = self.start()
        for _ in range(3):
            flow.step(run_id)
        for severity in ("unknown", []):
            def review(request):
                result = self.review(request)
                result["payload"]["findings"] = [{"summary": "Invalid", "severity": severity}]
                return result
            flow.adapters["plan_review"] = review
            with self.assertRaises(PreparationError):
                flow.step(run_id)
            self.assertEqual(flow.inspect(run_id)["run"]["current_node"], "plan_review")
        flow.adapters["plan_review"] = lambda request: {**self.review(request), "route": "ready"}
        with self.assertRaises(PreparationError):
            flow.step(run_id)
        self.assertNotIn("plan_review", flow.inspect(run_id)["task"]["artifacts"])

    def test_runtime_phase_is_explicit_and_validated(self):
        runtime = GraphRuntime()
        node = Node("n", "input/v1", "output/v1", ("success",), {"success": "succeeded"})
        graph = Graph("g", 1, "n", {"n": node})
        self.assertEqual(runtime.create_run(graph, {}).phase, "request")
        self.assertEqual(runtime.create_run(graph, {}, phase="preparation").phase, "preparation")
        with self.assertRaises(RuntimeError):
            runtime.create_run(graph, {}, phase="invalid")


if __name__ == "__main__":
    unittest.main()
