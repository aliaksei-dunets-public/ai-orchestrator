from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.health import run_health_checks


ROOT = Path(__file__).resolve().parents[2]


class HealthCliScenarioTests(unittest.TestCase):
    def run_cli(self, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "orchestrator", "health", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_json_output_is_valid(self) -> None:
        result = self.run_cli("--root", str(ROOT), "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIsInstance(payload["findings"], list)

    def test_missing_structure_returns_error_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_cli("--root", temporary)
            self.assertEqual(result.returncode, 1)
            self.assertIn("MISSING_REQUIRED_PATH", result.stdout)
            self.assertNotIn("Traceback", result.stderr)

    def test_workspace_inspection_has_stable_json(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "orchestrator",
                "workspace",
                "inspect",
                "TASK-0005",
                "--tasks-root",
                str(ROOT / ".orchestrator/tasks"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertIsNone(payload["result"]["assignment"])

    def test_health_rejects_missing_active_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / ".orchestrator/tasks"
            contexts = tasks / "contexts"
            contexts.mkdir(parents=True)
            (contexts / "TASK-0001.md").write_text("# task\n", encoding="utf-8")
            (tasks / "tasks.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "next_id": 2,
                        "tasks": [
                            {
                                "id": "TASK-0001",
                                "title": "Missing",
                                "status": "in_progress",
                                "context": "contexts/TASK-0001.md",
                                "status_note": None,
                                "created_at": "2026-07-28T00:00:00+00:00",
                                "updated_at": "2026-07-28T00:00:00+00:00",
                                "assignment": {
                                    "mode": "isolated_parallel",
                                    "run_id": "run-1",
                                    "sequence": 2,
                                    "max_workers": 2,
                                    "workspace_kind": "worktree",
                                    "workspace_path": str(root / "missing"),
                                    "branch": "orchestrator/run-1/task-0001",
                                    "base_commit": "a" * 40,
                                    "commit_evidence": None,
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_health_checks(root, scope="tasks")
            self.assertTrue(
                any(item.code == "TASK_WORKSPACE_MISSING" for item in report.findings)
            )
