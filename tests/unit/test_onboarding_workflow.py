from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.onboarding_workflow import (
    Choice,
    OnboardingError,
    Question,
    plan_onboarding,
    resolve_core_root,
)


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/system/project-onboarding/SKILL.md"


class OnboardingWorkflowUnitTests(unittest.TestCase):
    def test_core_root_is_resolved_from_canonical_skill(self) -> None:
        self.assertEqual(resolve_core_root(SKILL), ROOT)

    def test_question_requires_unique_choices_and_one_recommendation(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate"):
            Question(
                "mode",
                "Choose",
                (
                    Choice("same", "One", "First", True),
                    Choice("same", "Two", "Second", False),
                ),
            )
        with self.assertRaisesRegex(ValueError, "recommended"):
            Question(
                "mode",
                "Choose",
                (
                    Choice("one", "One", "First", True),
                    Choice("two", "Two", "Second", True),
                ),
            )

    def test_credential_like_answers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            with self.assertRaisesRegex(OnboardingError, "credential"):
                plan_onboarding(
                    SKILL,
                    target,
                    {"platform_profile": "codex", "api_token": "secret"},
                )

    def test_nested_credential_like_answer_is_not_echoed(self) -> None:
        credential = "ghp_12345678901234567890"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            with self.assertRaises(OnboardingError) as captured:
                plan_onboarding(
                    SKILL,
                    target,
                    {"technology_profiles": [credential]},
                )
            self.assertIn("credential", str(captured.exception))
            self.assertNotIn(credential, str(captured.exception))

    def test_plan_hash_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            (target / "pyproject.toml").write_text(
                "[project]\nname='sample'\n",
                encoding="utf-8",
            )
            (target / "src").mkdir()
            (target / "src/app.py").write_text("VALUE = 1\n", encoding="utf-8")
            answers = {
                "platform_profile": "codex",
                "external_core_path": "confirm",
            }
            first = plan_onboarding(SKILL, target, answers)
            second = plan_onboarding(SKILL, target, answers)
            self.assertEqual(first.status, "preview_ready")
            self.assertEqual(first.plan_hash, second.plan_hash)
            self.assertEqual(first.target_fingerprint, second.target_fingerprint)
