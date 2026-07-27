from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INTEGRATED = {
    "coding-discipline": "implementation-runner",
    "security-gate": "security-reviewer",
    "python-code-review": "code-reviewer",
    "optimizer": "orchestrator-auditor",
}


class UpstreamSkillContractTests(unittest.TestCase):
    def test_integrated_skills_are_registered_and_routed_by_coordinators(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        registered = {entry["id"]: entry["path"] for entry in registry["entries"]}
        for skill, coordinator in INTEGRATED.items():
            self.assertEqual(registered[skill], f"skills/{skill}/SKILL.md")
            content = (ROOT / registered[skill]).read_text(encoding="utf-8")
            self.assertIn(f"name: {skill}", content)
            coordinator_text = (ROOT / f"skills/{coordinator}/SKILL.md").read_text(encoding="utf-8")
            self.assertIn(f"`{skill}`", coordinator_text)

    def test_provenance_is_pinned_and_legacy_conflicts_are_not_registered(self) -> None:
        provenance = (ROOT / "docs/architecture/upstream-skills.md").read_text(encoding="utf-8")
        self.assertIn("4a50ba135fc05e3e98418b0b9fd8f537337d0b0a", provenance)
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        registered = {entry["id"] for entry in registry["entries"]}
        self.assertNotIn("task-manager", registered)
        self.assertNotIn("development-orchestrator-installer", registered)

    def test_python_profile_selects_python_review_and_shared_security(self) -> None:
        profile = json.loads((ROOT / "profiles/technologies/python.yaml").read_text(encoding="utf-8"))
        self.assertEqual(profile["skills"]["review"], ["python-code-review"])
        self.assertEqual(profile["skills"]["security"], ["security-gate"])
