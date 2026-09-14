from __future__ import annotations

import unittest

from orchestrator.workflow import ExecutionPolicy, select_execution_route


class WorkflowRoutingScenarioTests(unittest.TestCase):
    def test_quick_low_risk_uses_minimal_route_with_security(self) -> None:
        route = select_execution_route(ExecutionPolicy("quick", "low"))
        self.assertEqual(
            route.steps,
            ("freshness", "implement", "run-tests", "security-review"),
        )
        self.assertEqual(route.security_depth, "deterministic")
        self.assertFalse(route.independent_review)

    def test_standard_route_keeps_semantic_quality_gates(self) -> None:
        route = select_execution_route(ExecutionPolicy("standard", "medium"))
        self.assertEqual(
            route.steps,
            (
                "freshness",
                "implement",
                "design-tests",
                "run-tests",
                "task-review",
                "code-review",
                "security-review",
            ),
        )
        self.assertEqual(route.security_depth, "deterministic")

    def test_deep_or_high_risk_requires_independent_and_semantic_security(self) -> None:
        deep = select_execution_route(ExecutionPolicy("deep", "medium"))
        high = select_execution_route(ExecutionPolicy("quick", "high"))
        for route in (deep, high):
            self.assertIn("independent-review", route.steps)
            self.assertIn("security-review", route.steps)
            self.assertEqual(route.security_depth, "semantic")

    def test_impact_flags_add_only_required_steps(self) -> None:
        route = select_execution_route(
            ExecutionPolicy(
                "quick",
                "low",
                test_design_required=True,
                approval_required=True,
                documentation_impact=True,
            )
        )
        self.assertIn("design-tests", route.steps)
        self.assertEqual(route.steps[-2:], ("approvals", "documentation"))

    def test_security_sensitive_quick_task_escalates_semantic_reviews(self) -> None:
        route = select_execution_route(
            ExecutionPolicy("quick", "low", security_sensitive=True)
        )
        self.assertIn("code-review", route.steps)
        self.assertIn("independent-review", route.steps)
        self.assertEqual(route.security_depth, "semantic")

    def test_security_review_is_present_in_every_route(self) -> None:
        for mode in ("quick", "standard", "deep"):
            for risk in ("low", "medium", "high", "critical"):
                route = select_execution_route(ExecutionPolicy(mode, risk))
                self.assertIn("security-review", route.steps)
