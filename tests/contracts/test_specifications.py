from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_SPEC = ROOT / "docs" / "specifications" / "orchestrator-specification-ru.md"
TASK_SPEC = ROOT / "docs" / "specifications" / "task-layer-specification-ru.md"


class SpecificationContractTests(unittest.TestCase):
    def test_normative_versions_and_sources_of_truth(self) -> None:
        orchestrator = ORCHESTRATOR_SPEC.read_text(encoding="utf-8")
        task = TASK_SPEC.read_text(encoding="utf-8")
        self.assertIn("**Версия:** 0.4", orchestrator)
        self.assertIn("**Версия:** 0.3", task)
        self.assertIn("источником истины", orchestrator)
        self.assertIn("источником истины", task)
        self.assertIn("Google Antigravity", orchestrator)
        self.assertIn("конкурентные writers не поддерживаются", task)

    def test_markdown_fences_are_balanced(self) -> None:
        for path in (ORCHESTRATOR_SPEC, TASK_SPEC):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(len(re.findall(r"^```", text, re.MULTILINE)) % 2, 0, path)
            self.assertNotIn("\ufffd", text)

    def test_architecture_documents_exist_and_define_boundaries(self) -> None:
        adr = (ROOT / "docs" / "adr" / "0001-core-boundaries.md").read_text(encoding="utf-8")
        contracts = (ROOT / "docs" / "architecture" / "component-contracts.md").read_text(encoding="utf-8")
        for component in ("Core", "Task Creator", "Task Manager", "Task Execution Workflow", "Workflow Engine"):
            self.assertIn(component, contracts)
        self.assertIn("источники истины", adr.lower())
        self.assertIn("migration", adr)
