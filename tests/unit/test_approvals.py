from __future__ import annotations

import unittest

from orchestrator.approvals import (
    ApprovalError,
    ApprovalRequest,
    evidence_is_current,
    resolve_approval,
)


def request(*, safe_default: str = "reject") -> ApprovalRequest:
    return ApprovalRequest(
        id="approve-scope",
        question="Approve adding a new public command?",
        consequences=("The public CLI surface expands.", "Documentation and compatibility checks become required."),
        safe_default=safe_default,
        baseline_revision=2,
        baseline_hash="abc123",
        timeout_seconds=60,
    )


class ApprovalTests(unittest.TestCase):
    def test_approve_reject_and_wait(self) -> None:
        approved = resolve_approval(
            request(), answer="approve", current_revision=2, current_baseline_hash="abc123"
        )
        rejected = resolve_approval(
            request(), answer="reject", current_revision=2, current_baseline_hash="abc123"
        )
        waiting = resolve_approval(
            request(safe_default="wait"),
            answer=None,
            current_revision=2,
            current_baseline_hash="abc123",
        )
        self.assertEqual((approved.decision, rejected.decision, waiting.decision), ("approved", "rejected", "waiting"))

    def test_stale_revision_or_hash_invalidates_approval(self) -> None:
        with self.assertRaisesRegex(ApprovalError, "stale"):
            resolve_approval(
                request(), answer="approve", current_revision=3, current_baseline_hash="abc123"
            )
        evidence = resolve_approval(
            request(), answer="approve", current_revision=2, current_baseline_hash="abc123"
        )
        self.assertFalse(evidence_is_current(evidence, revision=3, baseline_hash="changed"))

    def test_timeout_uses_safe_default(self) -> None:
        rejected = resolve_approval(
            request(), answer=None, current_revision=2, current_baseline_hash="abc123", timed_out=True
        )
        waiting = resolve_approval(
            request(safe_default="wait"),
            answer=None,
            current_revision=2,
            current_baseline_hash="abc123",
            timed_out=True,
        )
        self.assertEqual(rejected.decision, "rejected")
        self.assertEqual(waiting.decision, "waiting")

    def test_question_consequences_and_default_are_mandatory(self) -> None:
        with self.assertRaises(ApprovalError):
            ApprovalRequest("x", "", (), "reject", 1, "hash")
