from __future__ import annotations

import unittest

from orchestrator.review import ReviewFinding, code_review


class CodeReviewScenarioTests(unittest.TestCase):
    def test_blocking_finding_returns_to_implementation(self) -> None:
        finding = ReviewFinding(
            code="NULL_DEREFERENCE",
            severity="high",
            file="orchestrator/example.py",
            evidence="value is None on the empty-input branch",
            impact="The public command crashes.",
            remediation="Handle the empty-input branch before dereference.",
            blocking=True,
        )
        result = code_review([finding], isolated_reviewer_available=True)
        self.assertEqual(result.verdict, "rework")
        self.assertEqual(result.findings[0].file, "orchestrator/example.py")

    def test_unavailable_isolation_has_explicit_fallback(self) -> None:
        result = code_review([], isolated_reviewer_available=False)
        self.assertEqual(result.verdict, "approved")
        self.assertEqual(result.reviewer_mode, "same-agent-clean-context")

    def test_correct_diff_does_not_generate_false_positive(self) -> None:
        self.assertEqual(code_review([], isolated_reviewer_available=True).findings, ())

    def test_incomplete_finding_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ReviewFinding("BAD", "high", "a.py", "", "impact", "fix", True)
