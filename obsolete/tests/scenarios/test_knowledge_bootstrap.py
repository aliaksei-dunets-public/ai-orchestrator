from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.knowledge import KnowledgeError
from orchestrator.knowledge_bootstrap import prepare_graph_update
from orchestrator.ontology import load_core_ontology


class KnowledgeBootstrapTests(unittest.TestCase):
    def _root(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        source = root / "docs/specifications/system.md"
        source.parent.mkdir(parents=True)
        source.write_text("canonical", encoding="utf-8")
        nodes = root / ".orchestrator/knowledge/nodes.jsonl"
        edges = root / ".orchestrator/knowledge/edges.jsonl"
        nodes.parent.mkdir(parents=True)
        nodes.write_text("", encoding="utf-8")
        edges.write_text("", encoding="utf-8")
        return temporary, root, nodes, edges

    def test_prepare_graph_update_is_non_mutating_and_deterministic(self) -> None:
        temporary, root, nodes, edges = self._root()
        self.addCleanup(temporary.cleanup)
        proposal = {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "component-b",
                    "kind": "component",
                    "label": "B",
                    "source": "docs/specifications/system.md",
                },
                {
                    "id": "component-a",
                    "kind": "component",
                    "label": "A",
                    "source": "docs/specifications/system.md",
                },
            ],
            "edges": [
                {
                    "id": "edge-a",
                    "source_node": "component-a",
                    "target_node": "component-b",
                    "relation": "depends_on",
                    "source": "docs/specifications/system.md",
                }
            ],
        }
        before_nodes = nodes.read_bytes()
        before_edges = edges.read_bytes()
        first = prepare_graph_update(
            root,
            nodes,
            edges,
            proposal,
            ontology=load_core_ontology(),
        )
        second = prepare_graph_update(
            root,
            nodes,
            edges,
            proposal,
            ontology=load_core_ontology(),
        )
        self.assertEqual(first.nodes_content, second.nodes_content)
        self.assertEqual(first.edges_content, second.edges_content)
        self.assertEqual(nodes.read_bytes(), before_nodes)
        self.assertEqual(edges.read_bytes(), before_edges)
        self.assertEqual(first.effective_node_ids, ("component-a", "component-b"))
        self.assertEqual(first.effective_edge_ids, ("edge-a",))

    def test_conflicting_id_and_invalid_provenance_fail_before_writes(self) -> None:
        temporary, root, nodes, edges = self._root()
        self.addCleanup(temporary.cleanup)
        base = {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "component-a",
                    "kind": "component",
                    "label": "A",
                    "source": "docs/specifications/system.md",
                }
            ],
            "edges": [],
        }
        prepared = prepare_graph_update(
            root, nodes, edges, base, ontology=load_core_ontology()
        )
        nodes.write_text(prepared.nodes_content, encoding="utf-8")
        with self.assertRaisesRegex(KnowledgeError, "Conflicting"):
            prepare_graph_update(
                root,
                nodes,
                edges,
                {
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "component-a",
                            "kind": "component",
                            "label": "different",
                            "source": "docs/specifications/system.md",
                        }
                    ],
                    "edges": [],
                },
                ontology=load_core_ontology(),
            )
        with self.assertRaisesRegex(KnowledgeError, "outside the project|excluded"):
            prepare_graph_update(
                root,
                nodes,
                edges,
                {
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "secret",
                            "kind": "document",
                            "label": "Secret",
                            "source": "../outside.md",
                        }
                    ],
                    "edges": [],
                },
                ontology=load_core_ontology(),
            )

    def test_dangling_edge_and_agent_supplied_digest_are_rejected(self) -> None:
        temporary, root, nodes, edges = self._root()
        self.addCleanup(temporary.cleanup)
        with self.assertRaisesRegex(KnowledgeError, "unknown|effective"):
            prepare_graph_update(
                root,
                nodes,
                edges,
                {
                    "schema_version": 1,
                    "nodes": [],
                    "edges": [
                        {
                            "id": "edge-a",
                            "source_node": "missing-a",
                            "target_node": "missing-b",
                            "relation": "depends_on",
                            "source": "docs/specifications/system.md",
                        }
                    ],
                },
                ontology=load_core_ontology(),
            )
        with self.assertRaisesRegex(KnowledgeError, "source_digest"):
            prepare_graph_update(
                root,
                nodes,
                edges,
                {
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "component-a",
                            "kind": "component",
                            "label": "A",
                            "source": "docs/specifications/system.md",
                            "source_digest": "0" * 64,
                        }
                    ],
                    "edges": [],
                },
                ontology=load_core_ontology(),
            )


if __name__ == "__main__":
    unittest.main()
