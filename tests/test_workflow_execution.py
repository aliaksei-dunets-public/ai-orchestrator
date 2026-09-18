import copy
import io
import json
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from orchestrator.model_process_adapter import process_model_adapter
from orchestrator.workflow_builder import ComponentLibrary, WorkflowBuilder, read_toml
from orchestrator.workflow_execution import ExecutorRegistry, ModelAdapter, WorkflowExecutor, WorkflowExecutionError

LIBRARY = Path(__file__).resolve().parents[1] / "workflow-library"


def workflow(overlay=None):
    definition = read_toml(LIBRARY / "workflows/testing-and-documentation.toml")
    definition["model_profiles"] = {"standard": {"provider": "fixture", "model": "fixture-standard"},
                                    "expert": {"provider": "fixture", "model": "fixture-expert"}}
    return WorkflowBuilder(ComponentLibrary(LIBRARY)).resolve(definition, overlay=overlay)


def inputs():
    return {"task": {"objective": "Проверить пример"},
            "project_profile": {"test_capability": "local-unittest", "documentation_targets": ["docs/result.md"]}}


def fixture_response(request):
    name = request["node_id"].rsplit(".", 1)[-1]
    incoming = request["inputs"]
    if name == "scope":
        assert incoming["task"]["objective"]
        result = {"outcome": "success", "outputs": {"scope": {"checks": ["arithmetic"]}}}
    elif name == "summary":
        record = incoming["execution_record"]
        status = "failed" if record["failed"] else "passed"
        result = {"outcome": status, "outputs": {"result": {
            "status": status, "summary": "Фактический результат unittest", "evidence_refs": record["evidence_refs"]}}}
    elif name == "impact":
        assert incoming["testing_result"]["status"] == "passed"
        result = {"outcome": "assessed", "outputs": {"impact": {"impacted": False, "targets": []}}}
    elif name == "update":
        assert incoming["impact"]["impacted"] is False
        result = {"outcome": "no_change", "outputs": {"result": {
            "status": "no_change", "summary": "Изменения документации не нужны",
            "evidence_refs": incoming["testing_result"]["evidence_refs"]}}}
    else:
        raise AssertionError(name)
    receipt = request["selected_executor"]
    return {"provider": receipt["provider"], "model": receipt["model"], "result": result}


def registry(root, *, fail=False, invoke=fixture_response, available=lambda p: True):
    result = ExecutorRegistry()
    result.register_model(ModelAdapter("fixture-transport", "fixture", available, invoke))
    def test_tool(request):
        assert request["inputs"]["scope"]["checks"] == ["arithmetic"]
        class Arithmetic(unittest.TestCase):
            def runTest(self):
                self.assertEqual(2 + 2, 5 if fail else 4)
        stream = io.StringIO()
        outcome = unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([Arithmetic()]))
        path = root / "unittest-evidence.txt"
        path.write_text(stream.getvalue(), encoding="utf-8")
        failed = len(outcome.failures) + len(outcome.errors)
        return {"outcome": "failure" if failed else "finished", "outputs": {"execution_record": {
            "passed": outcome.testsRun - failed, "failed": failed, "evidence_refs": [str(path)]}}}
    result.register_capability("project-test-runner", test_tool, executor_ref="stdlib-unittest")
    return result


def finish(executor):
    for _ in range(10):
        state = executor.inspect()
        if state["run"]["state"] in {"succeeded", "failed"}:
            return state
        executor.step(expected_revision=state["run"]["revision"])
    raise AssertionError("Unbounded workflow")


class WorkflowExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, resolved=None, **options):
        return WorkflowExecutor(self.root, resolved or workflow(), registry(self.root), **options)

    @staticmethod
    def finish(executor):
        return finish(executor)

    def test_real_unittest_transfers_nested_exports_and_publishes_receipts(self):
        executor = self.make()
        executor.start(inputs())
        state = self.finish(executor)
        self.assertEqual(state["result"]["outputs"]["testing_result"]["status"], "passed")
        self.assertEqual(state["result"]["outputs"]["documentation_result"]["status"], "no_change")
        self.assertEqual(len(state["evidence"]), 5)
        evidence = [json.loads(executor.repository.get(r["ref"], r["role"], r["version"]).content)
                    for r in state["evidence"]]
        self.assertEqual(evidence[1]["receipt"]["executor_ref"], "stdlib-unittest")
        self.assertEqual(evidence[2]["receipt"]["model"], "fixture-standard")
        self.assertEqual(evidence[3]["input_artifacts"]["testing_result"]["value"]["status"], "passed")
        self.assertIn("OK", (self.root / "unittest-evidence.txt").read_text())

    def test_failed_tests_skip_documentation(self):
        executor = WorkflowExecutor(self.root, workflow(), registry(self.root, fail=True))
        executor.start(inputs())
        state = self.finish(executor)
        self.assertEqual(state["run"]["state"], "failed")
        self.assertEqual(list(state["result"]["outputs"]), ["testing_result"])
        self.assertEqual(len(state["evidence"]), 3)

    def test_exact_model_dispatch_and_explicit_unavailable_fallback(self):
        resolved = workflow({"schema_version": 1, "nodes": {"testing.scope": {
            "operation": "patch", "execution": {"model_profile": "expert"}}}})
        calls = []
        def invoke(request):
            calls.append(request["selected_executor"])
            return fixture_response(request)
        registered = registry(self.root, available=lambda p: p["model"] == "fixture-standard", invoke=invoke)
        blocked = WorkflowExecutor(self.root, resolved, registered)
        initial = blocked.start(inputs())
        with self.assertRaises(WorkflowExecutionError) as caught:
            blocked.step(expected_revision=initial["run"]["revision"])
        self.assertEqual(caught.exception.code, "model_unavailable")
        self.assertEqual(blocked.inspect(), initial)
        self.assertEqual(calls, [])
        executor = WorkflowExecutor(self.root, resolved, registered, fallbacks={"expert": ["standard"]})
        state = executor.start(inputs())
        executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(calls[0]["requested_profile"], "expert")
        self.assertEqual(calls[0]["executed_profile"], "standard")
        self.assertEqual(calls[0]["fallback_reason"], "requested_model_unavailable")
        self.assertEqual(calls[0]["policy"], "single_agent")

    def test_different_identity_is_rejected_and_requires_reconciliation(self):
        calls = []
        def wrong(request):
            calls.append(request)
            response = fixture_response(request)
            response["model"] = "other-model"
            return response
        executor = WorkflowExecutor(self.root, workflow(), registry(self.root, invoke=wrong))
        state = executor.start(inputs())
        with self.assertRaises(WorkflowExecutionError) as caught:
            executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(caught.exception.code, "executor_mismatch")
        with self.assertRaises(WorkflowExecutionError) as caught:
            executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(caught.exception.code, "unknown_effect")
        response = fixture_response(calls[0])
        executor.recover_result(response, expected_revision=state["run"]["revision"], resolution_ref="host-log/1")
        self.assertEqual(len(calls), 1)
        self.assertIsNone(executor.inspect()["pending_effect"])

    def test_invalid_outputs_and_timeout_do_not_repeat_effects(self):
        for name in ("invalid", "exception"):
            with self.subTest(name=name):
                calls = []
                def invoke(request):
                    calls.append(request)
                    if name == "exception":
                        raise TimeoutError("Fixture")
                    response = fixture_response(request)
                    response["result"]["outputs"]["scope"]["checks"] = []
                    return response
                executor = WorkflowExecutor(self.root, workflow(), registry(self.root, invoke=invoke))
                state = executor.start(inputs())
                with self.assertRaises(ValueError):
                    executor.step(expected_revision=state["run"]["revision"])
                with self.assertRaises(WorkflowExecutionError):
                    executor.step(expected_revision=state["run"]["revision"])
                self.assertEqual(len(calls), 1)
                self.assertEqual(executor.inspect()["run"], state["run"])

    def test_missing_capability_stale_revision_budget_and_detached_snapshots(self):
        resolved = workflow({"schema_version": 1, "runtime": {"max_results": 1}})
        executor = self.make(resolved)
        state = executor.start(inputs())
        state["workflow_digest"] = "mutated"
        executor.step(expected_revision=state["run"]["revision"])
        with self.assertRaises(WorkflowExecutionError):
            executor.step(expected_revision=state["run"]["revision"])
        actual = executor.inspect()
        with self.assertRaises(WorkflowExecutionError):
            executor.step(expected_revision=actual["run"]["revision"])
        self.assertEqual(len(actual["evidence"]), 1)
        self.assertEqual(executor.workflow.digest, resolved.digest)
        empty = ExecutorRegistry()
        empty.register_model(ModelAdapter("fixture", "fixture", lambda p: True, fixture_response))
        executor = WorkflowExecutor(self.root, workflow(), empty)
        executor.start(inputs())
        executor.step(expected_revision=executor.inspect()["run"]["revision"])
        with self.assertRaises(WorkflowExecutionError) as caught:
            executor.step(expected_revision=executor.inspect()["run"]["revision"])
        self.assertEqual(caught.exception.code, "capability_unavailable")
        self.assertIsNone(executor.inspect()["pending_effect"])

    def test_inputs_and_artifact_integrity_checked_before_host_effect(self):
        executor = self.make()
        bad = inputs()
        bad["task"]["unexpected"] = True
        with self.assertRaises(ValueError):
            executor.start(bad)
        executor.start(inputs())
        artifact = executor.request()["input_artifacts"]["task"]
        path = self.root / artifact["record"]["path"]
        path.write_text('{"inputs": {}}')
        with self.assertRaises(Exception):
            executor.step(expected_revision=executor.inspect()["run"]["revision"])
        self.assertIsNone(executor.inspect()["pending_effect"])

    def test_guard_runs_before_and_after_call(self):
        stale = [False]
        calls = []
        def guard():
            if stale[0]:
                raise ValueError("Stale owner")
        def invoke(request):
            calls.append(request)
            stale[0] = True
            return fixture_response(request)
        executor = WorkflowExecutor(self.root, workflow(), registry(self.root, invoke=invoke), guard=guard)
        state = executor.start(inputs())
        with self.assertRaises(ValueError):
            executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(executor.inspect()["run"], state["run"])
        self.assertIsNotNone(executor.inspect()["pending_effect"])
        self.assertEqual(len(calls), 1)

    def test_real_subprocess_probe_and_model_request(self):
        path = self.root / "fixture-model-host.py"
        path.write_text('''import json,sys
p=json.load(sys.stdin)
if p["operation"]=="probe":
 q=p["profile"]; r={"available": q["model"]=="fixture-standard", "provider":q["provider"],"model":q["model"]}
else:
 q=p["request"]["selected_executor"]; r={"provider":q["provider"],"model":q["model"],"result":{"outcome":"success","outputs":{"scope":{"checks":["arithmetic"]}}}}
print(json.dumps(r))
''', encoding="utf-8")
        adapter = process_model_adapter(executor_ref="fixture-process", provider="fixture", argv=[sys.executable, str(path)])
        registered = ExecutorRegistry()
        registered.register_model(adapter)
        executor = WorkflowExecutor(self.root, workflow(), registered)
        state = executor.start(inputs())
        accepted = executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(accepted["run"]["current_node"], "testing.run")
        self.assertEqual(accepted["run"]["last_result"]["data"]["receipt"]["executor_ref"], "fixture-process")

    def test_invalid_fallback_and_duplicate_adapters_rejected(self):
        with self.assertRaises(WorkflowExecutionError):
            self.make(fallbacks={"standard": ["missing"]})
        registered = registry(self.root)
        with self.assertRaises(WorkflowExecutionError):
            registered.register_model(ModelAdapter("other", "fixture", lambda p: True, fixture_response))

    def test_publication_then_runtime_failure_recovers_without_effect_replay(self):
        calls = []
        def invoke(request):
            calls.append(request)
            return fixture_response(request)
        executor = WorkflowExecutor(self.root, workflow(), registry(self.root, invoke=invoke))
        state = executor.start(inputs())
        with patch.object(executor.runtime, "submit_result", side_effect=OSError("Fixture publication window")):
            with self.assertRaises(OSError):
                executor.step(expected_revision=state["run"]["revision"])
        self.assertIsNotNone(executor.inspect()["pending_effect"])
        accepted = executor.recover_result(fixture_response(calls[0]), expected_revision=state["run"]["revision"],
                                          resolution_ref="verified-host-response")
        self.assertEqual(accepted["run"]["current_node"], "testing.run")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(accepted["evidence"]), 1)

    def test_wait_identity_resume_and_per_node_budget_are_explicit(self):
        library = ComponentLibrary(LIBRARY)
        component = library.components["core/test-scope@1"]
        component["outcomes"]["needs_input"] = []
        definition = read_toml(LIBRARY / "workflows/testing-and-documentation.toml")
        definition["model_profiles"] = {"standard": {"provider": "fixture", "model": "fixture-standard"}}
        # Превращаем пример в один атомарный узел с ограниченным повтором.
        definition["component"]["entry"] = "scope"
        definition["nodes"] = {"scope": {"ref": "core/test-scope@1",
            "inputs": {p: "input:" + p for p in component["inputs"]},
            "transitions": {"success": "exit:success", "needs_input": "scope"}}}
        definition["outputs"] = {"scope": "test-scope/v1"}
        definition["outcomes"] = {"success": ["scope"]}
        definition["terminal_states"] = {"success": "succeeded"}
        definition["exits"] = {"success": {"scope": "scope.scope"}}
        definition["runtime"] = {"max_results": 3, "node_limits": {"scope": 2}}
        resolved = WorkflowBuilder(library).resolve(definition)
        calls = []
        def invoke(request):
            calls.append(request)
            receipt = request["selected_executor"]
            result = ({"outcome": "needs_input", "outputs": {}, "wait": {"question": "Выберите checks"}}
                      if request["resumed_wait"] is None else {"outcome": "success", "outputs": {
                          "scope": {"checks": [request["resumed_wait"]["answer"]]}}})
            return {"provider": receipt["provider"], "model": receipt["model"], "result": result}
        registered = ExecutorRegistry()
        registered.register_model(ModelAdapter("fixture-wait", "fixture", lambda p: True, invoke))
        executor = WorkflowExecutor(self.root, resolved, registered)
        state = executor.start(inputs())
        state = executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(state["run"]["state"], "waiting_input")
        with self.assertRaises(Exception):
            executor.resume_wait(expected_revision=state["run"]["revision"], wait_id="wrong", answer="arithmetic")
        state = executor.resume_wait(expected_revision=state["run"]["revision"],
            wait_id=state["run"]["wait"]["wait_id"], answer="arithmetic")
        state = executor.step(expected_revision=state["run"]["revision"])
        self.assertEqual(state["result"]["outputs"]["scope"]["checks"], ["arithmetic"])
        self.assertEqual(len(calls), 2)

    def test_local_demo_subprocess_utf8_docs_and_failed_route(self):
        for fail in (False, True):
            with self.subTest(fail=fail):
                target = self.root / ("failed" if fail else "passed")
                argv = [sys.executable, str(LIBRARY / "examples/run-local-workflow.py"), "--project", str(target)]
                if fail:
                    argv.append("--fail-test")
                result = subprocess.run(argv, capture_output=True, check=False, timeout=15)
                self.assertEqual(result.returncode, 1 if fail else 0, result.stderr.decode("utf-8", errors="replace"))
                value = json.loads(result.stdout)
                self.assertEqual(value["evidence_count"], 3 if fail else 5)
                self.assertEqual((target / "docs/demo.md").exists(), not fail)
                state = json.loads((target / "workflow-result.json").read_text(encoding="utf-8"))
                self.assertEqual(state["result"]["outputs"]["testing_result"]["status"], "failed" if fail else "passed")


if __name__ == "__main__":
    unittest.main()
