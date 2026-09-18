import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from orchestrator import GraphStatus, KnowledgeRefreshResult

from orchestrator import AgentExecution, AgentPreparation, ExecutionPreflight, PreparationError
from orchestrator.workflow_binding import WorkflowSource, read_binding
from orchestrator.workflow_builder import read_toml
from orchestrator.workflow_execution import ExecutorRegistry, ModelAdapter, WorkflowExecutionError
from orchestrator.workflow_roles import (ComponentRole, WorkflowRoleRegistry, component_workflow,
    testing_gate_handler, documentation_gate_handler)
from tests.test_workflow_execution import LIBRARY, inputs, registry, fixture_response, finish


class WorkflowIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "orchestrator").mkdir()
        (self.root / "orchestrator/entry.py").write_text("VALUE=1\n")
        shutil.copytree(LIBRARY, self.root / "library")
        definition = self.root / "library/workflows/testing-and-documentation.toml"
        definition.write_text(definition.read_text(encoding="utf-8").replace('provider = "host"', 'provider = "fixture"')
            .replace('model = "current-host-model"', 'model = "fixture-standard"')
            .replace('model = "project-expert-model"', 'model = "fixture-expert"'), encoding="utf-8")
        self.source = WorkflowSource(definition, (self.root / "library",))
        self.prep = AgentPreparation(self.root, workflow_source=self.source)
        self.task = self.prep.service.create_task(title="Workflow", task_type="implementation", objective="Example",
            original_request="Example", acceptance_criteria=["Pass checks"])

    def prepare(self):
        run = self.prep.start(self.task["id"], expected_task_version=self.task["version"],
            prepared_source_revision=ExecutionPreflight(self.root).source_revision())
        payloads = {"context": {"summary": "Inspected", "evidence_refs": ["orchestrator/entry.py"]},
            "analysis": {"objective_interpretation": "Example", "constraints": [], "invariants": [], "unknowns": []},
            "planning": {"goal": "Example", "scope": {"in": ["Code"], "out": ["Other"]},
                "global_constraints": [], "global_validation": ["Checks"], "work_units": [{
                    "id": "WU-1", "goal": "Example", "files_objects": ["orchestrator"],
                    "expected_result": ["Done"], "validation": ["Checks"], "depends_on": []}]}}
        for _ in range(6):
            state = self.prep.inspect(run.run_id)
            stage = state["run"]["current_node"]
            if stage == "plan_review":
                binding = self.prep.request(run.run_id)["workflow_binding"]
                envelope = {"outcome": "approved", "payload": {"findings": [], "criterion_ids": ["AC-01"],
                    "zero_context_executable": True, "approved_binding": {
                        "plan_sha256": state["artifacts"]["plan"]["sha256"], "definition_version": 1,
                        "workflow_digest": binding["digest"]}}}
            elif stage in {"package", "ready"}:
                envelope = {"outcome": "success"}
            else:
                envelope = {"outcome": "success", "payload": payloads[stage]}
            self.prep.submit(run.run_id, envelope, expected_revision=state["run"]["revision"],
                             expected_task_version=state["task"]["version"])
        return self.prep.service.get_task(self.task["id"])

    def gates(self):
        task = self.prepare()
        flow = AgentExecution(self.root, workflow_source=self.source)
        run = flow.start(task["id"], expected_task_version=task["version"], worker_ref="fixture-worker")
        state = flow.inspect(run.run_id)
        before = state["checkpoint_revision"]
        flow.submit(run.run_id, {"outcome": "success", "payload": {"unit_id": "WU-1", "summary": "Checked",
            "source_before": before, "source_after": before, "changed_files": [], "evidence_refs": ["fixture-check"],
            "validation": {"status": "passed", "checks_run": ["fixture"], "failed": []}, "unresolved": []}},
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        state = flow.inspect(run.run_id)
        flow.submit(run.run_id, {"outcome": "handoff"}, expected_revision=state["run"]["revision"],
                    expected_task_version=state["task"]["version"])
        task = flow.service.get_task(task["id"])
        state = flow.inspect(run.run_id)
        gate = flow.start_gates(run.run_id, expected_revision=state["run"]["revision"], expected_task_version=task["version"])
        gid = gate["run"]["run_id"]
        flow.submit_gate(gid, {"outcome": "approved", "payload": {"summary": "Fixture self-review",
            "implementation_revision": gate["source_revision"], "candidate_revision": gate["candidate_revision"],
            "findings": [], "evidence_refs": ["fixture-self-review"]}}, expected_revision=gate["run"]["revision"],
            expected_task_version=gate["task"]["version"])
        return flow, gid

    def role(self, name, phase="execution", *, instance=None, handler=None, resolved=None):
        instance = instance or name
        resolved = resolved or self.source.load()
        _, definition = component_workflow(resolved, instance)
        return ComponentRole(name, phase, instance, definition.get("inputs", {}), definition.get("outputs", {}),
                             definition["outcomes"], handler or (lambda *args: {}))

    def test_plan_review_package_bind_and_readonly_preflight_requires_source(self):
        task = self.prepare()
        checked = ExecutionPreflight(self.root, workflow_source=self.source).check(task["id"], expected_task_version=task["version"])
        binding = checked["binding"]["workflow_binding"]
        self.assertEqual(read_binding(self.prep.repository, binding).digest, self.source.load().digest)
        self.assertEqual(task, self.prep.service.get_task(task["id"]))
        with self.assertRaises(PreparationError) as caught:
            ExecutionPreflight(self.root).check(task["id"], expected_task_version=task["version"])
        self.assertEqual(caught.exception.code, "workflow_required")

    def test_changed_definition_overlay_component_and_contract_block_preflight(self):
        task = self.prepare()
        paths = [self.source.definition, self.root / "library/components/testing-summary.toml",
                 self.root / "library/contracts/test-result.json"]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                if path.suffix == ".json":
                    value = json.loads(content)
                    value["schema"]["properties"]["summary"]["minLength"] = 2
                    path.write_text(json.dumps(value), encoding="utf-8")
                else:
                    path.write_text(content.replace('title = "', 'title = "Изменено: ', 1), encoding="utf-8")
                with self.assertRaises(PreparationError) as caught:
                    ExecutionPreflight(self.root, workflow_source=self.source).check(task["id"], expected_task_version=task["version"])
                self.assertEqual(caught.exception.code, "stale_workflow")
            path.write_text(content, encoding="utf-8")
        self.assertIsNone(self.prep.service.get_task(task["id"])["active_claim"])

    def test_tampered_immutable_snapshot_rejected(self):
        task = self.prepare()
        binding = ExecutionPreflight(self.root, workflow_source=self.source).bindings(task)["workflow_binding"]
        (self.root / binding["snapshot"]["path"]).write_text("{}")
        with self.assertRaises(Exception):
            ExecutionPreflight(self.root, workflow_source=self.source).check(task["id"], expected_task_version=task["version"])
        self.assertIsNone(self.prep.service.get_task(task["id"])["active_claim"])

    def test_testing_documentation_roles_use_frozen_snapshot_and_normal_gate_publication(self):
        flow, gid = self.gates()
        frozen = self.source.load()
        roles = WorkflowRoleRegistry()
        roles.register(self.role("testing", handler=testing_gate_handler(flow.repository), resolved=frozen))
        roles.register(self.role("documentation", handler=documentation_gate_handler(flow.repository,
            source_adjacent_changed=False), resolved=frozen))
        # После claim активный run сохраняет старую модель, даже если TOML изменён.
        self.source.definition.write_text(self.source.definition.read_text(encoding="utf-8").replace(
            'model = "fixture-standard"', 'model = "unavailable-new-model"'), encoding="utf-8")
        state = flow.gate_inspect(gid)
        testing = flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        with self.assertRaises(PreparationError):
            flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
                expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        with self.assertRaises(WorkflowExecutionError):
            flow.submit_component(gid, testing, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        finished = finish(testing.executor)
        receipt = finished["run"]["results"]["testing.summary"]["data"]["receipt"]
        self.assertEqual(receipt["model"], "fixture-standard")
        flow.submit_component(gid, testing, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        state = flow.gate_inspect(gid)
        self.assertEqual(state["run"]["current_node"], "documentation")
        values = inputs()
        values["testing_result"] = finished["result"]["outputs"]["result"]
        docs = flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=values,
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        finish(docs.executor)
        flow.submit_component(gid, docs, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        state = flow.gate_inspect(gid)
        self.assertEqual(state["run"]["current_node"], "knowledge_refresh")
        self.assertEqual(state["task"]["status"], "active")
        self.assertEqual(state["task"]["artifacts"]["testing"]["metadata"]["status"], "passed")
        self.assertEqual(flow.service.health_check(), [])
        class FixtureKnowledge:
            def precommit_refresh(self):
                return KnowledgeRefreshResult("indexed", {"digest": "fixture"}, {"version": "fixture-v1"},
                                              1, 0, mode="incremental")
            def status(self):
                return GraphStatus("fresh", {"digest": "fixture"}, {"digest": "fixture"},
                                   {"version": "fixture-v1"}, {"package": "fixture"})
        flow.knowledge_service = FixtureKnowledge()
        flow.refresh_knowledge(gid, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        state = flow.gate_inspect(gid)
        source, candidate = state["source_revision"], state["candidate_revision"]
        evidence = state["artifacts"]["testing"]["evidence_ref"]
        flow.submit_gate(gid, {"outcome": "ready", "payload": {"summary": "Fixture full lifecycle",
            "candidate_revision": candidate, "implementation_revision": source, "reviewed_revision": source,
            "tested_revision": source, "documented_revision": source, "knowledge_required": False,
            "knowledge_status": "success", "criteria": [{"id": "AC-01", "status": "satisfied", "evidence_refs": [evidence]}],
            "blocking_findings": [], "evidence_refs": [evidence], "acceptance_package": {
                "summary": "Fixture acceptance", "scenarios": [{"id": "UAT-01", "title": "Workflow", "action": "Run",
                "expected": "Passed"}], "automated_evidence": [evidence], "known_warnings": [], "known_limitations": []}}},
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        task = flow.service.get_task(self.task["id"])
        self.assertEqual(task["status"], "awaiting_acceptance")
        self.assertIsNone(task["active_claim"])
        self.assertIsNone(task["active_run_ref"])
        self.assertEqual(flow.service.health_check(), [])

    def test_role_mismatch_unknown_role_and_lifecycle_gate_replacement_rejected(self):
        flow, gid = self.gates()
        roles = WorkflowRoleRegistry()
        role = self.role("testing")
        role.inputs["unexpected"] = "task-request/v1"
        roles.register(role)
        state = flow.gate_inspect(gid)
        with self.assertRaises(WorkflowExecutionError) as caught:
            flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
                expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        self.assertEqual(caught.exception.code, "role_contract_mismatch")
        for name in ("ready", "package", "knowledge_refresh"):
            with self.assertRaises(WorkflowExecutionError):
                roles.register(ComponentRole(name, "execution", "testing", {}, {}, {}, lambda *a: {}))

    def test_stale_task_version_prevents_component_effect(self):
        flow, gid = self.gates()
        roles = WorkflowRoleRegistry()
        roles.register(self.role("testing", handler=testing_gate_handler(flow.repository)))
        state = flow.gate_inspect(gid)
        component = flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        task = flow.service.get_task(self.task["id"])
        flow.service.record_user_decision(task["id"], task["version"], decision_type="clarification", value="Changed")
        with self.assertRaises(PreparationError):
            component.executor.step(expected_revision=component.executor.inspect()["run"]["revision"])
        self.assertEqual(component.executor.inspect()["evidence"], [])

    def test_handler_cannot_bypass_testing_gate_validator(self):
        flow, gid = self.gates()
        roles = WorkflowRoleRegistry()
        roles.register(self.role("testing", handler=lambda *a: {"outcome": "passed", "payload": {"summary": "Invented"}}))
        state = flow.gate_inspect(gid)
        component = flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        finish(component.executor)
        with self.assertRaises(PreparationError):
            flow.submit_component(gid, component, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        self.assertEqual(flow.gate_inspect(gid)["run"]["current_node"], "testing")

    def test_preparation_role_uses_atomic_component_and_shared_publication(self):
        task = self.task
        run = self.prep.start(task["id"], expected_task_version=task["version"],
            prepared_source_revision=ExecutionPreflight(self.root).source_revision())
        roles = WorkflowRoleRegistry()
        def context_handler(result, request, evidence):
            return {"outcome": "success", "payload": {"summary": "Fixture scope: " +
                ", ".join(result["outputs"]["scope"]["checks"]),
                "evidence_refs": [f'{r["ref"]}:{r["role"]}:{r["version"]}' for r in evidence]}}
        roles.register(self.role("context", "preparation", instance="testing.scope", handler=context_handler))
        state = self.prep.inspect(run.run_id)
        component = self.prep.start_component(run.run_id, roles=roles, executors=registry(self.root), inputs=inputs(),
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        finish(component.executor)
        self.prep.submit_component(run.run_id, component, expected_revision=state["run"]["revision"],
                                   expected_task_version=state["task"]["version"])
        state = self.prep.inspect(run.run_id)
        self.assertEqual(state["run"]["current_node"], "analysis")
        self.assertIn("context", state["artifacts"])
        self.assertEqual(state["task"]["status"], "preparing")
        self.assertIsNone(state["task"]["active_claim"])
        self.assertEqual(self.prep.service.health_check(), [])

    def test_review_requires_workflow_digest(self):
        original = self.prep._review
        def lose_digest(payload, outcome, session):
            payload["approved_binding"].pop("workflow_digest")
            return original(payload, outcome, session)
        with patch.object(self.prep, "_review", side_effect=lose_digest):
            with self.assertRaises(PreparationError) as caught:
                self.prepare()
        self.assertEqual(caught.exception.code, "stale_review")
        self.assertEqual(self.prep.service.get_task(self.task["id"])["status"], "preparing")

    def test_ready_rejects_config_drift_after_package(self):
        original = self.prep._gate_result
        def change_before_ready(session, stage):
            if stage == "ready":
                self.source.definition.write_text(self.source.definition.read_text(encoding="utf-8").replace(
                    'model = "fixture-standard"', 'model = "changed-model"'), encoding="utf-8")
            return original(session, stage)
        with patch.object(self.prep, "_gate_result", side_effect=change_before_ready):
            with self.assertRaises(PreparationError) as caught:
                self.prepare()
        self.assertEqual(caught.exception.code, "stale_workflow")
        task = self.prep.service.get_task(self.task["id"])
        self.assertEqual(task["status"], "preparing")
        self.assertIsNone(task["active_claim"])

    def test_project_replacement_executes_selected_component_and_model(self):
        overlay = self.root / "replacement.toml"
        overlay.write_text((self.root / "library/examples/project-replacement.toml").read_text(encoding="utf-8")
            .replace('provider = "host"', 'provider = "fixture"')
            .replace('model = "project-selected-model"', 'model = "fixture-expert"'), encoding="utf-8")
        self.source = WorkflowSource(self.source.definition, (self.root / "library", self.root / "library/project-example"), overlay)
        self.prep = AgentPreparation(self.root, workflow_source=self.source)
        flow, gid = self.gates()
        roles = WorkflowRoleRegistry()
        roles.register(self.role("testing", handler=testing_gate_handler(flow.repository)))
        state = flow.gate_inspect(gid)
        component = flow.start_component(gid, roles=roles, executors=registry(self.root), inputs=inputs(),
            expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        finished = finish(component.executor)
        summary = component.executor.repository.get(**{
            k: finished["evidence"][-1][k] for k in ("ref", "role", "version")})
        value = json.loads(summary.content)
        self.assertEqual(value["component_ref"], "project/testing-summary@1")
        self.assertEqual(value["receipt"]["model"], "fixture-expert")
        flow.submit_component(gid, component, expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
        self.assertEqual(flow.gate_inspect(gid)["run"]["current_node"], "documentation")

    def test_overlay_drift_blocks_preflight(self):
        overlay = self.root / "overlay.toml"
        overlay.write_text('schema_version=1\n[nodes."testing.run"]\noperation="patch"\n'
                           '[nodes."testing.run".config]\nmax_transient_retries=0\n', encoding="utf-8")
        self.source = WorkflowSource(self.source.definition, self.source.libraries, overlay)
        self.prep = AgentPreparation(self.root, workflow_source=self.source)
        task = self.prepare()
        overlay.write_text(overlay.read_text().replace("retries=0", "retries=1"), encoding="utf-8")
        with self.assertRaises(PreparationError) as caught:
            ExecutionPreflight(self.root, workflow_source=self.source).check(task["id"], expected_task_version=task["version"])
        self.assertEqual(caught.exception.code, "stale_workflow")


if __name__ == "__main__":
    unittest.main()
