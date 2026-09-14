from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.skill_installer import check_skill_drift, install_registered_skills, install_skill


ROOT = Path(__file__).resolve().parents[2]


class SkillInstallationContractTests(unittest.TestCase):
    def test_install_is_idempotent_and_detects_drift(self) -> None:
        source = ROOT / "skills" / "system" / "task-creator"
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / ".codex" / "skills" / "task-creator"
            self.assertTrue(install_skill(source, installed).clean)
            self.assertTrue(install_skill(source, installed).clean)
            (installed / "SKILL.md").write_text("manual drift", encoding="utf-8")
            drift = check_skill_drift(source, installed)
            self.assertIn("SKILL.md", drift.changed)

    def test_missing_and_extra_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            installed = root / "installed"
            source.mkdir()
            installed.mkdir()
            (source / "SKILL.md").write_text("source", encoding="utf-8")
            (source / "missing.txt").write_text("missing", encoding="utf-8")
            (installed / "SKILL.md").write_text("source", encoding="utf-8")
            (installed / "extra.txt").write_text("extra", encoding="utf-8")
            drift = check_skill_drift(source, installed)
            self.assertEqual(drift.missing, ("missing.txt",))
            self.assertEqual(drift.extra, ("extra.txt",))

    def test_registry_driven_workspace_projection_is_complete_and_idempotent(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        expected = {
            entry["id"]
            for entry in registry["entries"]
            if entry["enabled"] and entry["distribution"] in {"system", "bundled"}
        }
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / ".codex/skills"
            first = install_registered_skills(ROOT, installed)
            second = install_registered_skills(ROOT, installed)
            self.assertEqual(set(first), expected)
            self.assertEqual(set(second), expected)
            self.assertTrue(all(drift.clean for drift in first.values()))
            self.assertTrue(all(drift.clean for drift in second.values()))

    def test_checked_in_codex_workspace_projection_has_zero_drift(self) -> None:
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        expected = {
            entry["id"]
            for entry in registry["entries"]
            if entry["enabled"] and entry["distribution"] in {"system", "bundled"}
        }
        installed_ids = {
            path.name
            for path in (ROOT / ".codex/skills").iterdir()
            if path.is_dir()
        }
        self.assertEqual(installed_ids, expected)
        for entry in registry["entries"]:
            if not entry["enabled"] or entry["distribution"] == "optional":
                continue
            source = (ROOT / entry["path"]).parent
            installed = ROOT / ".codex/skills" / entry["id"]
            self.assertTrue(
                check_skill_drift(source, installed).clean,
                f"Workspace skill projection drifted: {entry['id']}",
            )

    def test_approved_optional_skill_is_installed_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            installed = Path(temporary) / ".codex/skills"
            result = install_registered_skills(
                ROOT,
                installed,
                optional_skills=("python-code-review",),
            )
            self.assertIn("python-code-review", result)
            self.assertNotIn("optimizer", result)
