from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal


Decision = Literal["approved", "rejected", "waiting"]
MemoryApprovalDecision = Literal["approve", "reject"]


class ApprovalError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    question: str
    consequences: tuple[str, ...]
    safe_default: Literal["reject", "wait"]
    baseline_revision: int
    baseline_hash: str
    timeout_seconds: int | None = None

    def __post_init__(self) -> None:
        if not all((self.id.strip(), self.question.strip(), self.baseline_hash.strip())):
            raise ApprovalError("Approval id, exact question, and baseline hash are required")
        if not self.consequences:
            raise ApprovalError("Approval consequences are required")
        if self.baseline_revision < 1:
            raise ApprovalError("baseline_revision must be positive")
        if self.timeout_seconds is not None and self.timeout_seconds < 1:
            raise ApprovalError("timeout_seconds must be positive")


@dataclass(frozen=True)
class ApprovalEvidence:
    request_id: str
    decision: Decision
    baseline_revision: int
    baseline_hash: str
    answer: str
    decided_at: str

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


@dataclass(frozen=True)
class MemoryApproval:
    proposal_hash: str
    source_digest: str
    decision: MemoryApprovalDecision
    approved_by: str
    approved_at: str
    approval_hash: str

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def create_memory_approval(
    *,
    proposal_hash: str,
    source_digest: str,
    approved_by: str,
    decision: MemoryApprovalDecision,
) -> MemoryApproval:
    if len(proposal_hash) != 64 or len(source_digest) != 64:
        raise ApprovalError("memory approval requires proposal and source SHA-256 hashes")
    if not approved_by.strip():
        raise ApprovalError("memory approval actor is required")
    approved_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = {
        "proposal_hash": proposal_hash,
        "source_digest": source_digest,
        "decision": decision,
        "approved_by": approved_by,
        "approved_at": approved_at,
    }
    digest = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return MemoryApproval(**payload, approval_hash=digest)


def resolve_approval(
    request: ApprovalRequest,
    *,
    answer: Literal["approve", "reject"] | None,
    current_revision: int,
    current_baseline_hash: str,
    timed_out: bool = False,
) -> ApprovalEvidence:
    if current_revision != request.baseline_revision or current_baseline_hash != request.baseline_hash:
        raise ApprovalError("Approval request is stale for the current baseline")
    if timed_out:
        decision: Decision = "rejected" if request.safe_default == "reject" else "waiting"
        detail = f"timeout; safe default={request.safe_default}"
    elif answer == "approve":
        decision, detail = "approved", "explicit approval"
    elif answer == "reject":
        decision, detail = "rejected", "explicit rejection"
    else:
        decision, detail = "waiting", "no decision"
    return ApprovalEvidence(
        request.id,
        decision,
        request.baseline_revision,
        request.baseline_hash,
        detail,
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def evidence_is_current(evidence: ApprovalEvidence, *, revision: int, baseline_hash: str) -> bool:
    return evidence.baseline_revision == revision and evidence.baseline_hash == baseline_hash
