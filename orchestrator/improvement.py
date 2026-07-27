from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from .audit import AuditFinding


class ImprovementError(ValueError):
    pass


@dataclass(frozen=True)
class ImprovementProposal:
    finding_fingerprint: str
    baseline_revision: int
    proposed_diff: str
    proposed_diff_hash: str
    rollback_instructions: str
    regression_test: str
    requires_task_manager: bool = True
    requires_approval: bool = True

    def to_dict(self) -> dict[str, object]:
        return {"schema_version": 1, **asdict(self)}


def design_improvement(
    finding: AuditFinding,
    *,
    baseline_revision: int,
    proposed_diff: str,
    rollback_instructions: str,
    regression_test: str,
) -> ImprovementProposal:
    if baseline_revision < 1:
        raise ImprovementError("baseline revision must be positive")
    if not proposed_diff.strip():
        raise ImprovementError("proposal requires an exact diff")
    if not rollback_instructions.strip():
        raise ImprovementError("rollback instructions are required")
    if not regression_test.strip():
        raise ImprovementError("a regression test is required")
    return ImprovementProposal(
        finding.fingerprint,
        baseline_revision,
        proposed_diff,
        hashlib.sha256(proposed_diff.encode("utf-8")).hexdigest(),
        rollback_instructions,
        regression_test,
    )


def may_apply_improvement(
    proposal: ImprovementProposal,
    *,
    registered_task: bool,
    approved_diff_hash: str | None,
    approved_revision: int | None,
) -> bool:
    return (
        registered_task
        and approved_diff_hash == proposal.proposed_diff_hash
        and approved_revision == proposal.baseline_revision
    )
