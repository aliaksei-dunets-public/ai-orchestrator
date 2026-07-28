from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import shutil

from orchestrator.knowledge import KnowledgeEdge, KnowledgeNode, add_edge, add_node
from orchestrator.memory import create_proposal, disable_entry, promote_proposal
from orchestrator.retrieval import build_context_pack, serialize_context_pack


ROOT = Path(__file__).resolve().parents[2]


class RetrievalTests(unittest.TestCase):
    def test_stable_scoring_graph_expansion_and_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/task.md"
            source.parent.mkdir(parents=True)
            source.write_text("Task Manager owns task state.", encoding="utf-8")
            promote_proposal(
                root,
                create_proposal(
                    root,
                    kind="decision",
                    content="Task Manager uses JSON.",
                    source=source,
                    confidence=1,
                ),
            )
            nodes = root / ".orchestrator/knowledge/nodes.jsonl"
            edges = root / ".orchestrator/knowledge/edges.jsonl"
            add_node(nodes, KnowledgeNode("N1", "component", "Task Manager", str(source)))
            add_node(nodes, KnowledgeNode("N2", "document", "Task specification", str(source)))
            add_edge(
                edges,
                KnowledgeEdge("E1", "N1", "N2", "defined_by", str(source)),
                nodes_path=nodes,
            )
            first = build_context_pack(
                root, task_context="Change Task Manager", budget_chars=1200, graph_depth=1
            )
            second = build_context_pack(
                root, task_context="Change Task Manager", budget_chars=1200, graph_depth=1
            )
            self.assertEqual(serialize_context_pack(first), serialize_context_pack(second))
            self.assertLessEqual(first["used_chars"], 1200)
            self.assertEqual([item["id"] for item in first["memory"]], ["MEM-0001"])
            self.assertEqual({item["id"] for item in first["nodes"]}, {"N1", "N2"})
            self.assertEqual([item["id"] for item in first["edges"]], ["E1"])

    def test_disabled_stale_and_irrelevant_records_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical", encoding="utf-8")
            entry = promote_proposal(
                root,
                create_proposal(
                    root,
                    kind="lesson",
                    content="Use bounded retrieval.",
                    source=source,
                    confidence=1,
                ),
            )
            disable_entry(root, entry.id, reason="obsolete")
            empty = build_context_pack(root, terms=["unrelated"], budget_chars=256)
            self.assertEqual(empty["memory"], [])
            self.assertEqual(empty["nodes"], [])
            self.assertEqual(empty["edges"], [])

    def test_russian_graph_provenance_is_excluded_from_context_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy(ROOT / "config/language-policy.json", root / "config.json")
            (root / "config").mkdir()
            (root / "config.json").replace(root / "config/language-policy.json")
            source = root / "docs/guides/guide-ru.md"
            source.parent.mkdir(parents=True)
            source.write_text(
                "---\nlanguage: ru\ntranslation_of: docs/guides/guide.md\n---\n# \u0420\u0443\u0441\u0441\u043a\u0438\u0439\n",
                encoding="utf-8",
            )
            nodes = root / ".orchestrator/knowledge/nodes.jsonl"
            add_node(nodes, KnowledgeNode("RU1", "document", "Russian guide", str(source)))
            pack = build_context_pack(root, terms=["guide"], budget_chars=512)
            self.assertEqual(pack["nodes"], [])


if __name__ == "__main__":
    unittest.main()
