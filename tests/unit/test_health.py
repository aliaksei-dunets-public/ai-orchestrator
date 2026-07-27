from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.health import format_json, format_text, run_health_checks


ROOT = Path(__file__).resolve().parents[2]


class HealthTests(unittest.TestCase):
    def test_repository_health_has_no_errors(self) -> None:
        report = run_health_checks(ROOT)
        self.assertTrue(report.ok, format_text(report))
        self.assertEqual(report.exit_code(), 0)

    def test_text_and_json_are_views_of_same_findings(self) -> None:
        report = run_health_checks(ROOT)
        payload = json.loads(format_json(report))
        for finding in payload["findings"]:
            self.assertIn(finding["code"], format_text(report))
            self.assertIn(finding["message"], format_text(report))

    def test_corrupt_task_registry_is_reported_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / ".orchestrator" / "tasks"
            tasks.mkdir(parents=True)
            (tasks / "tasks.json").write_text("{broken", encoding="utf-8")
            report = run_health_checks(root, scope="tasks")
            self.assertFalse(report.ok)
            self.assertTrue(any(item.code == "REGISTRY_CORRUPT" for item in report.findings))

    def test_strict_fails_on_warning_only(self) -> None:
        from orchestrator.health import Finding, HealthReport

        report = HealthReport((Finding("WARN", "WARNING", "warning"),))
        self.assertEqual(report.exit_code(), 0)
        self.assertEqual(report.exit_code(strict=True), 1)

    def test_existing_codex_projection_drift_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "skills/example"
            installed = root / ".codex/skills/example"
            registry = root / "registries"
            schemas = root / "config/schemas"
            source.mkdir(parents=True)
            installed.mkdir(parents=True)
            registry.mkdir()
            schemas.mkdir(parents=True)
            (source / "SKILL.md").write_text("canonical", encoding="utf-8")
            (installed / "SKILL.md").write_text("drifted", encoding="utf-8")
            (registry / "skills.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "entries": [
                            {
                                "id": "example",
                                "path": "skills/example/SKILL.md",
                                "kind": "skill",
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_health_checks(root)
            drift = [item for item in report.findings if item.code == "SKILL_PROJECTION_DRIFT"]
            self.assertEqual(len(drift), 1)
            self.assertEqual(drift[0].severity, "ERROR")
            self.assertIn("changed", drift[0].message)
