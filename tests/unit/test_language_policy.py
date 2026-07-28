from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.language_policy import (
    LanguagePolicyError,
    classify_path,
    inventory_repository,
    load_policy,
)


ROOT = Path(__file__).resolve().parents[2]


class LanguagePolicyTests(unittest.TestCase):
    def test_english_canonical_document_is_graph_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "docs" / "guides" / "guide.md"
            path.parent.mkdir(parents=True)
            path.write_text("# English Guide\n\nUse the CLI.\n", encoding="utf-8")

            decision = classify_path(root, path, policy=load_policy(ROOT))

        self.assertEqual(decision.language, "en")
        self.assertEqual(decision.document_class, "user_canonical")
        self.assertTrue(decision.canonical)
        self.assertTrue(decision.graph_eligible)
        self.assertFalse(decision.excluded)

    def test_russian_companion_is_not_graph_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "docs" / "guides" / "guide.ru.md"
            path.parent.mkdir(parents=True)
            path.write_text("# \u0420\u0443\u0441\u0441\u043a\u043e\u0435 \u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0441\u0442\u0432\u043e\n", encoding="utf-8")

            decision = classify_path(root, path, policy=load_policy(ROOT))

        self.assertEqual(decision.language, "ru")
        self.assertEqual(decision.document_class, "user_companion")
        self.assertFalse(decision.canonical)
        self.assertFalse(decision.graph_eligible)

    def test_mixed_language_document_is_rejected_for_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "notes.md"
            path.write_text("# English title\n\n\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0430\u0431\u0437\u0430\u0446.\n", encoding="utf-8")

            decision = classify_path(root, path, policy=load_policy(ROOT))

        self.assertEqual(decision.language, "mixed")
        self.assertFalse(decision.graph_eligible)
        self.assertIn("mixed", decision.reason)

    def test_excluded_path_cannot_be_a_graph_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "releases" / "1.0" / "README.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Release\n", encoding="utf-8")

            decision = classify_path(root, path, policy=load_policy(ROOT))

        self.assertTrue(decision.excluded)
        self.assertFalse(decision.graph_eligible)

    def test_generated_projection_is_not_a_canonical_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / ".codex" / "skills" / "example" / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text("# Skill\n\nEnglish instructions.\n", encoding="utf-8")

            decision = classify_path(root, path, policy=load_policy(ROOT))

        self.assertEqual(decision.document_class, "generated")
        self.assertFalse(decision.canonical)
        self.assertFalse(decision.graph_eligible)

    def test_inventory_is_deterministic_and_reports_unclassified_cyrillic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("# English\n", encoding="utf-8")
            (root / "docs" / "guides").mkdir(parents=True)
            (root / "docs" / "guides" / "guide.ru.md").write_text("# \u0420\u0443\u0441\u0441\u043a\u0438\u0439\n", encoding="utf-8")
            (root / "unclassified.md").write_text("\u0420\u0443\u0441\u0441\u043a\u0438\u0439 \u0442\u0435\u043a\u0441\u0442\n", encoding="utf-8")
            policy = load_policy(ROOT)

            first = inventory_repository(root, policy=policy)
            second = inventory_repository(root, policy=policy)

        self.assertEqual(first, second)
        self.assertTrue(any(item.path == "unclassified.md" and item.error for item in first))
        self.assertFalse(any(item.path.endswith("guide.ru.md") and item.error for item in first))

    def test_invalid_source_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(LanguagePolicyError):
                classify_path(Path(temporary), Path(temporary).parent / "outside.md", policy=load_policy(ROOT))
