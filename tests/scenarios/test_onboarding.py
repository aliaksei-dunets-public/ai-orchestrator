from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.onboarding import collect_facts, onboard


class OnboardingScenarioTests(unittest.TestCase):
    def test_dry_run_full_diff_and_second_run_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "pyproject.toml").write_text("[project]\nname='sample'\n", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src/app.py").write_text("print('ok')\n", encoding="utf-8")
            destination = root / "docs/project-context.md"
            preview = onboard(root, destination, dry_run=True)
            self.assertTrue(preview.changed)
            self.assertIn("+++ ", preview.diff)
            self.assertFalse(destination.exists())
            applied = onboard(root, destination, dry_run=False)
            self.assertTrue(applied.changed)
            second = onboard(root, destination, dry_run=True)
            self.assertFalse(second.changed)
            self.assertEqual(second.diff, "")

    def test_manual_block_is_preserved_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            destination = root / "project-context.md"
            first = onboard(root, destination, dry_run=False)
            manual = "<!-- manual:start -->\nOwner note.\n<!-- manual:end -->"
            destination.write_text(first.content.replace(
                "<!-- manual:start -->\nAdd project-specific notes here.\n<!-- manual:end -->",
                manual,
            ), encoding="utf-8")
            result = onboard(root, destination, dry_run=False)
            self.assertIn(manual, result.content)

    def test_secrets_and_generated_trees_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text("API_KEY=secret", encoding="utf-8")
            (root / "generated").mkdir()
            (root / "generated/huge.py").write_text("secret", encoding="utf-8")
            facts = collect_facts(root)
            serialized = repr(facts)
            self.assertNotIn(".env", serialized)
            self.assertNotIn("generated", serialized)
