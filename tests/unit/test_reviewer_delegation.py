from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.review import ReviewFinding, code_review
from orchestrator.reviewer import (
    IndependentReviewerAdapter,
    IndependentReviewerResult,
    ReviewerRequest,
    admit_independent_reviewer,
    dispatch_independent_reviewer,
)
from orchestrator.telemetry import JsonlTelemetrySink, TokenUsage, load_events


class FakeReviewer:
    def __init__(self, result: IndependentReviewerResult) -> None:
        self.result = result
        self.requests: list[ReviewerRequest] = []

    def review(self, request: ReviewerRequest) -> IndependentReviewerResult:
        self.requests.append(request)
        return self.result


class ReviewerDelegationTests(unittest.TestCase):
    def _request(self, **overrides: object) -> ReviewerRequest:
        values: dict[str, object] = {
            "task_id": "TASK-0009",
            "task_mode": "standard",
            "risk": "high",
            "acceptance_criteria": ("One reviewer maximum",),
            "context_pack": "Only bounded task context.",
            "changed_paths": ("orchestrator/review.py",),
            "diff_summary": "Adds a read-only adapter seam.",
            "test_evidence": ("focused tests pass",),
        }
        values.update(overrides)
        return ReviewerRequest(**values)

    def test_admission_is_bounded_and_qualifying(self) -> None:
        self.assertTrue(admit_independent_reviewer(task_mode="deep", risk="low").admitted)
        self.assertTrue(admit_independent_reviewer(task_mode="quick", risk="low", security_sensitive=True).admitted)
        self.assertTrue(admit_independent_reviewer(task_mode="standard", risk="low", boundaries=("migration",)).admitted)
        self.assertFalse(admit_independent_reviewer(task_mode="standard", risk="medium").admitted)
        self.assertFalse(admit_independent_reviewer(task_mode="standard", risk="high", dispatch_count=1).admitted)

    def test_request_is_read_only_and_rejects_unbounded_or_secret_input(self) -> None:
        request = self._request()
        self.assertTrue(request.read_only)
        self.assertEqual(request.write_authority, "none")
        with self.assertRaises(ValueError):
            self._request(read_only=False)
        with self.assertRaises(ValueError):
            self._request(diff_summary="token" + "=super-secret-value")
        with self.assertRaises(ValueError):
            self._request(changed_paths=("C:/outside.py",))

    def test_native_result_is_normalized_and_telemetry_is_payload_free(self) -> None:
        finding = ReviewFinding(
            "REVIEW_NOTE",
            "medium",
            "orchestrator/review.py",
            "The adapter found a concrete issue.",
            "The issue could affect review correctness.",
            "Add a regression test.",
        )
        adapter = FakeReviewer(
            IndependentReviewerResult(
                findings=(finding,),
                evidence=("bounded evidence",),
                usage=TokenUsage(subagent_input_tokens=20, subagent_output_tokens=12),
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            telemetry = JsonlTelemetrySink(Path(temporary) / "events.jsonl")
            outcome = dispatch_independent_reviewer(
                self._request(),
                capability_mode="native",
                capability_adapter="sub-agent",
                adapter=adapter,
                telemetry_sink=telemetry,
                run_id="TASK-0009-review",
            )
            self.assertEqual(outcome.mode, "native")
            self.assertEqual(outcome.handoffs, 1)
            self.assertEqual(outcome.result.findings, (finding,))
            self.assertEqual(adapter.requests[0].write_authority, "none")
            raw = (Path(temporary) / "events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("bounded evidence", raw)
            self.assertNotIn("orchestrator/review.py", raw)
            event = load_events(Path(temporary) / "events.jsonl")[0]
            self.assertEqual(event["metrics"]["agent_handoffs"], 1)
            self.assertEqual(event["metrics"]["usage"]["subagent_input_tokens"], 20)

    def test_fallback_is_explicit_and_code_review_keeps_compatibility(self) -> None:
        outcome = dispatch_independent_reviewer(
            self._request(),
            capability_mode="fallback",
            capability_adapter="clean-context-review",
            adapter=None,
        )
        self.assertEqual(outcome.mode, "same-agent-clean-context")
        self.assertTrue(outcome.fallback_reason)
        result = code_review(
            [],
            isolated_reviewer_available=False,
            reviewer_request=self._request(),
            reviewer_capability_mode="fallback",
            reviewer_capability_adapter="clean-context-review",
        )
        self.assertEqual(result.verdict, "approved")
        self.assertEqual(result.reviewer_mode, "same-agent-clean-context")
        self.assertTrue(result.reviewer_reason)

    def test_non_qualifying_review_does_not_dispatch(self) -> None:
        adapter = FakeReviewer(IndependentReviewerResult())
        outcome = dispatch_independent_reviewer(
            self._request(task_mode="standard", risk="medium"),
            capability_mode="native",
            capability_adapter="sub-agent",
            adapter=adapter,
        )
        self.assertEqual(outcome.mode, "not-admitted")
        self.assertEqual(adapter.requests, [])


if __name__ == "__main__":
    unittest.main()
