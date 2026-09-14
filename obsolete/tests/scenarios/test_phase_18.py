from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.knowledge import KnowledgeEdge, KnowledgeNode, add_edge, add_node, rebuild_indexes


class KnowledgeGraphRebuildScenarioTests(unittest.TestCase):
    def test_canonical_jsonl_rebuild_is_byte_for_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "specification.md"
            source.write_text("canonical source", encoding="utf-8")
            nodes = root / "nodes.jsonl"
            edges = root / "edges.jsonl"
            add_node(nodes, KnowledgeNode("NODE-B", "component", "Runner", str(source)))
            add_node(nodes, KnowledgeNode("NODE-A", "contract", "Task Context", str(source)))
            add_edge(
                edges,
                KnowledgeEdge("EDGE-1", "NODE-B", "NODE-A", "consumes", str(source)),
                nodes_path=nodes,
            )
            first = rebuild_indexes(nodes, edges, root / "first.json").read_bytes()
            second = rebuild_indexes(nodes, edges, root / "second.json").read_bytes()
            self.assertEqual(first, second)
            self.assertIn(b"NODE-A", first)
