from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class ArchitectureFoundationScenarioTests(unittest.TestCase):
    def test_layers_have_single_responsibility_and_explicit_interfaces(self) -> None:
        contracts = (ROOT / "docs/architecture/component-contracts.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs/adr/0001-core-boundaries.md").read_text(encoding="utf-8")
        components = [section for section in contracts.split("\n## ") if section.strip()][1:]
        self.assertGreaterEqual(len(components), 5)
        for component in components:
            self.assertIn("Входы", component)
            self.assertIn("Выходы", component)
            self.assertTrue("Не владеет" in component or "Не превращает" in component)
        self.assertIn("источник", adr.lower())
        self.assertIn("истины", adr.lower())
        self.assertTrue("canonical" in adr.lower() or "каноническ" in adr.lower())
        for evolution_rule in ("revision", "migration", "contract tests"):
            self.assertIn(evolution_rule, adr.lower())

    def test_normative_documents_reference_both_contracts_without_broken_links(self) -> None:
        orchestrator = (ROOT / "docs/specifications/orchestrator-specification-ru.md").read_text(encoding="utf-8")
        task_layer = (ROOT / "docs/specifications/task-layer-specification-ru.md").read_text(encoding="utf-8")
        self.assertIn("task-layer-specification-ru.md", orchestrator)
        self.assertIn("orchestrator-specification-ru.md", task_layer)
        self.assertNotIn("\ufffd", orchestrator + task_layer)
