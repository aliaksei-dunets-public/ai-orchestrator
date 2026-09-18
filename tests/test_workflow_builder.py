from __future__ import annotations

import copy
import tempfile
import unittest
import contextlib
import io
from pathlib import Path

from orchestrator import AgentGraphRuntime, NodeResult, WaitState
from orchestrator.workflow_builder import (ComponentLibrary, WorkflowBuilder, WorkflowBuildError,
                                           read_toml, main, check_schema)
from orchestrator.workflow_viewer import render_workflow

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "workflow-library"
DEFINITION = LIBRARY / "workflows/testing-and-documentation.toml"


class WorkflowBuilderTests(unittest.TestCase):
    def setUp(self):
        self.library = ComponentLibrary(LIBRARY)
        self.builder = WorkflowBuilder(self.library)
        self.definition = read_toml(DEFINITION)

    def rejected(self, action, code=None):
        with self.assertRaises(WorkflowBuildError) as context:
            action()
        if code:
            self.assertEqual(context.exception.code, code)
        return context.exception

    def replace_summary(self, ref, **changes):
        manifest = self.library.get("core/testing-summary@1")
        manifest["component"]["id"] = ref.split("@")[0]
        manifest["component"]["version"] = int(ref.split("@")[1])
        manifest.update(changes)
        self.library.components[ref] = manifest
        return manifest

    def test_nested_exits_route_to_parent_and_graph_round_trip(self):
        resolved = self.builder.resolve(self.definition)
        self.assertEqual(resolved.graph.entry_node, "testing.scope")
        self.assertEqual(len(resolved.graph.nodes), 5)
        self.assertEqual(resolved.graph.nodes["testing.summary"].transitions["passed"], "documentation.impact")
        self.assertEqual(resolved.graph.nodes["testing.summary"].transitions["failed"], "failed")
        self.assertEqual(resolved.graph.nodes["documentation.update"].transitions["no_change"], "succeeded")
        from orchestrator import Graph
        self.assertEqual(Graph.from_dict(resolved.to_dict()["graph"]), resolved.graph)

    def test_compiled_graph_accepts_real_runtime_results_without_executor(self):
        resolved = self.builder.resolve(self.definition)
        runtime = AgentGraphRuntime()
        run = runtime.create_run(resolved.graph, {}, **resolved.runtime_options)
        payloads = [
            ("success", {"scope": {"checks": ["unit"]}}),
            ("finished", {"execution_record": {"passed": 1, "failed": 0, "evidence_refs": ["test:unit"]}}),
            ("passed", {"result": {"status": "passed", "summary": "Проверено", "evidence_refs": ["test:unit"]}}),
            ("assessed", {"impact": {"impacted": False, "targets": []}}),
            ("no_change", {"result": {"status": "no_change", "summary": "Нет влияния", "evidence_refs": ["impact:checked"]}}),
        ]
        for outcome, outputs in payloads:
            resolved.validate_outputs(run.current_node, outcome, outputs)
            run = runtime.submit_result(run.run_id, NodeResult(run.current_node, outcome, data=outputs), expected_revision=run.revision)
        self.assertEqual(run.state, "succeeded")
        self.assertEqual(len(run.history), 5)

    def test_failed_testing_does_not_execute_documentation(self):
        resolved = self.builder.resolve(self.definition)
        runtime = AgentGraphRuntime()
        run = runtime.create_run(resolved.graph, {})
        for outcome, outputs in [("success", {"scope": {"checks": ["unit"]}}),
                                 ("failure", {"execution_record": {"passed": 0, "failed": 1, "evidence_refs": ["test:failed"]}}),
                                 ("failed", {"result": {"status": "failed", "summary": "Ошибка", "evidence_refs": ["test:failed"]}})]:
            run = runtime.submit_result(run.run_id, NodeResult(run.current_node, outcome, data=outputs), expected_revision=run.revision)
        self.assertEqual(run.state, "failed")
        self.assertNotIn("documentation.impact", run.results)

    def test_project_patch_profile_config_budget_and_provenance(self):
        resolved = self.builder.load(DEFINITION, overlay=LIBRARY / "examples/project-overlay.toml")
        snap = resolved.to_dict()
        leaf = snap["leaves"]["testing.run"]
        self.assertEqual(leaf["config"]["max_transient_retries"], 0)
        self.assertNotIn("model_profile", leaf["execution"])
        self.assertEqual(snap["leaves"]["testing.summary"]["execution"]["model_profile"], "expert")
        node = snap["tree"]["children"]["testing"]["children"]["summary"]
        self.assertIn("project-overlay.toml", node["provenance"]["execution.model_profile"])
        self.assertIn("project-overlay.toml", snap["model_profile_provenance"]["expert.model"])
        self.assertEqual(resolved.runtime_options["node_limits"], {"testing.summary": 3})

    def test_compatible_node_replacement_does_not_inherit_old_execution(self):
        custom = self.replace_summary("project/custom-summary@1")
        custom["execution"]["instruction"] = "Проектная инструкция"
        self.definition["nodes"]["testing"]["execution"] = {"model_profile": "expert"}
        overlay = {"schema_version": 1, "nodes": {"testing.summary": {"operation": "replace", "ref": "project/custom-summary@1"}}}
        resolved = self.builder.resolve(self.definition, overlay=overlay)
        leaf = resolved.to_dict()["leaves"]["testing.summary"]
        self.assertEqual(leaf["ref"], "project/custom-summary@1")
        self.assertEqual(leaf["execution"]["instruction"], "Проектная инструкция")
        self.assertEqual(leaf["execution"]["model_profile"], "expert")

    def test_subgraph_replacement_and_child_patch_are_order_independent(self):
        custom = self.library.get("core/testing@1")
        custom["component"]["id"] = "project/testing"
        self.library.components["project/testing@1"] = custom
        parent = {"operation": "replace", "ref": "project/testing@1"}
        child = {"operation": "patch", "config": {"max_transient_retries": 2}}
        a = {"schema_version": 1, "nodes": {"testing.run": child, "testing": parent}}
        b = {"schema_version": 1, "nodes": {"testing": parent, "testing.run": child}}
        first = self.builder.resolve(self.definition, overlay=a)
        second = self.builder.resolve(self.definition, overlay=b)
        self.assertEqual(first.digest, second.digest)
        self.assertEqual(first.to_dict()["leaves"]["testing.run"]["config"]["max_transient_retries"], 2)

    def test_incompatible_replacement_is_rejected(self):
        custom = self.replace_summary("project/broken@1")
        custom["outputs"] = {"result": "documentation-summary/v1"}
        self.rejected(lambda: self.builder.resolve(self.definition, overlay={"schema_version": 1, "nodes": {
            "testing.summary": {"operation": "replace", "ref": "project/broken@1"}}}), "incompatible_replacement")

    def test_unavailable_output_on_one_branch_is_rejected(self):
        self.library.components["core/test-runner@1"]["outcomes"]["failure"] = []
        self.rejected(lambda: self.builder.resolve(self.definition), "unavailable_artifact")

    def test_artifact_produced_after_consumer_is_rejected(self):
        self.library.components["core/testing@1"]["component"]["entry"] = "summary"
        self.library.components["core/testing-summary@1"]["outcomes"]["retry"] = []
        self.library.components["core/testing@1"]["nodes"]["summary"]["transitions"]["retry"] = "scope"
        self.rejected(lambda: self.builder.resolve(self.definition), "unavailable_artifact")

    def test_wrong_binding_contract_is_rejected(self):
        self.definition["nodes"]["documentation"]["inputs"]["testing_result"] = "input:task"
        self.rejected(lambda: self.builder.resolve(self.definition), "contract_mismatch")

    def test_unknown_nodes_ports_outcomes_fields_and_unpinned_refs_are_rejected(self):
        changes = [
            lambda d: d.update({"mystery": 1}),
            lambda d: d["nodes"]["testing"].update({"ref": "core/testing@latest"}),
            lambda d: d["nodes"]["testing"]["transitions"].update({"passed": "missing"}),
            lambda d: d["nodes"]["testing"]["inputs"].update({"task": "input:missing"}),
            lambda d: d["nodes"]["testing"].update({"exec": {}}),
            lambda d: d["nodes"]["testing"]["transitions"].update({"misspelled": "documentation"}),
        ]
        for change in changes:
            with self.subTest(change=change):
                definition = copy.deepcopy(self.definition)
                change(definition)
                self.rejected(lambda: self.builder.resolve(definition))
        self.rejected(lambda: self.builder.resolve(self.definition, overlay={"schema_version": 1, "nodes": {"missing": {"operation": "patch"}}}))

    def test_recursive_library_composition_is_rejected(self):
        self.library.components["core/testing@1"]["nodes"]["scope"]["ref"] = "core/testing@1"
        self.rejected(lambda: self.builder.resolve(self.definition), "component_cycle")

    def test_invalid_config_profile_and_limits_are_rejected(self):
        patches = [
            {"testing.run": {"operation": "patch", "config": {"max_transient_retries": True}}},
            {"testing.run": {"operation": "patch", "config": {"max_transient_retries": 9}}},
            {"testing.run": {"operation": "patch", "config": {"unknown": 1}}},
            {"testing.run": {"operation": "patch", "execution": {"model_profile": "expert"}}},
            {"testing.summary": {"operation": "patch", "execution": {"model_profile": "missing"}}},
            {"testing.summary": {"operation": "patch", "execution": {"model_profile": {"x": "y"}}}},
        ]
        for patch in patches:
            with self.subTest(patch=patch):
                self.rejected(lambda: self.builder.resolve(self.definition, overlay={"schema_version": 1, "nodes": patch}))
        for runtime in [{"max_results": True}, {"node_limits": {"missing": 3}}, {"node_limits": {"testing.scope": 0}}]:
            self.rejected(lambda: self.builder.resolve(self.definition, overlay={"schema_version": 1, "runtime": runtime}))

    def test_snapshot_is_detached_and_digest_changes_with_policy(self):
        resolved = self.builder.resolve(self.definition)
        original = resolved.digest
        snap = resolved.to_dict()
        snap["leaves"]["testing.summary"]["execution"]["model_profile"] = "mutated"
        self.assertEqual(resolved.digest, original)
        self.definition["model_profiles"]["standard"]["model"] = "different"
        self.assertNotEqual(self.builder.resolve(self.definition).digest, original)

    def test_two_instances_have_distinct_namespaces_and_routing(self):
        self.definition["nodes"]["testing_again"] = copy.deepcopy(self.definition["nodes"]["testing"])
        self.definition["nodes"]["testing"]["transitions"]["passed"] = "testing_again"
        resolved = self.builder.resolve(self.definition)
        self.assertEqual(len(resolved.graph.nodes), 8)
        self.assertEqual(resolved.graph.nodes["testing.summary"].transitions["passed"], "testing_again.scope")
        self.assertEqual(resolved.graph.nodes["testing_again.summary"].transitions["passed"], "documentation.impact")

    def test_output_schema_validates_structure_and_boolean_is_not_integer(self):
        resolved = self.builder.resolve(self.definition)
        resolved.validate_outputs("testing.run", "finished", {"execution_record": {"passed": 1, "failed": 0, "evidence_refs": ["real"]}})
        for record in [{"passed": True, "failed": 0, "evidence_refs": ["real"]},
                       {"passed": 1, "failed": 0, "evidence_refs": []},
                       {"passed": 1, "failed": -1, "evidence_refs": ["real"]},
                       {"passed": 1, "failed": 0, "evidence_refs": ["real"], "extra": 0}]:
            self.rejected(lambda: resolved.validate_outputs("testing.run", "finished", {"execution_record": record}), "contract_mismatch")
        self.rejected(lambda: resolved.validate_outputs("testing.run", "finished", {}), "contract_mismatch")

    def test_duplicate_contract_and_unsupported_schema_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "contracts"
            path.mkdir()
            (path / "task.json").write_bytes((LIBRARY / "contracts/task.json").read_bytes())
            self.rejected(lambda: ComponentLibrary([LIBRARY, folder]))
        self.rejected(lambda: check_schema({"type": "string", "pattern": "x"}, "schema"))

    def test_wait_stays_in_same_node_then_resumes_under_runtime_guards(self):
        self.library.components["core/test-scope@1"]["outcomes"]["needs_input"] = []
        self.library.components["core/testing@1"]["nodes"]["scope"]["transitions"]["needs_input"] = "scope"
        resolved = self.builder.resolve(self.definition)
        runtime = AgentGraphRuntime()
        run = runtime.create_run(resolved.graph, {})
        wait = WaitState("scope-question", "testing.scope", "user_input", question="Какие проверки?")
        run = runtime.submit_result(run.run_id, NodeResult("testing.scope", "needs_input", wait=wait), expected_revision=run.revision)
        self.assertEqual(run.state, "waiting_input")
        run = runtime.resume_wait(run.run_id, expected_revision=run.revision, wait_id="scope-question", node_id="testing.scope", answer="unit")
        self.assertEqual(run.current_node, "testing.scope")
        self.library.components["core/testing@1"]["nodes"]["scope"]["transitions"]["needs_input"] = "run"
        self.rejected(lambda: self.builder.resolve(self.definition))

    def test_html_escapes_instruction_and_has_no_network_assets(self):
        self.library.components["core/testing-summary@1"]["execution"]["instruction"] = '</script><script>window.injected=true</script>'
        html = render_workflow(self.builder.resolve(self.definition))
        self.assertNotIn('<script>window.injected=true', html)
        self.assertIn('\\u003c/script\\u003e', html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('https://cdn', html)

    def test_export_cannot_overwrite_source_or_library(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "input.toml"
            destination.write_bytes(DEFINITION.read_bytes())
            before = destination.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["export", str(destination), "--library", str(LIBRARY), "--json", str(destination)])
            self.assertEqual(code, 2)
            self.assertEqual(destination.read_bytes(), before)

    def test_export_rejects_output_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "output.txt"
            path.write_text("Сохранить", encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["export", str(DEFINITION), "--library", str(LIBRARY), "--json", str(path), "--html", str(path)])
            self.assertEqual(code, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "Сохранить")

    def test_schema_metadata_and_reserved_runtime_names_are_rejected(self):
        for schema in [{"type":"string", "minLength":-1}, {"type":"object", "required":["missing"]},
                       {"type":"integer", "minimum":3, "maximum":1}]:
            self.rejected(lambda: check_schema(schema, "schema"))
        self.definition["nodes"]["succeeded"] = self.definition["nodes"].pop("testing")
        self.rejected(lambda: self.builder.resolve(self.definition))


if __name__ == "__main__":
    unittest.main()
