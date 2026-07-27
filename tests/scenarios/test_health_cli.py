from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


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
