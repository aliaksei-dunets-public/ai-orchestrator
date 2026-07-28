from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator import __version__
from orchestrator.documentation import broken_local_links
from orchestrator.release import (
    build_manifest,
    build_release_artifact,
    install_artifact,
    verify_manifest,
)
from orchestrator.skill_installer import install_registered_skills


ROOT = Path(__file__).resolve().parents[2]
VERSION = __version__
ARTIFACT = ROOT / "releases" / VERSION / "artifact"
MANIFEST = ROOT / "releases" / VERSION / "manifest.json"


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_manifest_is_reproducible_and_checksums_verify(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        rebuilt = build_manifest(ROOT, manifest["files"].keys(), version=VERSION)
        self.assertEqual(rebuilt, manifest)
        self.assertEqual(verify_manifest(ROOT, manifest), [])
        artifact_files = {
            path.relative_to(ROOT).as_posix()
            for path in ARTIFACT.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        }
        self.assertEqual(set(manifest["files"]), artifact_files)

    def test_clean_managed_and_standalone_install(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            managed_project = root / "managed"
            standalone_project = root / "standalone"
            managed_project.mkdir()
            standalone_project.mkdir()
            (managed_project / "owned.txt").write_text("keep", encoding="utf-8")
            managed = install_artifact(ARTIFACT, managed_project, managed=True)
            standalone = install_artifact(ARTIFACT, standalone_project, managed=False)
            self.assertEqual((managed_project / "owned.txt").read_text(encoding="utf-8"), "keep")
            self.assertTrue((managed / "orchestrator/__init__.py").is_file())
            self.assertTrue((standalone / "orchestrator/__init__.py").is_file())
            managed_skills = install_registered_skills(
                managed,
                managed_project / ".codex/skills",
                project_root=managed_project,
            )
            standalone_skills = install_registered_skills(
                standalone,
                standalone_project / ".codex/skills",
                project_root=standalone_project,
            )
            self.assertEqual(set(managed_skills), set(standalone_skills))
            self.assertNotIn("python-code-review", managed_skills)
            self.assertNotIn("optimizer", managed_skills)

    def test_supported_upgrade_and_rollback_are_documented(self) -> None:
        migration = (ROOT / "docs/migrations/1.2.md").read_text(encoding="utf-8")
        for section in ("Supported inputs", "Compatibility window", "Known limitations", "Rollback"):
            self.assertIn(section, migration)
        workspaces = (
            ROOT / "docs/migrations/1.3-task-workspaces.md"
        ).read_text(encoding="utf-8")
        self.assertIn("## Совместимость", workspaces)
        self.assertIn("## Rollback", workspaces)

    def test_release_readme_links_resolve_inside_artifact(self) -> None:
        self.assertEqual(broken_local_links(ARTIFACT / "README.md", root=ARTIFACT), [])
        self.assertTrue((ARTIFACT / "CHANGELOG.md").is_file())
        self.assertTrue((ARTIFACT / "ROADMAP.md").is_file())
        for category in ("system", "bundled", "optional"):
            self.assertTrue((ARTIFACT / "skills" / category).is_dir())

    def test_supported_managed_upgrade_preserves_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            previous_core = project / ".orchestrator/core/orchestrator"
            previous_core.mkdir(parents=True)
            (previous_core / "__init__.py").write_text('__version__ = "0.4.0"\n', encoding="utf-8")
            task_state = project / ".orchestrator/tasks/tasks.json"
            task_state.parent.mkdir(parents=True)
            task_state.write_text('{"schema_version": 1, "next_id": 1, "tasks": []}\n', encoding="utf-8")
            before = task_state.read_bytes()
            installed = install_artifact(ARTIFACT, project, managed=True)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(installed)
            imported = subprocess.run(
                [sys.executable, "-c", "import orchestrator; print(orchestrator.__version__)"],
                cwd=project,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertEqual(imported.stdout.strip(), VERSION)
            self.assertEqual(task_state.read_bytes(), before)

    def test_approved_optional_and_project_owned_skills_install_from_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            installed_core = install_artifact(ARTIFACT, project, managed=True)
            selection = project / ".orchestrator/skills.json"
            selection.parent.mkdir(parents=True, exist_ok=True)
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
            result = install_registered_skills(
                installed_core,
                project / ".codex/skills",
                project_root=project,
            )
            self.assertIn("python-code-review", result)
            self.assertIn("company-review", result)
            self.assertNotIn("optimizer", result)

    def test_artifact_builder_reproduces_current_release_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rebuilt = build_release_artifact(ROOT, Path(temporary) / "artifact")
            expected = {
                path.relative_to(ARTIFACT).as_posix()
                for path in ARTIFACT.rglob("*")
                if path.is_file()
            }
            actual = {
                path.relative_to(rebuilt).as_posix()
                for path in rebuilt.rglob("*")
                if path.is_file()
            }
            self.assertEqual(actual, expected)

    def test_worktree_runtime_is_in_release_artifact(self) -> None:
        for relative in (
            "orchestrator/registry_lock.py",
            "orchestrator/worktree_manager.py",
            "docs/adr/0003-task-workspace-execution-modes.md",
            "docs/migrations/1.3-task-workspaces.md",
        ):
            self.assertTrue((ARTIFACT / relative).is_file(), relative)
