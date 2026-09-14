from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.memory import create_proposal, promote_proposal
from orchestrator.retrieval import build_context_pack


class ContextRetrievalScenarioTests(unittest.TestCase):
    def test_empty_store_is_valid_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = build_context_pack(
                Path(temporary),
                task_context="Implement health command",
                affected_paths=["orchestrator/health.py"],
                budget_chars=512,
            )
            self.assertEqual(pack["memory"], [])
            self.assertEqual(pack["nodes"], [])
            self.assertEqual(pack["edges"], [])
            self.assertEqual(pack["used_chars"], 0)

    def test_stale_source_is_not_returned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("v1", encoding="utf-8")
            promote_proposal(
                root,
                create_proposal(
                    root,
                    kind="observation",
                    content="Health uses stable codes.",
                    source=source,
                    confidence=1,
                ),
            )
            source.write_text("v2", encoding="utf-8")
            pack = build_context_pack(root, terms=["health"], budget_chars=512)
            self.assertEqual(pack["memory"], [])


if __name__ == "__main__":
    unittest.main()
