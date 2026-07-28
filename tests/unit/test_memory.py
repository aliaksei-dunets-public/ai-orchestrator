from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.memory import MemoryError, append_entry, load_entries, source_digest


class MemoryTests(unittest.TestCase):
    def test_project_aware_append_rejects_escape_before_source_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            outside = root.parent / "outside.md"
            outside.write_text("private", encoding="utf-8")
            with self.assertRaisesRegex(MemoryError, "outside"):
                append_entry(
                    root / ".orchestrator/memory/entries.jsonl",
                    kind="observation",
                    content="Do not read outside.",
                    source=outside,
                    confidence=1,
                    project_root=root,
                )
            self.assertFalse((root / ".orchestrator/memory/entries.jsonl").exists())

    def test_entry_has_source_timestamp_and_observation_is_not_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "session.md"
            source.write_text("confirmed observation", encoding="utf-8")
            store = root / "memory.jsonl"
            entry = append_entry(
                store, kind="observation", content="CLI uses JSON output.", source=source, confidence=0.9
            )
            self.assertEqual(entry.source, str(source.resolve()))
            self.assertTrue(entry.timestamp)
            self.assertEqual(entry.kind, "observation")
            with self.assertRaisesRegex(MemoryError, "automatically"):
                append_entry(
                    store, kind="instruction", content="Always change CLI.", source=source, confidence=1
                )

    def test_duplicate_supersede_secret_and_stale_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.md"
            source.write_text("v1", encoding="utf-8")
            digest = source_digest(source)
            store = root / "memory.jsonl"
            first = append_entry(
                store, kind="decision", content="Use JSONL.", source=source, confidence=1
            )
            with self.assertRaisesRegex(MemoryError, "duplicate"):
                append_entry(store, kind="decision", content="Use JSONL.", source=source, confidence=1)
            second = append_entry(
                store,
                kind="decision",
                content="Use canonical JSONL.",
                source=source,
                confidence=1,
                supersedes=first.id,
            )
            self.assertEqual(second.supersedes, first.id)
            with self.assertRaisesRegex(MemoryError, "secret"):
                append_entry(
                    store, kind="lesson", content="api_key=supersecret", source=source, confidence=1
                )
            source.write_text("v2", encoding="utf-8")
            with self.assertRaisesRegex(MemoryError, "stale"):
                append_entry(
                    store,
                    kind="lesson",
                    content="Source changed.",
                    source=source,
                    confidence=0.5,
                    expected_source_digest=digest,
                )
            self.assertEqual(len(load_entries(store)), 2)
