from __future__ import annotations

import json
import unittest
from pathlib import Path

from orchestrator.review import task_review


ROOT = Path(__file__).resolve().parents[2]


class TaskReviewScenarioTests(unittest.TestCase):
    def test_pass_has_coverage_for_every_criterion(self) -> None:
        result = task_review(
            acceptance_criteria=["CLI works", "Tests pass"],
            evidence={"CLI works": True, "Tests pass": True},
            in_scope_paths=["orchestrator", "tests"],
            changed_paths=["orchestrator/cli.py", "tests/test_cli.py"],
        )
        self.assertEqual(result.verdict, "approved")
        self.assertEqual([item.status for item in result.criteria], ["satisfied", "satisfied"])
        self.assertEqual(result.to_dict()["schema_version"], 1)

    def test_missing_evidence_and_scope_creep_are_blocking(self) -> None:
        result = task_review(
            acceptance_criteria=["CLI works", "Tests pass"],
            evidence={"CLI works": True},
            in_scope_paths=["orchestrator/cli.py"],
            changed_paths=["orchestrator/cli.py", "README.md"],
        )
        self.assertEqual(result.verdict, "rework")
        self.assertEqual(result.criteria[1].status, "unverified")
        self.assertEqual({item.code for item in result.findings}, {"ACCEPTANCE_NOT_SATISFIED", "SCOPE_CREEP"})

    def test_result_matches_shared_schema_required_shape(self) -> None:
        schema = json.loads((ROOT / "config/schemas/review-result.schema.json").read_text(encoding="utf-8"))
        result = task_review(
            acceptance_criteria=["Works"],
            evidence={"Works": False},
            in_scope_paths=["src"],
            changed_paths=["src/a.py"],
        ).to_dict()
        self.assertEqual(set(schema["required"]) - set(result), set())
        self.assertIn(result["verdict"], schema["properties"]["verdict"]["enum"])
