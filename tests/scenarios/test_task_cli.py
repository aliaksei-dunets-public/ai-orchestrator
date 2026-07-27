from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.unit.test_task_manager import DRAFT


ROOT = Path(__file__).resolve().parents[2]


class TaskCliScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.tasks = Path(self.temporary.name) / ".orchestrator" / "tasks"
        (self.tasks / "drafts").mkdir(parents=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "orchestrator.task_cli", "--tasks-root", str(self.tasks), *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def draft(self, name: str, title: str) -> Path:
        path = self.tasks / "drafts" / name
        path.write_text(DRAFT.replace("Test task", title), encoding="utf-8")
        return path

    def test_full_small_lifecycle_and_json_contract(self) -> None:
        draft = self.draft("small.md", "Small task")
        registered = self.run_cli("register", "--context", str(draft))
        self.assertEqual(registered.returncode, 0, registered.stderr)
        self.assertTrue(json.loads(registered.stdout)["ok"])
        claimed = self.run_cli("claim-next", "--json")
        payload = json.loads(claimed.stdout)
        self.assertEqual(payload["task"]["status"], "in_progress")
        completed = self.run_cli("complete", "TASK-0001")
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["task"]["status"], "done")
        validated = self.run_cli("validate", "--json")
        self.assertEqual(validated.returncode, 0, validated.stdout)

    def test_empty_backlog_uses_exit_code_six(self) -> None:
        result = self.run_cli("claim-next", "--json")
        self.assertEqual(result.returncode, 6)
        self.assertEqual(json.loads(result.stdout)["error"]["code"], "NO_AVAILABLE_TASKS")

    def test_single_writer_claim_and_gitignore(self) -> None:
        self.run_cli("register", "--context", str(self.draft("one.md", "One")))
        self.run_cli("register", "--context", str(self.draft("two.md", "Two")))
        self.assertEqual(self.run_cli("claim-next", "--json").returncode, 0)
        self.assertEqual(self.run_cli("claim-next", "--json").returncode, 5)
        for relative in (
            ".orchestrator/tasks/tasks.json",
            ".orchestrator/tasks/probe.tmp",
            ".orchestrator/tasks/probe.lock",
        ):
            result = subprocess.run(
                ["git", "check-ignore", relative],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, relative)
