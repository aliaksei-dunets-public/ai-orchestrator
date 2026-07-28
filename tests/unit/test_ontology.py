from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.ontology import OntologyError, load_core_ontology, merge_ontology


class OntologyTests(unittest.TestCase):
    def test_project_terms_are_additive(self) -> None:
        core = load_core_ontology()
        merged = merge_ontology(
            core,
            {
                "schema_version": 1,
                "immutable": False,
                "node_kinds": ["service"],
                "relations": ["calls"],
            },
        )
        self.assertIn("component", merged.node_kinds)
        self.assertIn("service", merged.node_kinds)
        self.assertIn("calls", merged.relations)

    def test_core_redefinition_and_invalid_terms_are_rejected(self) -> None:
        core = load_core_ontology()
        with self.assertRaisesRegex(OntologyError, "redefine"):
            merge_ontology(
                core,
                {
                    "schema_version": 1,
                    "immutable": False,
                    "node_kinds": ["component"],
                    "relations": [],
                },
            )
        with self.assertRaisesRegex(OntologyError, "term"):
            merge_ontology(
                core,
                {
                    "schema_version": 1,
                    "immutable": False,
                    "node_kinds": ["Bad Term"],
                    "relations": [],
                },
            )


if __name__ == "__main__":
    unittest.main()
