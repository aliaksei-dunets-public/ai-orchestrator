from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from .approvals import create_memory_approval
from .memory import (
    APPROVALS_PATH,
    _atomic_append,
    create_proposal,
    disable_entry,
    effective_entries,
    load_approvals,
    load_proposals,
    promote_proposal,
    supersede_entry,
)


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--root", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="memory_command", required=True)
    propose = commands.add_parser("propose")
    propose.add_argument("--kind", required=True, choices=("observation", "decision", "lesson", "instruction"))
    propose.add_argument("--content", required=True)
    propose.add_argument("--source", required=True)
    propose.add_argument("--confidence", required=True, type=float)
    propose.add_argument("--supersedes")
    approve = commands.add_parser("approve")
    approve.add_argument("--proposal-hash", required=True)
    approve.add_argument("--source-digest", required=True)
    approve.add_argument("--approved-by", required=True)
    approve.add_argument("--decision", choices=("approve", "reject"), required=True)
    promote = commands.add_parser("promote")
    promote.add_argument("--proposal-hash", required=True)
    promote.add_argument("--approval-hash")
    disable = commands.add_parser("disable")
    disable.add_argument("--id", required=True)
    disable.add_argument("--reason", required=True)
    supersede = commands.add_parser("supersede")
    supersede.add_argument("--id", required=True)
    supersede.add_argument("--replacement-id", required=True)
    supersede.add_argument("--reason", required=True)
    commands.add_parser("list")


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.root.resolve()
    if args.memory_command == "propose":
        return create_proposal(
            root,
            kind=args.kind,
            content=args.content,
            source=args.source,
            confidence=args.confidence,
            supersedes=args.supersedes,
        ).to_dict()
    if args.memory_command == "approve":
        approval = create_memory_approval(
            proposal_hash=args.proposal_hash,
            source_digest=args.source_digest,
            approved_by=args.approved_by,
            decision=args.decision,
        )
        _atomic_append(root / APPROVALS_PATH, approval.to_dict())
        return approval.to_dict()
    if args.memory_command == "promote":
        proposal = next(
            (item for item in load_proposals(root) if item.proposal_hash == args.proposal_hash),
            None,
        )
        if proposal is None:
            raise ValueError("proposal not found")
        approval = None
        if args.approval_hash:
            approval = next(
                (item for item in load_approvals(root) if item.approval_hash == args.approval_hash),
                None,
            )
            if approval is None:
                raise ValueError("approval not found")
        return promote_proposal(root, proposal, approval=approval).to_dict()
    if args.memory_command == "disable":
        return disable_entry(root, args.id, reason=args.reason).to_dict()
    if args.memory_command == "supersede":
        return supersede_entry(
            root, args.id, args.replacement_id, reason=args.reason
        ).to_dict()
    return {
        "schema_version": 1,
        "entries": [entry.to_dict() for entry in effective_entries(root)],
    }
