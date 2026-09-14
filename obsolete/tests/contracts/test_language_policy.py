from __future__ import annotations

import json
import unittest
from pathlib import Path

from orchestrator.language_policy import load_policy


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "config" / "language-policy.json"


class LanguagePolicyContractTests(unittest.TestCase):
    def test_policy_is_schema_version_one_and_declares_source_classes(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["default_language"], "en")
        self.assertIn("en", payload["languages"])
        self.assertIn("ru", payload["languages"])
        for name in ("canonical", "user_canonical", "user_companion", "generated", "excluded"):
            self.assertIn(name, payload["document_classes"])
        self.assertEqual(load_policy(ROOT).schema_version, 1)

    def test_graph_policy_allows_only_english_canonical_sources(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["graph_source_languages"], ["en"])
        self.assertTrue(payload["document_classes"]["canonical"]["graph_eligible"])
        self.assertFalse(payload["document_classes"]["user_companion"]["graph_eligible"])
        self.assertFalse(payload["document_classes"]["generated"]["graph_eligible"])

    def test_policy_contains_operational_and_release_exclusions(self) -> None:
        payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

        exclusions = set(payload["excluded_path_prefixes"])
        self.assertIn(".git/", exclusions)
        self.assertIn(".venv/", exclusions)
        self.assertIn("releases/", exclusions)
        self.assertIn(".orchestrator/", exclusions)
