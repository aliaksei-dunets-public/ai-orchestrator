from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.health import run_health_checks


class MemoryKnowledgeHealthTests(unittest.TestCase):
    def _layout(self, root: Path) -> None:
        for relative in (
            ".orchestrator/memory/entries.jsonl",
            ".orchestrator/memory/events.jsonl",
            ".orchestrator/memory/approvals.jsonl",
            ".orchestrator/knowledge/nodes.jsonl",
            ".orchestrator/knowledge/edges.jsonl",
        ):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")
        ontology = root / ".orchestrator/knowledge/ontology.json"
        ontology.write_text(
            '{"schema_version":1,"immutable":false,"node_kinds":[],"relations":[]}\n',
            encoding="utf-8",
        )
        config = root / "config"
        config.mkdir()
        core = Path(__file__).resolve().parents[2] / "config/knowledge-ontology.json"
        (config / "knowledge-ontology.json").write_bytes(core.read_bytes())
        (root / ".gitignore").write_text(
            ".orchestrator/memory/proposals/\n"
            ".orchestrator/knowledge/indexes/\n"
            ".orchestrator/migrations/backups/\n",
            encoding="utf-8",
        )

    def test_corrupt_jsonl_and_git_policy_are_reported_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._layout(root)
            (root / ".orchestrator/memory/entries.jsonl").write_text("{broken\n", encoding="utf-8")
            (root / ".gitignore").write_text(".orchestrator/\n", encoding="utf-8")
            report = run_health_checks(root)
            codes = {item.code for item in report.findings}
            self.assertIn("MEMORY_KNOWLEDGE_INVALID_JSONL", codes)
            self.assertIn("MEMORY_KNOWLEDGE_GIT_POLICY", codes)

    def test_stale_index_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._layout(root)
            index = root / ".orchestrator/knowledge/indexes/index.json"
            index.parent.mkdir(parents=True)
            index.write_text("{}\n", encoding="utf-8")
            report = run_health_checks(root)
            self.assertTrue(any(item.code == "KNOWLEDGE_INDEX_STALE" for item in report.findings))


if __name__ == "__main__":
    unittest.main()
