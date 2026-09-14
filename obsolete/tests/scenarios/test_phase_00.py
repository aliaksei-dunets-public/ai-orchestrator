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
            self.assertIn("Inputs", component)
            self.assertIn("Outputs", component)
            self.assertIn("Does not own", component)
        self.assertIn("source", adr.lower())
        self.assertIn("truth", adr.lower())
        self.assertIn("canonical", adr.lower())
        for evolution_rule in ("revision", "migration", "contract tests"):
            self.assertIn(evolution_rule, adr.lower())

    def test_normative_documents_reference_both_contracts_without_broken_links(self) -> None:
        orchestrator = (ROOT / "docs/architecture/orchestrator-core.md").read_text(encoding="utf-8")
        task_layer = (ROOT / "docs/architecture/task-layer.md").read_text(encoding="utf-8")
        self.assertIn("task-layer.md", orchestrator)
        self.assertIn("orchestrator-core.md", task_layer)
        self.assertNotIn("\ufffd", orchestrator + task_layer)
