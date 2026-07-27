from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.audit import audit_repository


class AuditScenarioTests(unittest.TestCase):
    def test_seeded_contradiction_dead_workflow_and_missing_test(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/a.md").write_text(
                "NORMATIVE writer=single\nAUDIT_EXPECT_TEST: impossible_subject_xyz\n",
                encoding="utf-8",
            )
            (root / "docs/b.md").write_text("NORMATIVE writer=multiple\n", encoding="utf-8")
            (root / "registries").mkdir()
            (root / "registries/workflows.json").write_text(
                json.dumps({"entries": [{"id": "dead", "path": "workflows/dead.yaml"}]}),
                encoding="utf-8",
            )
            (root / "tests").mkdir()
            report = audit_repository(root)
            codes = {item.code for item in report.findings}
            self.assertEqual(codes, {"CONTRADICTORY_RULE", "DEAD_WORKFLOW", "MISSING_TEST"})
            for finding in report.findings:
                self.assertTrue(finding.evidence)
                self.assertTrue(finding.severity)
                self.assertTrue(finding.proposal)

    def test_audit_is_read_only_and_deduplicates_known_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            document = root / "docs/spec.md"
            document.write_text(
                "NORMATIVE x=one\nNORMATIVE x=two\nNORMATIVE x=two\n",
                encoding="utf-8",
            )
            before = document.read_bytes()
            first = audit_repository(root)
            self.assertEqual(document.read_bytes(), before)
            fingerprints = [item.fingerprint for item in first.findings]
            self.assertEqual(len(fingerprints), len(set(fingerprints)))
            second = audit_repository(root, known_fingerprints=fingerprints)
            self.assertEqual(second.findings, ())

    def test_inventory_detects_skill_workflow_schema_and_runtime_test_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "registries").mkdir()
            (root / "skills/orphan").mkdir(parents=True)
            (root / "skills/orphan/SKILL.md").write_text(
                "---\nname: orphan\n description: fixture\n---\n",
                encoding="utf-8",
            )
            (root / "workflows").mkdir()
            (root / "workflows/main.yaml").write_text(
                "schema_version: 1\nid: main\nsteps:\n"
                "  - id: run\n    skill: missing-skill\n    depends_on: [missing-step]\n",
                encoding="utf-8",
            )
            (root / "registries/skills.json").write_text(
                json.dumps({"entries": []}),
                encoding="utf-8",
            )
            (root / "registries/workflows.json").write_text(
                json.dumps({"entries": [{"id": "main", "path": "workflows/main.yaml"}]}),
                encoding="utf-8",
            )
            (root / "config/schemas").mkdir(parents=True)
            (root / "config/schemas/old.json").write_text(
                json.dumps({"$schema": "http://json-schema.org/draft-07/schema#"}),
                encoding="utf-8",
            )
            (root / "orchestrator").mkdir()
            (root / "orchestrator/uncovered.py").write_text("VALUE = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests/test_other.py").write_text("def test_other(): pass\n", encoding="utf-8")
            codes = {item.code for item in audit_repository(root).findings}
            self.assertTrue(
                {
                    "UNREGISTERED_SKILL",
                    "DANGLING_SKILL_REFERENCE",
                    "DANGLING_WORKFLOW_STEP",
                    "SCHEMA_DRAFT_DRIFT",
                    "UNTESTED_RUNTIME_MODULE",
                }.issubset(codes)
            )
