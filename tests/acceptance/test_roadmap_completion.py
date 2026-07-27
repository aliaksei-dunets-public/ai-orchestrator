from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_RE = re.compile(r"^- (?:Create|Modify|Test): `([^`]+)`$", re.MULTILINE)
UNITTEST_RE = re.compile(r"`python -m unittest ([^`\r\n]+)`")


class RoadmapCompletionAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plans = sorted((ROOT / "docs/plans").glob("2026-*-phase-*.md"))

    def test_all_25_plans_have_acceptance_and_all_named_artifacts_exist(self) -> None:
        self.assertEqual(len(self.plans), 25)
        registry = json.loads((ROOT / "registries/skills.json").read_text(encoding="utf-8"))
        current_skill_roots = {
            entry["id"]: Path(entry["path"]).parent
            for entry in registry["entries"]
        }
        missing: list[str] = []
        for plan in self.plans:
            text = plan.read_text(encoding="utf-8")
            self.assertIn("## Acceptance Criteria", text, plan.name)
            self.assertIn("## Testing Strategy", text, plan.name)
            for relative in ARTIFACT_RE.findall(text):
                target = ROOT / relative
                parts = Path(relative).parts
                if (
                    not target.exists()
                    and len(parts) >= 3
                    and parts[0] == "skills"
                    and parts[1] in current_skill_roots
                ):
                    target = ROOT / current_skill_roots[parts[1]].joinpath(*parts[2:])
                if "*" not in relative and "?" not in relative and not target.exists():
                    missing.append(f"{plan.name}: {relative}")
        self.assertEqual(missing, [])

    def test_every_declared_unittest_target_is_importable(self) -> None:
        loader = unittest.TestLoader()
        failures: list[str] = []
        for plan in self.plans:
            for command_body in UNITTEST_RE.findall(plan.read_text(encoding="utf-8")):
                targets = [
                    token
                    for token in command_body.split()
                    if not token.startswith("-") and token not in {"discover"}
                ]
                for target in targets:
                    if target in {"tests/contracts", "'test_registry*.py'"}:
                        continue
                    suite = loader.loadTestsFromName(target)
                    errors = [
                        str(test)
                        for test in suite
                        if test.__class__.__name__ == "_FailedTest"
                    ]
                    failures.extend(f"{plan.name}: {target}: {error}" for error in errors)
        self.assertEqual(failures, [])

    def test_task_creator_validator_accepts_every_plan(self) -> None:
        validator = ROOT / "skills/system/task-creator/scripts/validate_plan.py"
        completed = subprocess.run(
            [sys.executable, str(validator), *(str(plan) for plan in self.plans)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
