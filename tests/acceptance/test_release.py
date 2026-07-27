from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from orchestrator.documentation import broken_local_links
from orchestrator.release import build_manifest, install_artifact, verify_manifest


ROOT = Path(__file__).resolve().parents[2]


class ReleaseAcceptanceTests(unittest.TestCase):
    def test_manifest_is_reproducible_and_checksums_verify(self) -> None:
        manifest_path = ROOT / "releases/1.0.0/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rebuilt = build_manifest(ROOT, manifest["files"].keys(), version="1.0.0")
        self.assertEqual(rebuilt, manifest)
        self.assertEqual(verify_manifest(ROOT, manifest), [])
        artifact_files = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "releases/1.0.0/artifact").rglob("*")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
        }
        self.assertEqual(set(manifest["files"]), artifact_files)

    def test_clean_managed_and_standalone_install(self) -> None:
        artifact = ROOT / "releases/1.0.0/artifact"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            managed_project = root / "managed"
            standalone_project = root / "standalone"
            managed_project.mkdir()
            standalone_project.mkdir()
            (managed_project / "owned.txt").write_text("keep", encoding="utf-8")
            managed = install_artifact(artifact, managed_project, managed=True)
            standalone = install_artifact(artifact, standalone_project, managed=False)
            self.assertEqual((managed_project / "owned.txt").read_text(encoding="utf-8"), "keep")
            self.assertTrue((managed / "orchestrator/__init__.py").is_file())
            self.assertTrue((standalone / "orchestrator/__init__.py").is_file())

    def test_supported_upgrade_and_rollback_are_documented(self) -> None:
        migration = (ROOT / "docs/migrations/1.0.md").read_text(encoding="utf-8")
        for section in ("Supported inputs", "Compatibility window", "Known limitations", "Rollback"):
            self.assertIn(section, migration)

    def test_release_readme_links_resolve_inside_artifact(self) -> None:
        artifact = ROOT / "releases/1.0.0/artifact"
        self.assertEqual(broken_local_links(artifact / "README.md", root=artifact), [])
        self.assertTrue((artifact / "CHANGELOG.md").is_file())
        self.assertTrue((artifact / "ROADMAP.md").is_file())

    def test_supported_managed_upgrade_preserves_project_state(self) -> None:
        artifact = ROOT / "releases/1.0.0/artifact"
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            previous_core = project / ".orchestrator/core/orchestrator"
            previous_core.mkdir(parents=True)
            (previous_core / "__init__.py").write_text('__version__ = "0.4.0"\n', encoding="utf-8")
            task_state = project / ".orchestrator/tasks/tasks.json"
            task_state.parent.mkdir(parents=True)
            task_state.write_text('{"schema_version": 1, "next_id": 1, "tasks": []}\n', encoding="utf-8")
            before = task_state.read_bytes()
            installed = install_artifact(artifact, project, managed=True)
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
            self.assertEqual(imported.stdout.strip(), "1.0.0")
            self.assertEqual(task_state.read_bytes(), before)
