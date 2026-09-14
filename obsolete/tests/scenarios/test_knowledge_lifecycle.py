from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.knowledge import (
    KnowledgeEdge,
    KnowledgeError,
    KnowledgeNode,
    add_edge,
    add_node,
    effective_graph,
    rebuild_indexes,
)
from orchestrator.ontology import load_core_ontology


class KnowledgeLifecycleTests(unittest.TestCase):
    def test_project_aware_writes_validate_ontology_provenance_and_effective_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical", encoding="utf-8")
            nodes = root / ".orchestrator/knowledge/nodes.jsonl"
            edges = root / ".orchestrator/knowledge/edges.jsonl"
            ontology = load_core_ontology()
            add_node(
                nodes,
                KnowledgeNode("N1", "document", "Spec", "docs/specifications/system.md"),
                project_root=root,
                ontology=ontology,
            )
            add_node(
                nodes,
                KnowledgeNode(
                    "N2",
                    "document",
                    "New spec",
                    "docs/specifications/system.md",
                    supersedes="N1",
                ),
                project_root=root,
                ontology=ontology,
            )
            with self.assertRaisesRegex(KnowledgeError, "effective"):
                add_edge(
                    edges,
                    KnowledgeEdge(
                        "E1", "N1", "N2", "defined_by", "docs/specifications/system.md"
                    ),
                    nodes_path=nodes,
                    project_root=root,
                    ontology=ontology,
                )
            with self.assertRaisesRegex(KnowledgeError, "ontology"):
                add_node(
                    nodes,
                    KnowledgeNode("N3", "unknown", "Bad", "docs/specifications/system.md"),
                    project_root=root,
                    ontology=ontology,
                )
            edges.write_text(
                json.dumps(
                    KnowledgeEdge(
                        "E-STALE",
                        "N1",
                        "N2",
                        "defined_by",
                        "docs/specifications/system.md",
                    ).to_dict()
                )
                + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(KnowledgeError, "non-effective"):
                effective_graph(nodes, edges)

    def test_complete_index_is_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "spec.md"
            source.write_text("canonical", encoding="utf-8")
            nodes = root / "nodes.jsonl"
            edges = root / "edges.jsonl"
            add_node(nodes, KnowledgeNode("N1", "document", "Spec", str(source)))
            add_node(nodes, KnowledgeNode("N2", "component", "Core", str(source)))
            add_edge(
                edges,
                KnowledgeEdge("E1", "N2", "N1", "defined_by", str(source)),
                nodes_path=nodes,
            )
            first = rebuild_indexes(nodes, edges, root / "a.json").read_bytes()
            second = rebuild_indexes(nodes, edges, root / "b.json").read_bytes()
            self.assertEqual(first, second)
            payload = json.loads(first)
            for field in (
                "store_digest",
                "edge_ids_by_relation",
                "node_ids_by_source",
                "edge_ids_by_source",
                "incoming_edge_ids",
                "outgoing_edge_ids",
            ):
                self.assertIn(field, payload)
            active_nodes, active_edges = effective_graph(nodes, edges)
            self.assertEqual(len(active_nodes), 2)
            self.assertEqual(len(active_edges), 1)


if __name__ == "__main__":
    unittest.main()
