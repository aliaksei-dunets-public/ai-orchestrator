from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.execution import retrieve_execution_context
from orchestrator.task_creation import retrieve_task_creation_context


ROOT = Path(__file__).resolve().parents[2]


class TaskCreationRetrievalTests(unittest.TestCase):
    def test_all_routes_have_bounded_valid_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for mode, budget in (("quick", 2048), ("standard", 6144), ("deep", 12288)):
                creation = retrieve_task_creation_context(
                    root, mode=mode, request="Change health"
                )
                execution = retrieve_execution_context(
                    root, mode=mode, task_context="Change health"
                )
                self.assertEqual(creation["budget_chars"], budget)
                self.assertEqual(execution["budget_chars"], budget)
                self.assertEqual(creation["memory"], [])

    def test_workflows_retrieve_before_analysis_and_implementation(self) -> None:
        creation = (ROOT / "workflows/task-creation-standard.yaml").read_text(encoding="utf-8")
        execution = (ROOT / "workflows/task-execution.yaml").read_text(encoding="utf-8")
        backlog = (ROOT / "workflows/backlog-loop.yaml").read_text(encoding="utf-8")
        self.assertLess(creation.index("id: retrieve-context"), creation.index("id: analyze"))
        self.assertLess(execution.index("- retrieve-context"), execution.index("- implement"))
        self.assertLess(backlog.index("- retrieve-context"), backlog.index("- task-execution"))
        self.assertLess(backlog.index("- task-execution"), backlog.index("- finalize-task"))
        self.assertLess(backlog.index("- finalize-task"), backlog.index("- commit-task"))
        self.assertIn("propose-session-memory-candidates", backlog)


if __name__ == "__main__":
    unittest.main()
