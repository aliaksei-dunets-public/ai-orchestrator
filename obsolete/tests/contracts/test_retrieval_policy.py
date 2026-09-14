from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RetrievalPolicyContractTests(unittest.TestCase):
    def test_release_artifact_is_excluded_from_default_search(self) -> None:
        ignore = (ROOT / ".rgignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("releases/", ignore)
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("releases/` is excluded", instructions)
        defaults = (ROOT / "config/defaults.yaml").read_text(encoding="utf-8")
        self.assertIn("default_excludes:", defaults)
        self.assertIn("- releases/**", defaults)
        self.assertIn("explicit_release_search: true", defaults)

    def test_telemetry_operational_state_is_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".orchestrator/telemetry/", gitignore)
