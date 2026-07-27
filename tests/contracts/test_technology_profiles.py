from __future__ import annotations

import unittest
from pathlib import Path

from orchestrator.technologies import (
    TechnologyProfileError,
    command_is_automatic,
    detect_technology,
    load_technology_profile,
    merge_profiles,
    recommend_optional_skills,
)


ROOT = Path(__file__).resolve().parents[2]


class TechnologyProfileContractTests(unittest.TestCase):
    def test_sandbox_projects_select_expected_profiles_with_evidence(self) -> None:
        python = load_technology_profile(ROOT / "profiles/technologies/python.yaml")
        abap = load_technology_profile(ROOT / "profiles/technologies/abap-rap.yaml")
        py_detection = detect_technology(ROOT / "tests/sandbox-projects/python-minimal", python)
        abap_detection = detect_technology(ROOT / "tests/sandbox-projects/abap-rap-minimal", abap)
        self.assertGreater(py_detection.confidence, 0)
        self.assertTrue(py_detection.evidence)
        self.assertGreater(abap_detection.confidence, 0)
        self.assertTrue(abap_detection.evidence)

    def test_merge_precedence_is_stable_and_conflicts_are_explicit(self) -> None:
        low = {"id": "low", "precedence": 20, "commands": {"a": {"argv": ["a"]}}}
        high = {"id": "high", "precedence": 10, "commands": {"b": {"argv": ["b"]}}}
        merged = merge_profiles([low, high])
        self.assertEqual(merged["profiles"], ["high", "low"])
        conflict = {"id": "conflict", "precedence": 30, "commands": {"a": {"argv": ["other"]}}}
        with self.assertRaisesRegex(TechnologyProfileError, "Conflicting"):
            merge_profiles([low, conflict])

    def test_unknown_or_approval_required_command_is_not_automatic(self) -> None:
        python = load_technology_profile(ROOT / "profiles/technologies/python.yaml")
        abap = load_technology_profile(ROOT / "profiles/technologies/abap-rap.yaml")
        self.assertTrue(command_is_automatic(python["commands"]["test"]))
        self.assertFalse(command_is_automatic(abap["commands"]["unit-test"]))
        self.assertFalse(command_is_automatic({"argv": ["unknown"]}))

    def test_optional_recommendations_are_explicit_profile_metadata(self) -> None:
        python = load_technology_profile(ROOT / "profiles/technologies/python.yaml")
        abap = load_technology_profile(ROOT / "profiles/technologies/abap-rap.yaml")
        self.assertEqual(python["recommended_optional_skills"], ["python-code-review"])
        self.assertEqual(abap.get("recommended_optional_skills", []), [])
        self.assertEqual(
            recommend_optional_skills([abap, python], {"python-code-review", "optimizer"}),
            ("python-code-review",),
        )

    def test_unknown_optional_recommendation_is_rejected(self) -> None:
        profile = {
            "schema_version": 1,
            "id": "invalid",
            "precedence": 1,
            "detection": {},
            "commands": {},
            "recommended_optional_skills": ["missing"],
        }
        with self.assertRaisesRegex(TechnologyProfileError, "Unknown optional skill"):
            recommend_optional_skills([profile], {"optimizer"})

    def test_duplicate_optional_recommendations_are_rejected_on_load(self) -> None:
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "profile.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "invalid",
                        "precedence": 1,
                        "detection": {},
                        "commands": {},
                        "recommended_optional_skills": ["optimizer", "optimizer"],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(TechnologyProfileError, "unique skill ids"):
                load_technology_profile(path)
