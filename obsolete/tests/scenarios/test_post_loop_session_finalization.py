from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.backlog import BacklogLimits, BacklogResult, run_backlog
from orchestrator.session_report import finalize_session


class PostLoopSessionFinalizationScenarios(unittest.TestCase):
    def test_empty_loop_runs_session_finalization_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls: list[str] = []

            def finish(result: BacklogResult) -> None:
                calls.append(result.status)
                finalize_session(
                    root,
                    "reports/session.md",
                    {"summary": result.reason},
                )

            result = run_backlog(
                limits=BacklogLimits(1, 10, 10),
                claim_next=lambda: None,
                execute_task=lambda task_id, remaining: self.fail("must not execute"),
                finalize_task=lambda run: self.fail("must not finalize a task"),
                commit_task=lambda run: self.fail("must not commit"),
                complete_task=lambda task_id, commit, receipt: self.fail(
                    "must not complete"
                ),
                finalize_session=finish,
            )
            self.assertEqual(result.status, "empty")
            self.assertEqual(calls, ["empty"])
            self.assertTrue((root / "reports/session.md").is_file())

    def test_session_failure_is_reported_without_changing_loop_status(self) -> None:
        result = run_backlog(
            limits=BacklogLimits(1, 10, 10),
            claim_next=lambda: None,
            execute_task=lambda task_id, remaining: self.fail("must not execute"),
            finalize_task=lambda run: self.fail("must not finalize a task"),
            commit_task=lambda run: self.fail("must not commit"),
            complete_task=lambda task_id, commit, receipt: self.fail(
                "must not complete"
            ),
            finalize_session=lambda result: (_ for _ in ()).throw(
                OSError("report unavailable")
            ),
        )
        self.assertEqual(result.status, "empty")
        self.assertIn("report unavailable", result.post_loop_errors[0])


if __name__ == "__main__":
    unittest.main()
