from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TaskCliTests(unittest.TestCase):
    def test_resources_are_available_without_creating_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "resources"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)["result"]
            self.assertEqual(set(paths), {"contract", "usage", "example_skill"})
            self.assertTrue(all(Path(path).is_file() for path in paths.values()))
            self.assertFalse((Path(directory) / ".orchestrator").exists())

    def test_create_and_list_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "cp1252"
            create = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "create",
                 "--title", "Задача", "--objective", "Проверить", "--request", "Сделай проверку",
                 "--criterion", "Проверка прошла"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            self.assertEqual(json.loads(create.stdout)["result"]["id"], "TASK-0001")
            listing = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "list", "--status", "created"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertEqual(len(json.loads(listing.stdout)["result"]), 1)
            validation = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "validate"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stderr)
            self.assertEqual(json.loads(validation.stdout), {"ok": True, "result": []})


if __name__ == "__main__":
    unittest.main()
