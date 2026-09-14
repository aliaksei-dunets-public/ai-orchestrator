from __future__ import annotations

import unittest
from pathlib import Path

from orchestrator.platforms import load_platform_profile, resolve_capability
from orchestrator.review import ReviewFinding, code_review
from orchestrator.reviewer import IndependentReviewerResult, ReviewerRequest


ROOT = Path(__file__).resolve().parents[2]


class EmptyReviewer:
    def review(self, request: ReviewerRequest) -> IndependentReviewerResult:
        return IndependentReviewerResult()


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

    def test_platform_capability_routes_native_and_fallback_through_one_contract(self) -> None:
        request = ReviewerRequest(
            task_id="TASK-0009",
            task_mode="standard",
            risk="high",
            acceptance_criteria=("review is bounded",),
            context_pack="bounded context",
            changed_paths=("orchestrator/review.py",),
            diff_summary="review seam",
            test_evidence=("tests pass",),
        )
        codex = load_platform_profile(ROOT / "profiles/platforms/codex.yaml")
        claude = load_platform_profile(ROOT / "profiles/platforms/claude-vscode.yaml")
        codex_capability = resolve_capability(codex, "review_isolation")
        claude_capability = resolve_capability(claude, "review_isolation")
        native = code_review(
            [],
            isolated_reviewer_available=True,
            reviewer_request=request,
            reviewer_capability_mode=codex_capability.mode,
            reviewer_capability_adapter=codex_capability.adapter,
            reviewer_adapter=EmptyReviewer(),
        )
        fallback = code_review(
            [],
            isolated_reviewer_available=False,
            reviewer_request=request,
            reviewer_capability_mode=claude_capability.mode,
            reviewer_capability_adapter=claude_capability.adapter,
        )
        self.assertEqual(native.reviewer_mode, "native")
        self.assertEqual(fallback.reviewer_mode, "same-agent-clean-context")
        self.assertTrue(fallback.reviewer_reason)
