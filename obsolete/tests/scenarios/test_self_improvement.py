from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.audit import AuditFinding
from orchestrator.improvement import ImprovementError, design_improvement, may_apply_improvement


FINDING = AuditFinding(
    code="MISSING_TEST",
    severity="medium",
    message="A test is missing.",
    evidence=("docs/spec.md:10",),
    proposal="Add a regression test.",
    fingerprint="f" * 64,
)


class SelfImprovementScenarioTests(unittest.TestCase):
    def test_proposal_does_not_change_repository_and_binds_exact_diff_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "core.py"
            target.write_text("VALUE = 1\n", encoding="utf-8")
            before = target.read_bytes()
            proposal = design_improvement(
                FINDING,
                baseline_revision=3,
                proposed_diff="- VALUE = 1\n+ VALUE = 2\n",
                rollback_instructions="Revert VALUE to 1.",
                regression_test="python -m unittest tests.test_core",
            )
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse(
                may_apply_improvement(
                    proposal,
                    registered_task=True,
                    approved_diff_hash="wrong",
                    approved_revision=3,
                )
            )
            self.assertTrue(
                may_apply_improvement(
                    proposal,
                    registered_task=True,
                    approved_diff_hash=proposal.proposed_diff_hash,
                    approved_revision=3,
                )
            )

    def test_direct_self_write_and_incomplete_proposal_fail_closed(self) -> None:
        proposal = design_improvement(
            FINDING,
            baseline_revision=1,
            proposed_diff="+ test\n",
            rollback_instructions="Revert commit.",
            regression_test="python -m unittest tests.test_regression",
        )
        self.assertFalse(
            may_apply_improvement(
                proposal,
                registered_task=False,
                approved_diff_hash=proposal.proposed_diff_hash,
                approved_revision=1,
            )
        )
        with self.assertRaises(ImprovementError):
            design_improvement(
                FINDING,
                baseline_revision=1,
                proposed_diff="+ test\n",
                rollback_instructions="",
                regression_test="",
            )
