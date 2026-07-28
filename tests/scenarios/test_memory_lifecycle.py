from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.approvals import create_memory_approval
from orchestrator.memory import (
    MemoryError,
    create_proposal,
    disable_entry,
    effective_entries,
    promote_proposal,
    supersede_entry,
)


class MemoryLifecycleTests(unittest.TestCase):
    def _project(self, root: Path) -> tuple[Path, Path]:
        spec = root / "docs/specifications/system.md"
        report = root / "reports/session.md"
        spec.parent.mkdir(parents=True)
        report.parent.mkdir(parents=True)
        spec.write_text("canonical", encoding="utf-8")
        report.write_text("observed", encoding="utf-8")
        return spec, report

    def test_authoritative_observation_promotes_but_instruction_requires_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec, _ = self._project(root)
            proposal = create_proposal(
                root, kind="observation", content="Use JSONL.", source=spec, confidence=1
            )
            entry = promote_proposal(root, proposal)
            self.assertEqual(entry.source, "docs/specifications/system.md")
            instruction = create_proposal(
                root, kind="instruction", content="Always run checks.", source=spec, confidence=1
            )
            with self.assertRaisesRegex(MemoryError, "approval"):
                promote_proposal(root, instruction)

    def test_non_authoritative_approval_is_bound_to_hashes_and_stale_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, report = self._project(root)
            proposal = create_proposal(
                root, kind="lesson", content="Retry once.", source=report, confidence=0.8
            )
            with self.assertRaisesRegex(MemoryError, "approval"):
                promote_proposal(root, proposal)
            approval = create_memory_approval(
                proposal_hash=proposal.proposal_hash,
                source_digest=proposal.source_digest,
                approved_by="user",
                decision="approve",
            )
            promote_proposal(root, proposal, approval=approval)
            changed = create_proposal(
                root, kind="lesson", content="Validate first.", source=report, confidence=0.9
            )
            report.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(MemoryError, "stale"):
                promote_proposal(root, changed, approval=approval)

    def test_disable_and_supersede_are_append_only_effective_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec, _ = self._project(root)
            first = promote_proposal(
                root,
                create_proposal(root, kind="decision", content="A", source=spec, confidence=1),
            )
            second = promote_proposal(
                root,
                create_proposal(
                    root,
                    kind="decision",
                    content="B",
                    source=spec,
                    confidence=1,
                    supersedes=first.id,
                ),
            )
            supersede_entry(root, first.id, second.id, reason="updated")
            self.assertEqual([item.id for item in effective_entries(root)], [second.id])
            disable_entry(root, second.id, reason="invalidated")
            self.assertEqual(effective_entries(root), [])
            self.assertEqual(
                len((root / ".orchestrator/memory/events.jsonl").read_text().splitlines()),
                4,
            )
            before = (root / ".orchestrator/memory/events.jsonl").read_bytes()
            with self.assertRaisesRegex(MemoryError, "cycle"):
                supersede_entry(root, second.id, first.id, reason="bad cycle")
            self.assertEqual(
                (root / ".orchestrator/memory/events.jsonl").read_bytes(),
                before,
            )


if __name__ == "__main__":
    unittest.main()
