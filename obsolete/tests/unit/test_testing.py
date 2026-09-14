from __future__ import annotations

import sys
import unittest

from orchestrator.testing import TestCaseSpec, TestPlanError, run_test, validate_test_plan


class TestDesignerTests(unittest.TestCase):
    def test_every_acceptance_criterion_must_have_a_check(self) -> None:
        cases = [TestCaseSpec("a", ("criterion a",), (sys.executable, "-c", "pass"))]
        with self.assertRaisesRegex(TestPlanError, "criterion b"):
            validate_test_plan(["criterion a", "criterion b"], cases)

    def test_regression_is_required_only_for_fixed_bug(self) -> None:
        focused = [TestCaseSpec("a", ("works",), (sys.executable, "-c", "pass"))]
        with self.assertRaisesRegex(TestPlanError, "requires a regression"):
            validate_test_plan(["works"], focused, fixed_bug=True)
        regression = [
            TestCaseSpec("a", ("works",), (sys.executable, "-c", "pass"), kind="regression")
        ]
        validate_test_plan(["works"], regression, fixed_bug=True)
        with self.assertRaisesRegex(TestPlanError, "reserved for fixed bugs"):
            validate_test_plan(["works"], regression, fixed_bug=False)


class TestRunnerTests(unittest.TestCase):
    def test_passing_and_failing_commands_capture_evidence(self) -> None:
        passing = run_test(TestCaseSpec("pass", ("works",), (sys.executable, "-c", "print('ok')")))
        failing = run_test(
            TestCaseSpec("fail", ("works",), (sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"))
        )
        self.assertEqual((passing.status, passing.exit_code), ("passed", 0))
        self.assertIn("ok", passing.summary)
        self.assertEqual((failing.status, failing.exit_code), ("failed", 3))
        self.assertIn("bad", failing.summary)

    def test_timeout_and_missing_tool_are_blocked(self) -> None:
        timeout = run_test(
            TestCaseSpec("timeout", ("works",), (sys.executable, "-c", "import time; time.sleep(2)")),
            timeout_seconds=0.01,
        )
        missing = run_test(
            TestCaseSpec("missing", ("works",), ("definitely-not-an-orchestrator-tool",))
        )
        self.assertEqual(timeout.status, "blocked")
        self.assertIn("Timed out", timeout.summary)
        self.assertEqual(missing.status, "blocked")
        self.assertIn("Tool unavailable", missing.summary)
