from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.memory_knowledge_migration import (
    MigrationError,
    apply_migration,
    plan_migration,
    rollback_migration,
)


class MemoryKnowledgeMigrationTests(unittest.TestCase):
    def test_preview_apply_and_rollback_preserve_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "docs/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("canonical", encoding="utf-8")
            legacy = root / ".orchestrator/memory.jsonl"
            legacy.parent.mkdir()
            record = {
                "schema_version": 1,
                "id": "MEM-0001",
                "kind": "decision",
                "content": "Use JSONL.",
                "source": str(source),
                "source_digest": __import__("hashlib").sha256(source.read_bytes()).hexdigest(),
                "confidence": 1,
                "timestamp": "2026-01-01T00:00:00+00:00",
                "supersedes": None,
                "enabled": True,
            }
            legacy.write_text(json.dumps(record) + "\n", encoding="utf-8")
            plan = plan_migration(root)
            self.assertEqual(plan.record_count, 1)
            result = apply_migration(root, plan, approved_plan_hash=plan.plan_hash)
            self.assertEqual(result["status"], "completed")
            canonical = root / ".orchestrator/memory/entries.jsonl"
            migrated = json.loads(canonical.read_text(encoding="utf-8"))
            self.assertEqual(migrated["content"], record["content"])
            self.assertEqual(migrated["source"], "docs/specifications/system.md")
            self.assertTrue(rollback_migration(root, plan.plan_hash))
            self.assertFalse(canonical.exists())

    def test_stale_plan_is_rejected_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / ".orchestrator/memory.jsonl"
            legacy.parent.mkdir()
            legacy.write_text("", encoding="utf-8")
            plan = plan_migration(root)
            legacy.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(MigrationError, "stale"):
                apply_migration(root, plan, approved_plan_hash=plan.plan_hash)


if __name__ == "__main__":
    unittest.main()
