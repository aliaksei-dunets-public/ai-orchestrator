from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.execution import (
    ExecutionError,
    ExecutionStep,
    StepOutcome,
    baseline_hash,
    execute_plan,
)


CONTEXT = """---
schema_version: 1
id: TASK-0001
revision: 1
title: Example
---

# TASK-0001 — Example

## План реализации

- First.
- Second.

# Execution Record
"""


class ImplementationRunnerScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.context = self.root / "TASK-0001.md"
        self.context.write_text(CONTEXT, encoding="utf-8")
        self.checkpoint = self.root / "checkpoint.json"
        self.digest = baseline_hash(CONTEXT)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_stale_context_is_rejected_before_first_step(self) -> None:
        calls: list[str] = []
        changed = CONTEXT.replace("- Second.", "- Changed.")
        self.context.write_text(changed, encoding="utf-8")
        with self.assertRaises(ExecutionError):
            execute_plan(
                context_path=self.context,
                expected_revision=1,
                expected_baseline_hash=self.digest,
                steps=[ExecutionStep("one", "First")],
                run_step=lambda step, attempt: calls.append(step.id) or StepOutcome("completed", "ok"),
                checkpoint_path=self.checkpoint,
            )
        self.assertEqual(calls, [])

    def test_retries_are_bounded_and_each_attempt_has_evidence(self) -> None:
        def runner(step: ExecutionStep, attempt: int) -> StepOutcome:
            if attempt == 1:
                return StepOutcome("failed", "first attempt failed")
            return StepOutcome("completed", "second attempt passed")

        result = execute_plan(
            context_path=self.context,
            expected_revision=1,
            expected_baseline_hash=self.digest,
            steps=[ExecutionStep("one", "First", max_attempts=2)],
            run_step=runner,
            checkpoint_path=self.checkpoint,
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.records[0].attempts, 2)
        self.assertEqual(result.records[0].evidence, ["first attempt failed", "second attempt passed"])

    def test_restart_skips_completed_checkpoint(self) -> None:
        completed_calls: list[str] = []

        def interrupted(step: ExecutionStep, attempt: int) -> StepOutcome:
            if step.id == "one":
                return StepOutcome("completed", "one done")
            raise RuntimeError("process interrupted")

        with self.assertRaises(RuntimeError):
            execute_plan(
                context_path=self.context,
                expected_revision=1,
                expected_baseline_hash=self.digest,
                steps=[ExecutionStep("one", "First"), ExecutionStep("two", "Second")],
                run_step=interrupted,
                checkpoint_path=self.checkpoint,
            )

        def resumed(step: ExecutionStep, attempt: int) -> StepOutcome:
            completed_calls.append(step.id)
            return StepOutcome("completed", f"{step.id} done")

        result = execute_plan(
            context_path=self.context,
            expected_revision=1,
            expected_baseline_hash=self.digest,
            steps=[ExecutionStep("one", "First"), ExecutionStep("two", "Second")],
            run_step=resumed,
            checkpoint_path=self.checkpoint,
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(completed_calls, ["two"])

    def test_scope_change_stops_in_waiting_user(self) -> None:
        result = execute_plan(
            context_path=self.context,
            expected_revision=1,
            expected_baseline_hash=self.digest,
            steps=[ExecutionStep("one", "First")],
            run_step=lambda step, attempt: StepOutcome("scope_change", "Need to expand public API"),
            checkpoint_path=self.checkpoint,
        )
        self.assertEqual(result.status, "waiting_user")
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "waiting_user")
        self.assertIn("expand public API", payload["reason"])
