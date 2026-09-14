from __future__ import annotations

import unittest
from copy import deepcopy
from pathlib import Path

from orchestrator.technologies import (
    TechnologyProfileError,
    command_is_automatic,
    detect_technology,
    load_technology_profile,
    merge_profiles,
)


ROOT = Path(__file__).resolve().parents[2]


class TechnologyProfileScenarioTests(unittest.TestCase):
    def test_python_and_abap_sandboxes_produce_explained_detection(self) -> None:
        cases = (
            ("python.yaml", "python-minimal", "python"),
            ("abap-rap.yaml", "abap-rap-minimal", "abap-rap"),
        )
        for profile_name, sandbox_name, expected in cases:
            with self.subTest(profile=expected):
                profile = load_technology_profile(ROOT / "profiles/technologies" / profile_name)
                detection = detect_technology(ROOT / "tests/sandbox-projects" / sandbox_name, profile)
                self.assertEqual(detection.profile_id, expected)
                self.assertGreater(detection.confidence, 0)
                self.assertTrue(all(item.startswith(("marker:", "extension:")) for item in detection.evidence))

    def test_composite_order_is_stable_and_unknown_command_fails_closed(self) -> None:
        python = load_technology_profile(ROOT / "profiles/technologies/python.yaml")
        abap = load_technology_profile(ROOT / "profiles/technologies/abap-rap.yaml")
        with self.assertRaisesRegex(TechnologyProfileError, "Conflicting"):
            merge_profiles([abap, python])
        non_conflicting_abap = deepcopy(abap)
        non_conflicting_abap["directories"] = {"abap_source": ["src"], "abap_tests": ["test"]}
        merged = merge_profiles([non_conflicting_abap, python])
        self.assertEqual(merged["profiles"], ["python", "abap-rap"])
        self.assertFalse(command_is_automatic({"argv": ["unknown-tool"]}))
