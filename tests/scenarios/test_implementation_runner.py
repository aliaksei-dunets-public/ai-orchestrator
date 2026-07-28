from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.execution import (
    MAX_EVIDENCE_CHARS,
    MAX_STEP_ATTEMPTS,
    ExecutionError,
    ExecutionStep,
    StepOutcome,
    baseline_hash,
    execute_plan,
)
from orchestrator.telemetry import JsonlTelemetrySink, TokenUsage, load_events


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

    def test_workspace_binding_rejects_external_checkpoint(self) -> None:
        outside = self.root.parent / "external-checkpoint.json"
        with self.assertRaisesRegex(ExecutionError, "assigned workspace"):
            execute_plan(
                context_path=self.context,
                expected_revision=1,
                expected_baseline_hash=self.digest,
                steps=[ExecutionStep("one", "First")],
                run_step=lambda step, attempt: StepOutcome("completed", "ok"),
                checkpoint_path=outside,
                workspace_root=self.root,
            )

    def test_attempt_budget_has_a_hard_upper_bound(self) -> None:
        with self.assertRaisesRegex(ValueError, str(MAX_STEP_ATTEMPTS)):
            ExecutionStep("one", "First", max_attempts=MAX_STEP_ATTEMPTS + 1)

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

    def test_evidence_is_bounded_and_telemetry_excludes_payload(self) -> None:
        telemetry_path = self.root / "telemetry.jsonl"
        diagnostic_tail = "TAIL-DIAGNOSTIC"
        large_evidence = "sensitive-output-" * 400 + diagnostic_tail
        ticks = iter((0.0, 1.0, 1.025, 1.030))
        result = execute_plan(
            context_path=self.context,
            expected_revision=1,
            expected_baseline_hash=self.digest,
            steps=[ExecutionStep("one", "First")],
            run_step=lambda step, attempt: StepOutcome(
                "completed",
                large_evidence,
                evidence_ref="artifacts/TASK-0001/attempt-1.log",
                usage=TokenUsage(total_tokens=120, tool_result_tokens=20),
                tool_calls=2,
                agent_handoffs=1,
            ),
            checkpoint_path=self.checkpoint,
            telemetry_sink=JsonlTelemetrySink(telemetry_path),
            clock=lambda: next(ticks),
        )
        stored = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        bounded = stored["records"][0]["evidence"][0]
        self.assertLessEqual(len(bounded), MAX_EVIDENCE_CHARS)
        self.assertIn("truncated chars=", bounded)
        self.assertTrue(bounded.endswith(diagnostic_tail))
        self.assertEqual(
            stored["records"][0]["evidence_refs"],
            ["artifacts/TASK-0001/attempt-1.log"],
        )
        raw_telemetry = telemetry_path.read_text(encoding="utf-8")
        self.assertNotIn("sensitive-output", raw_telemetry)
        events = load_events(telemetry_path)
        self.assertEqual([item["event"] for item in events], ["step_attempt", "run_completed"])
        self.assertEqual(result.telemetry.tool_calls, 2)
        self.assertEqual(result.telemetry.agent_handoffs, 1)
        self.assertEqual(result.telemetry.usage.total_tokens, 120)

    def test_telemetry_failure_is_reported_without_failing_execution(self) -> None:
        class BrokenSink:
            def emit(self, event) -> None:
                raise OSError("telemetry disk unavailable")

        result = execute_plan(
            context_path=self.context,
            expected_revision=1,
            expected_baseline_hash=self.digest,
            steps=[ExecutionStep("one", "First")],
            run_step=lambda step, attempt: StepOutcome("completed", "done"),
            checkpoint_path=self.checkpoint,
            telemetry_sink=BrokenSink(),
        )
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.telemetry_errors)
        self.assertIn("telemetry disk unavailable", result.telemetry_errors[0])
