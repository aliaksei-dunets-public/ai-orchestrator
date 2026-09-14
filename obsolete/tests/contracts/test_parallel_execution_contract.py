from __future__ import annotations

import json
import unittest
from pathlib import Path

from orchestrator.task_manager import ExecutionSettings, TaskManagerError


ROOT = Path(__file__).resolve().parents[2]


class ParallelExecutionContractTests(unittest.TestCase):
    def test_serial_defaults_and_isolated_requirements(self) -> None:
        serial = ExecutionSettings()
        self.assertEqual(serial.mode, "serial")
        self.assertEqual(serial.max_workers, 1)
        with self.assertRaises(TaskManagerError):
            ExecutionSettings(mode="isolated_parallel")
        isolated = ExecutionSettings(
            mode="isolated_parallel",
            run_id="run-1",
            max_workers=2,
            worktree_root=".orchestrator/worktrees",
        )
        self.assertEqual(isolated.mode, "isolated_parallel")

    def test_registry_schema_accepts_optional_assignment(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/task-registry.schema.json").read_text(
                encoding="utf-8"
            )
        )
        task = schema["properties"]["tasks"]["items"]
        self.assertIn("assignment", task["properties"])
        assignment = task["properties"]["assignment"]
        self.assertEqual(assignment["properties"]["workspace_kind"]["enum"], ["main", "worktree"])

    def test_defaults_define_serial_mode_and_bounded_workers(self) -> None:
        defaults = (ROOT / "config/defaults.yaml").read_text(encoding="utf-8")
        self.assertIn("execution:", defaults)
        self.assertIn("mode: serial", defaults)
        self.assertIn("max_workers: 1", defaults)
