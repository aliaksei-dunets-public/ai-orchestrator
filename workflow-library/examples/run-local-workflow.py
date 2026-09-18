"""Воспроизводимый workflow: JSON subprocess fixture + настоящий unittest tool."""
import argparse
import io
import json
from pathlib import Path
import sys
import unittest

from orchestrator.model_process_adapter import process_model_adapter
from orchestrator.workflow_builder import ComponentLibrary, WorkflowBuilder, read_toml
from orchestrator.workflow_execution import ExecutorRegistry, WorkflowExecutor

parser = argparse.ArgumentParser()
parser.add_argument("--project", type=Path, required=True, help="Каталог результатов демонстрации")
parser.add_argument("--fail-test", action="store_true")
args = parser.parse_args()
root = args.project.resolve()
root.mkdir(parents=True, exist_ok=True)
library = Path(__file__).resolve().parents[1]
definition = read_toml(library / "workflows/testing-and-documentation.toml")
definition["model_profiles"] = {"standard": {"provider": "local-fixture", "model": "fixture-v1"}}
resolved = WorkflowBuilder(ComponentLibrary(library)).resolve(definition, source="local-fixture-demo")
executors = ExecutorRegistry()
executors.register_model(process_model_adapter(executor_ref="local-fixture-process", provider="local-fixture",
    argv=[sys.executable, str(library / "examples/local-model-host.py"), "--project", str(root)], timeout=10))

def test_tool(request):
    if request["inputs"]["scope"]["checks"] != ["arithmetic"]:
        raise ValueError("Fixture поддерживает только arithmetic")
    class Arithmetic(unittest.TestCase):
        def runTest(self):
            self.assertEqual(2 + 2, 5 if args.fail_test else 4)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream).run(unittest.TestSuite([Arithmetic()]))
    failed = len(result.failures) + len(result.errors)
    log = root / "unittest-result.txt"
    log.write_text(stream.getvalue(), encoding="utf-8")
    return {"outcome": "failure" if failed else "finished", "outputs": {"execution_record": {
        "passed": result.testsRun - failed, "failed": failed, "evidence_refs": [str(log)]}}}

executors.register_capability("project-test-runner", test_tool, executor_ref="stdlib-unittest")
executor = WorkflowExecutor(root, resolved, executors)
state = executor.start({"task": {"objective": "Проверить арифметику и сохранить описание процесса"},
    "project_profile": {"test_capability": "local-unittest", "documentation_targets": ["docs/demo.md"]}})
# Это bounded demo driver. Публичный executor исполняет только один explicit step.
for _ in range(resolved.runtime_options["max_results"]):
    if state["run"]["state"] in {"succeeded", "failed"}:
        break
    state = executor.step(expected_revision=state["run"]["revision"])
(root / "workflow-result.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"state": state["run"]["state"], "workflow_digest": resolved.digest,
    "evidence_count": len(state["evidence"]), "result": state["result"]["outputs"],
    "model_transport": "local fixture; LLM не вызывается"}))
sys.exit(0 if state["run"]["state"] == "succeeded" else 1)
