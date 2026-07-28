from __future__ import annotations

import unittest
from pathlib import Path

from orchestrator.language_policy import classify_path, load_policy


ROOT = Path(__file__).resolve().parents[2]


class BilingualDocumentationScenarioTests(unittest.TestCase):
    def test_russian_user_guides_are_reader_only_sources(self) -> None:
        policy = load_policy(ROOT)
        for path in sorted((ROOT / "docs/guides").glob("*-ru.md")):
            decision = classify_path(ROOT, path, policy=policy)
            self.assertEqual(decision.language, "ru", path.name)
            self.assertFalse(decision.canonical, path.name)
            self.assertFalse(decision.graph_eligible, path.name)

    def test_english_user_guides_are_canonical_sources(self) -> None:
        policy = load_policy(ROOT)
        for path in sorted((ROOT / "docs/guides").glob("*.md")):
            if path.name.endswith("-ru.md"):
                continue
            decision = classify_path(ROOT, path, policy=policy)
            self.assertEqual(decision.language, "en", path.name)
            self.assertTrue(decision.canonical, path.name)
            self.assertTrue(decision.graph_eligible, path.name)
