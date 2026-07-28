from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "config" / "schemas"


class MemoryKnowledgeContractTests(unittest.TestCase):
    def test_lifecycle_schemas_and_core_ontology_exist(self) -> None:
        expected = {
            "memory-proposal.schema.json",
            "memory-event.schema.json",
            "memory-approval.schema.json",
            "knowledge-ontology.schema.json",
            "knowledge-index.schema.json",
            "context-pack.schema.json",
        }
        self.assertEqual(
            expected,
            {path.name for path in SCHEMAS.glob("*.json")} & expected,
        )
        for name in expected:
            schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertEqual(
                schema["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_core_ontology_has_unique_immutable_terms(self) -> None:
        ontology = json.loads(
            (ROOT / "config" / "knowledge-ontology.json").read_text(encoding="utf-8")
        )
        self.assertEqual(ontology["schema_version"], 1)
        self.assertTrue(ontology["immutable"])
        self.assertEqual(
            ontology["node_kinds"],
            ["document", "component", "contract", "decision", "task", "risk"],
        )
        self.assertEqual(
            ontology["relations"],
            [
                "defined_by",
                "depends_on",
                "implements",
                "affects",
                "supersedes",
                "produced_by",
            ],
        )
        self.assertEqual(len(ontology["node_kinds"]), len(set(ontology["node_kinds"])))
        self.assertEqual(len(ontology["relations"]), len(set(ontology["relations"])))

    def test_legacy_records_remain_valid_shapes(self) -> None:
        memory = json.loads(
            (SCHEMAS / "memory-entry.schema.json").read_text(encoding="utf-8")
        )
        node = json.loads(
            (SCHEMAS / "knowledge-node.schema.json").read_text(encoding="utf-8")
        )
        edge = json.loads(
            (SCHEMAS / "knowledge-edge.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(memory["properties"]["schema_version"]["const"], 1)
        self.assertNotIn("proposal_hash", memory["required"])
        self.assertNotIn("source_digest", node["required"])
        self.assertNotIn("source_digest", edge["required"])

    def test_project_config_and_defaults_define_bounded_target_owned_stores(self) -> None:
        project = json.loads(
            (SCHEMAS / "project-config.schema.json").read_text(encoding="utf-8")
        )
        lifecycle = project["properties"]["memory_knowledge"]
        self.assertEqual(lifecycle["type"], "object")
        defaults = (ROOT / "config" / "defaults.yaml").read_text(encoding="utf-8")
        for value in (
            ".orchestrator/memory/entries.jsonl",
            ".orchestrator/memory/events.jsonl",
            ".orchestrator/knowledge/nodes.jsonl",
            ".orchestrator/knowledge/edges.jsonl",
            "quick_chars: 2048",
            "standard_chars: 6144",
            "deep_chars: 12288",
        ):
            self.assertIn(value, defaults)


if __name__ == "__main__":
    unittest.main()
