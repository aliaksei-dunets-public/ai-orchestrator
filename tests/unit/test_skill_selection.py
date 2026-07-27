from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.skill_installer import (
    SkillSelectionError,
    install_registered_skills,
    load_skill_selection,
)


ROOT = Path(__file__).resolve().parents[2]


class SkillSelectionTests(unittest.TestCase):
    def test_missing_selection_is_empty_and_valid_selection_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            self.assertEqual(load_skill_selection(project), ())
            selection = project / ".orchestrator/skills.json"
            selection.parent.mkdir()
            selection.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "optional_skills": ["python-code-review"],
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_skill_selection(project), ("python-code-review",))

    def test_invalid_or_duplicate_selection_is_rejected(self) -> None:
        invalid_payloads = (
            {"schema_version": 2, "optional_skills": []},
            {"schema_version": 1, "optional_skills": ["optimizer", "optimizer"]},
            {"schema_version": 1, "optional_skills": ["Bad ID"]},
            {"schema_version": 1, "optional_skills": [], "extra": True},
        )
        for payload in invalid_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temporary:
                project = Path(temporary)
                selection = project / ".orchestrator/skills.json"
                selection.parent.mkdir()
                selection.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(SkillSelectionError):
                    load_skill_selection(project)

    def test_project_selection_and_project_owned_skill_join_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            selection = project / ".orchestrator/skills.json"
            selection.parent.mkdir()
            selection.write_text(
                '{"schema_version": 1, "optional_skills": ["python-code-review"]}',
                encoding="utf-8",
            )
            custom = project / ".orchestrator/project-skills/company-review"
            custom.mkdir(parents=True)
            (custom / "SKILL.md").write_text(
                "---\nname: company-review\ndescription: Project review.\n---\n",
                encoding="utf-8",
            )
            installed = project / ".codex/skills"
            result = install_registered_skills(ROOT, installed, project_root=project)
            self.assertIn("python-code-review", result)
            self.assertIn("company-review", result)
            self.assertTrue((installed / "company-review/SKILL.md").is_file())
            self.assertFalse((installed / "optimizer").exists())

    def test_unknown_non_optional_and_colliding_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            selection = project / ".orchestrator/skills.json"
            selection.parent.mkdir()
            for skill_id in ("missing-skill", "task-creator"):
                selection.write_text(
                    json.dumps({"schema_version": 1, "optional_skills": [skill_id]}),
                    encoding="utf-8",
                )
                with self.subTest(skill_id=skill_id), self.assertRaises(SkillSelectionError):
                    install_registered_skills(
                        ROOT,
                        project / ".codex/skills",
                        project_root=project,
                    )

            selection.write_text(
                '{"schema_version": 1, "optional_skills": []}',
                encoding="utf-8",
            )
            collision = project / ".orchestrator/project-skills/code-reviewer"
            collision.mkdir(parents=True)
            (collision / "SKILL.md").write_text("collision", encoding="utf-8")
            with self.assertRaises(SkillSelectionError):
                install_registered_skills(
                    ROOT,
                    project / ".codex/skills",
                    project_root=project,
                )

    def test_failed_staging_preserves_existing_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            installed = project / ".codex/skills"
            previous = installed / "previous/SKILL.md"
            previous.parent.mkdir(parents=True)
            previous.write_text("working", encoding="utf-8")
            from orchestrator import skill_installer

            original_copytree = skill_installer.shutil.copytree
            failed = False

            def fail_once_during_publish(source, destination, *args, **kwargs):
                nonlocal failed
                if Path(destination) == installed and not failed:
                    failed = True
                    raise RuntimeError("injected copy failure")
                return original_copytree(source, destination, *args, **kwargs)

            with mock.patch(
                "orchestrator.skill_installer.shutil.copytree",
                side_effect=fail_once_during_publish,
            ):
                with self.assertRaisesRegex(RuntimeError, "injected copy failure"):
                    install_registered_skills(ROOT, installed)
            self.assertEqual(previous.read_text(encoding="utf-8"), "working")

    def test_projection_cannot_replace_repository_or_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            with self.assertRaisesRegex(SkillSelectionError, "protected root"):
                install_registered_skills(ROOT, ROOT)
            with self.assertRaisesRegex(SkillSelectionError, "protected root"):
                install_registered_skills(
                    ROOT,
                    project,
                    project_root=project,
                )


if __name__ == "__main__":
    unittest.main()
