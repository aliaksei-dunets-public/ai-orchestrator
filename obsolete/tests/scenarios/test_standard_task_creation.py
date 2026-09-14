from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from orchestrator.task_creation import (
    PlanTask,
    TaskContextDefinition,
    TaskCreationError,
    render_task_context,
    review_plan,
)


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "skills" / "system" / "task-creator" / "scripts" / "validate_task_context.py"
SPEC = importlib.util.spec_from_file_location("standard_context_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def definition(*, mode: str = "standard", approved: bool = False) -> TaskContextDefinition:
    return TaskContextDefinition(
        title="Implement feature",
        task_type="feature",
        mode=mode,
        risk="high" if mode == "deep" else "medium",
        original_request="Implement a validated feature.",
        goal="Produce the requested behavior.",
        problem="The behavior is absent.",
        current_behavior="No supported behavior.",
        expected_behavior="The behavior is available and tested.",
        analysis="Repository evidence identifies one integration boundary.",
        selected_approach="Add a focused component behind the existing boundary.",
        alternatives=["Modify Core directly — rejected due to coupling."],
        in_scope=["Component", "Contract tests"],
        out_of_scope=["Unrelated refactor"],
        components=["orchestrator/component.py"],
        acceptance_criteria=["Contract and scenario tests pass."],
        constraints=["No new runtime dependency."],
        risks=["Interface drift."],
        plan=["Write contract test.", "Implement component.", "Run scenario suite."],
        plan_review="Approved: complete, ordered and testable.",
        open_questions=[],
        approach_approved=approved,
    )


class StandardTaskCreationScenarioTests(unittest.TestCase):
    def test_standard_context_covers_normative_contract(self) -> None:
        content = render_task_context(definition())
        self.assertEqual(VALIDATOR.validate_text(content, "draft"), [])

    def test_defective_plan_returns_to_writer(self) -> None:
        review = review_plan(
            [PlanTask("Component", ("orchestrator/component.py",), ("Implement.",), (), ("Works.",))],
            ["Works."],
        )
        self.assertFalse(review.approved)
        self.assertIn("task 1 has no tests", review.issues)

    def test_deep_context_requires_explicit_approval(self) -> None:
        with self.assertRaises(TaskCreationError):
            render_task_context(definition(mode="deep", approved=False))
        approved = render_task_context(definition(mode="deep", approved=True))
        self.assertIn("approach_approved: true", approved)
