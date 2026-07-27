from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.skill_installer import install_registered_skills
from orchestrator.technologies import (
    load_technology_profile,
    recommend_optional_skills,
)


ROOT = Path(__file__).resolve().parents[2]


class OptionalSkillOnboardingScenarioTests(unittest.TestCase):
    def test_recommendation_is_read_only_until_explicit_selection(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        available = {
            entry["id"]
            for entry in registry["entries"]
            if entry["distribution"] == "optional"
        }
        python = load_technology_profile(ROOT / "profiles/technologies/python.yaml")
        recommendations = recommend_optional_skills([python], available)
        self.assertEqual(recommendations, ("python-code-review",))

        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            selection = project / ".orchestrator/skills.json"
            installed = project / ".codex/skills"
            self.assertFalse(selection.exists())

            initial = install_registered_skills(ROOT, installed, project_root=project)
            self.assertNotIn("python-code-review", initial)
            self.assertFalse(selection.exists())

            selection.parent.mkdir(parents=True)
            selection.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "optional_skills": list(recommendations),
                    }
                ),
                encoding="utf-8",
            )
            approved = install_registered_skills(ROOT, installed, project_root=project)
            self.assertIn("python-code-review", approved)
            self.assertTrue((installed / "python-code-review/SKILL.md").is_file())

    def test_abap_profile_has_no_missing_optional_recommendation(self) -> None:
        abap = load_technology_profile(ROOT / "profiles/technologies/abap-rap.yaml")
        self.assertEqual(recommend_optional_skills([abap], {"optimizer"}), ())


if __name__ == "__main__":
    unittest.main()
