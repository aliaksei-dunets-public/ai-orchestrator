from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_DISTRIBUTION = {
    "system": {
        "project-onboarding",
        "security-reviewer",
        "task-context-validator",
        "task-creator",
    },
    "bundled": {
        "code-reviewer",
        "coding-discipline",
        "documentation-manager",
        "implementation-runner",
        "improvement-designer",
        "knowledge-curator",
        "memory-manager",
        "orchestrator-auditor",
        "plan-reviewer",
        "plan-writer",
        "security-gate",
        "session-reporter",
        "task-analyzer",
        "task-reviewer",
        "test-designer",
        "test-runner",
    },
    "optional": {"optimizer", "python-code-review"},
}


class SkillDistributionContractTests(unittest.TestCase):
    def test_every_registered_skill_has_exactly_one_distribution(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        actual = {name: set() for name in EXPECTED_DISTRIBUTION}
        for entry in registry["entries"]:
            distribution = entry.get("distribution")
            self.assertIn(distribution, actual, entry)
            actual[distribution].add(entry["id"])
        self.assertEqual(actual, EXPECTED_DISTRIBUTION)

    def test_registry_schema_requires_distribution_only_for_skills(self) -> None:
        schema = json.loads((ROOT / "config/schemas/registry.schema.json").read_text(encoding="utf-8"))
        item = schema["properties"]["entries"]["items"]
        self.assertEqual(
            item["properties"]["distribution"]["enum"],
            ["system", "bundled", "optional"],
        )
        conditional = item["allOf"][0]
        self.assertEqual(conditional["if"]["properties"]["kind"]["const"], "skill")
        self.assertIn("distribution", conditional["then"]["required"])
        self.assertEqual(conditional["else"]["not"]["required"], ["distribution"])

    def test_skill_selection_schema_is_minimal_and_deduplicated(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/skill-selection.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
        optional = schema["properties"]["optional_skills"]
        self.assertTrue(optional["uniqueItems"])
        self.assertEqual(optional["items"]["pattern"], "^[a-z0-9][a-z0-9-]*$")
        self.assertFalse(schema["additionalProperties"])

    def test_technology_profile_schema_allows_unique_optional_recommendations(self) -> None:
        schema = json.loads(
            (ROOT / "config/schemas/technology-profile.schema.json").read_text(encoding="utf-8")
        )
        recommendations = schema["properties"]["recommended_optional_skills"]
        self.assertEqual(recommendations["type"], "array")
        self.assertTrue(recommendations["uniqueItems"])

    def test_profile_recommendations_resolve_to_registered_optional_skills(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        optional = {
            entry["id"]
            for entry in registry["entries"]
            if entry.get("distribution") == "optional"
        }
        for path in sorted((ROOT / "profiles/technologies").glob("*.yaml")):
            profile = json.loads(path.read_text(encoding="utf-8"))
            for skill_id in profile.get("recommended_optional_skills", []):
                self.assertIn(skill_id, optional, f"{path}: {skill_id}")


if __name__ == "__main__":
    unittest.main()
