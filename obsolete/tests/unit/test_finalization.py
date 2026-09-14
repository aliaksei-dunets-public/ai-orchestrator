from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.approvals import create_memory_approval
from orchestrator.finalization import (
    FinalizationError,
    finalize_task,
    load_receipt,
    verify_completion_receipt,
    write_receipt,
)
from orchestrator.memory import (
    APPROVALS_PATH,
    _atomic_append,
    effective_entries,
    load_proposals,
)


class FinalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        (self.root / "config").mkdir()
        (self.root / "config/knowledge-ontology.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "immutable": True,
                    "node_kinds": ["component", "task"],
                    "relations": ["affects"],
                }
            ),
            encoding="utf-8",
        )
        (self.root / "config/documentation-map.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "rules": [
                        {
                            "path_prefixes": ["src/"],
                            "documents": ["docs/guide.md"],
                            "owner": "documentation-manager",
                            "reason": "Runtime contract changed.",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.root / "docs").mkdir()
        (self.root / "docs/guide.md").write_text("# Guide\n", encoding="utf-8")
        (self.root / "src").mkdir()
        (self.root / "src/runtime.py").write_text("VALUE = 1\n", encoding="utf-8")
        knowledge = self.root / ".orchestrator/knowledge"
        knowledge.mkdir(parents=True)
        (knowledge / "ontology.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "immutable": False,
                    "node_kinds": [],
                    "relations": [],
                }
            ),
            encoding="utf-8",
        )
        (knowledge / "nodes.jsonl").write_text("", encoding="utf-8")
        (knowledge / "edges.jsonl").write_text("", encoding="utf-8")
        memory = self.root / ".orchestrator/memory"
        memory.mkdir()
        for name in ("entries.jsonl", "events.jsonl", "approvals.jsonl"):
            (memory / name).write_text("", encoding="utf-8")
        tasks = self.root / ".orchestrator/tasks"
        (tasks / "contexts").mkdir(parents=True)
        (tasks / "checkpoints").mkdir()
        self.context = tasks / "contexts/TASK-0001.md"
        self.context.write_text(
            "---\n"
            "schema_version: 1\n"
            "id: TASK-0001\n"
            "revision: 1\n"
            "title: Finalize\n"
            "type: feature\n"
            "mode: standard\n"
            "risk: medium\n"
            "created_by: task-creation-workflow\n"
            "---\n\n"
            "# TASK-0001 — Finalize\n\n"
            "## Goal\n\nFinalize the task.\n\n"
            "# Execution Record\n\n"
            "## Completion Summary\n\nStatus: completed.\n",
            encoding="utf-8",
        )
        self.checkpoint = tasks / "checkpoints/TASK-0001.checkpoint.lock"
        self.checkpoint.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "completed",
                    "reason": None,
                    "records": [
                        {
                            "id": "implementation",
                            "status": "completed",
                            "attempts": 1,
                            "evidence": ["tests passed"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def finalize(self, **overrides: object):
        arguments: dict[str, object] = {
            "project_root": self.root,
            "task_id": "TASK-0001",
            "context_path": self.context,
            "checkpoint_path": self.checkpoint,
            "changed_paths": ["src/runtime.py", "docs/guide.md"],
            "documentation_dispositions": [
                {
                    "document": "docs/guide.md",
                    "status": "updated",
                    "reason": "",
                    "evidence_ref": "docs/guide.md",
                }
            ],
            "knowledge_proposal": {
                "schema_version": 1,
                "nodes": [],
                "edges": [],
            },
            "memory_candidates": [],
        }
        arguments.update(overrides)
        return finalize_task(**arguments)  # type: ignore[arg-type]

    def test_empty_graph_and_memory_produce_bound_ready_receipt(self) -> None:
        receipt = self.finalize()
        self.assertTrue(receipt.ready_for_completion)
        self.assertEqual(receipt.knowledge_status, "empty")
        self.assertEqual(receipt.memory_status, "completed")
        destination = self.root / ".orchestrator/tasks/finalization/TASK-0001.json"
        write_receipt(destination, receipt)
        loaded = load_receipt(destination)
        self.assertEqual(loaded, receipt)
        verify_completion_receipt(
            loaded,
            task_id="TASK-0001",
            context_path=self.context,
        )

    def test_tampered_or_stale_receipt_is_rejected(self) -> None:
        receipt = self.finalize()
        destination = self.root / "receipt.json"
        write_receipt(destination, receipt)
        payload = json.loads(destination.read_text(encoding="utf-8"))
        payload["task_id"] = "TASK-9999"
        destination.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(FinalizationError, "hash"):
            load_receipt(destination)

        write_receipt(destination, receipt)
        self.context.write_text(
            self.context.read_text(encoding="utf-8").replace(
                "Finalize the task.", "Changed baseline."
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(FinalizationError, "stale context baseline"):
            verify_completion_receipt(
                load_receipt(destination),
                task_id="TASK-0001",
                context_path=self.context,
            )

    def test_incomplete_checkpoint_blocks_finalization(self) -> None:
        payload = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        payload["status"] = "in_progress"
        self.checkpoint.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(FinalizationError, "not completed"):
            self.finalize()

    def test_changed_paths_reject_root_escape_and_ambiguous_root(self) -> None:
        for changed_path in ("../escape.py", "C:/escape.py", "."):
            with self.subTest(changed_path=changed_path):
                with self.assertRaisesRegex(FinalizationError, "project root"):
                    self.finalize(changed_paths=[changed_path])

    def test_invalid_task_id_fails_before_canonical_writes(self) -> None:
        nodes = self.root / ".orchestrator/knowledge/nodes.jsonl"
        before = nodes.read_bytes()
        with self.assertRaisesRegex(FinalizationError, "TASK-NNNN"):
            self.finalize(
                task_id="invalid",
                knowledge_proposal={
                    "schema_version": 1,
                    "nodes": [
                        {
                            "id": "runtime",
                            "kind": "component",
                            "label": "Runtime",
                            "source": "docs/guide.md",
                            "supersedes": None,
                            "enabled": True,
                        }
                    ],
                    "edges": [],
                },
            )
        self.assertEqual(nodes.read_bytes(), before)

    def test_duplicate_memory_candidates_fail_before_canonical_promotion(self) -> None:
        candidate = {
            "kind": "decision",
            "content": "Use finalization receipts.",
            "source": ".orchestrator/tasks/contexts/TASK-0001.md",
            "confidence": 1.0,
        }
        with self.assertRaisesRegex(FinalizationError, "duplicate memory candidate"):
            self.finalize(memory_candidates=[candidate, candidate])
        self.assertEqual(effective_entries(self.root), [])

    def test_authoritative_memory_is_idempotently_promoted(self) -> None:
        candidate = {
            "kind": "decision",
            "content": "Use finalization receipts.",
            "source": ".orchestrator/tasks/contexts/TASK-0001.md",
            "confidence": 1.0,
        }
        first = self.finalize(memory_candidates=[candidate])
        second = self.finalize(memory_candidates=[candidate])
        self.assertEqual(first.memory_entry_ids, second.memory_entry_ids)
        self.assertEqual(len(effective_entries(self.root)), 1)

    def test_non_authoritative_memory_waits_without_canonical_promotion(self) -> None:
        reports = self.root / "reports"
        reports.mkdir()
        (reports / "session.md").write_text("# Session\n", encoding="utf-8")
        receipt = self.finalize(
            memory_candidates=[
                {
                    "kind": "observation",
                    "content": "The session completed.",
                    "source": "reports/session.md",
                    "confidence": 0.8,
                }
            ]
        )
        self.assertFalse(receipt.ready_for_completion)
        self.assertEqual(receipt.memory_status, "waiting_user")
        self.assertEqual(len(receipt.pending_approval_hashes), 1)
        self.assertEqual(effective_entries(self.root), [])

    def test_hash_bound_approval_resumes_pending_memory(self) -> None:
        reports = self.root / "reports"
        reports.mkdir()
        (reports / "session.md").write_text("# Session\n", encoding="utf-8")
        candidate = {
            "kind": "observation",
            "content": "The session completed.",
            "source": "reports/session.md",
            "confidence": 0.8,
        }
        waiting = self.finalize(memory_candidates=[candidate])
        proposal = load_proposals(self.root)[0]
        approval = create_memory_approval(
            proposal_hash=proposal.proposal_hash,
            source_digest=proposal.source_digest,
            approved_by="test",
            decision="approve",
        )
        _atomic_append(
            self.root / APPROVALS_PATH,
            approval.to_dict(),
        )
        resumed = self.finalize(memory_candidates=[candidate])
        self.assertFalse(waiting.ready_for_completion)
        self.assertTrue(resumed.ready_for_completion)
        self.assertEqual(len(resumed.memory_entry_ids), 1)

    def test_non_empty_graph_is_applied_with_provenance(self) -> None:
        receipt = self.finalize(
            knowledge_proposal={
                "schema_version": 1,
                "nodes": [
                    {
                        "id": "runtime",
                        "kind": "component",
                        "label": "Runtime",
                        "source": "docs/guide.md",
                        "supersedes": None,
                        "enabled": True,
                    }
                ],
                "edges": [],
            }
        )
        self.assertEqual(receipt.knowledge_status, "applied")
        nodes = (self.root / ".orchestrator/knowledge/nodes.jsonl").read_text(
            encoding="utf-8"
        )
        self.assertIn('"id":"runtime"', nodes)
        self.assertTrue(
            (self.root / ".orchestrator/knowledge/indexes/index.json").is_file()
        )


if __name__ == "__main__":
    unittest.main()
