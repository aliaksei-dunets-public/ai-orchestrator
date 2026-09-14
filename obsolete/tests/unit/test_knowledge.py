from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.knowledge import (
    KnowledgeEdge,
    KnowledgeError,
    KnowledgeNode,
    add_edge,
    add_node,
    rebuild_indexes,
)


class KnowledgeTests(unittest.TestCase):
    def test_sources_edges_conflicts_and_reproducible_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "spec.md"
            source.write_text("canonical", encoding="utf-8")
            nodes = root / "nodes.jsonl"
            edges = root / "edges.jsonl"
            add_node(nodes, KnowledgeNode("N2", "component", "Task Manager", str(source)))
            add_node(nodes, KnowledgeNode("N1", "document", "Specification", str(source)))
            add_edge(
                edges,
                KnowledgeEdge("E1", "N2", "N1", "defined_by", str(source)),
                nodes_path=nodes,
            )
            with self.assertRaisesRegex(KnowledgeError, "Conflicting"):
                add_node(nodes, KnowledgeNode("N1", "document", "Other label", str(source)))
            with self.assertRaisesRegex(KnowledgeError, "unknown node"):
                add_edge(
                    edges,
                    KnowledgeEdge("E2", "N2", "MISSING", "uses", str(source)),
                    nodes_path=nodes,
                )
            first = rebuild_indexes(nodes, edges, root / "index-a.json").read_bytes()
            second = rebuild_indexes(nodes, edges, root / "index-b.json").read_bytes()
            self.assertEqual(first, second)

    def test_missing_provenance_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(KnowledgeError, "does not exist"):
                add_node(root / "nodes.jsonl", KnowledgeNode("N1", "x", "x", str(root / "missing")))
