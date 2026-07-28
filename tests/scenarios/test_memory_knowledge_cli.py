from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator import context_cli, knowledge_cli, memory_cli


ROOT = Path(__file__).resolve().parents[2]


class MemoryKnowledgeCliTests(unittest.TestCase):
    def test_domain_cli_modules_are_directly_routed(self) -> None:
        for module in (memory_cli, knowledge_cli, context_cli):
            self.assertTrue(callable(module.configure))
            self.assertTrue(callable(module.run))

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "orchestrator", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )

    def test_context_empty_store_and_invalid_source_are_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self._run(
                "context", "--root", temporary, "--term", "health", "--budget-chars", "256"
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["result"]["memory"], [])
            invalid = self._run(
                "memory",
                "--root",
                temporary,
                "propose",
                "--kind",
                "lesson",
                "--content",
                "Test",
                "--source",
                "missing.md",
                "--confidence",
                "1",
            )
            self.assertEqual(invalid.returncode, 2)
            error = json.loads(invalid.stdout)
            self.assertFalse(error["ok"])
            self.assertNotIn("Traceback", invalid.stderr + invalid.stdout)
            malformed = self._run("context", "--budget-chars", "not-an-integer")
            self.assertEqual(malformed.returncode, 2)
            self.assertEqual(json.loads(malformed.stdout)["error"]["code"], "INVALID_ARGUMENTS")
            self.assertEqual(malformed.stderr, "")

    def test_authoritative_memory_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical", encoding="utf-8")
            proposed = self._run(
                "memory",
                "--root",
                temporary,
                "propose",
                "--kind",
                "decision",
                "--content",
                "Use JSON.",
                "--source",
                str(source),
                "--confidence",
                "1",
            )
            proposal = json.loads(proposed.stdout)["result"]
            promoted = self._run(
                "memory",
                "--root",
                temporary,
                "promote",
                "--proposal-hash",
                proposal["proposal_hash"],
            )
            self.assertEqual(promoted.returncode, 0, promoted.stdout)
            listed = self._run("memory", "--root", temporary, "list")
            self.assertEqual(len(json.loads(listed.stdout)["result"]["entries"]), 1)


if __name__ == "__main__":
    unittest.main()
