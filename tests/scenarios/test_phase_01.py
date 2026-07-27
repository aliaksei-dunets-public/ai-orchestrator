from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RepositoryScaffoldScenarioTests(unittest.TestCase):
    def test_editable_install_and_import_from_temporary_project_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            target = root / "site"
            source.mkdir()
            shutil.copy2(ROOT / "pyproject.toml", source / "pyproject.toml")
            shutil.copy2(ROOT / "README.md", source / "README.md")
            shutil.copytree(ROOT / "orchestrator", source / "orchestrator")
            install = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "-e",
                    str(source),
                    "--no-deps",
                    "--no-build-isolation",
                    "--target",
                    str(target),
                    "--disable-pip-version-check",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stdout + install.stderr)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(target)
            imported = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        f"import site; site.addsitedir({str(target)!r}); "
                        "import orchestrator; print(orchestrator.__version__)"
                    ),
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertEqual(imported.stdout.strip(), "1.0.0")

    def test_registries_reference_existing_artifacts_and_agents_is_safe(self) -> None:
        for registry_name in ("skills.json", "workflows.json"):
            payload = json.loads((ROOT / "registries" / registry_name).read_text(encoding="utf-8"))
            for entry in payload["entries"]:
                self.assertTrue((ROOT / entry["path"]).is_file(), entry)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8").lower()
        for requirement in ("security", "test", "task"):
            self.assertIn(requirement, agents)
