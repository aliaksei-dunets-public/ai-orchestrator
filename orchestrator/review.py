from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Mapping, Sequence


CriterionStatus = Literal["satisfied", "failed", "unverified"]
Severity = Literal["advisory", "low", "medium", "high", "critical"]


@dataclass(frozen=True)
class CriterionReview:
    criterion: str
    status: CriterionStatus
    evidence: str


@dataclass(frozen=True)
class ReviewFinding:
    code: str
    severity: Severity
    file: str
    evidence: str
    impact: str
    remediation: str
    blocking: bool = False

    def __post_init__(self) -> None:
        values = (self.code, self.file, self.evidence, self.impact, self.remediation)
        if not all(value.strip() for value in values):
            raise ValueError("Every finding requires code, file, evidence, impact, and remediation")


@dataclass(frozen=True)
class ReviewResult:
    kind: str
    verdict: Literal["approved", "rework", "blocked"]
    criteria: tuple[CriterionReview, ...]
    findings: tuple[ReviewFinding, ...]
    reviewer_mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "kind": self.kind,
            "verdict": self.verdict,
            "criteria": [asdict(item) for item in self.criteria],
            "findings": [asdict(item) for item in self.findings],
            "reviewer_mode": self.reviewer_mode,
        }


def _in_scope(path: str, allowed: Sequence[str]) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return any(
        normalized == item.replace("\\", "/").lstrip("./")
        or normalized.startswith(item.replace("\\", "/").rstrip("/") + "/")
        for item in allowed
    )


def task_review(
    *,
    acceptance_criteria: Sequence[str],
    evidence: Mapping[str, bool | None],
    in_scope_paths: Sequence[str],
    changed_paths: Sequence[str],
    reviewer_mode: str = "isolated",
) -> ReviewResult:
    criteria: list[CriterionReview] = []
    for criterion in acceptance_criteria:
        value = evidence.get(criterion)
        status: CriterionStatus = "satisfied" if value is True else "failed" if value is False else "unverified"
        detail = "verified evidence" if value is True else "negative evidence" if value is False else "evidence missing"
        criteria.append(CriterionReview(criterion, status, detail))

    findings: list[ReviewFinding] = []
    for path in changed_paths:
        if not _in_scope(path, in_scope_paths):
            findings.append(
                ReviewFinding(
                    code="SCOPE_CREEP",
                    severity="high",
                    file=path,
                    evidence=f"{path} is absent from the approved scope",
                    impact="The implementation changes an unapproved surface.",
                    remediation="Revert the change or obtain a new baseline approval.",
                    blocking=True,
                )
            )
    for item in criteria:
        if item.status != "satisfied":
            findings.append(
                ReviewFinding(
                    code="ACCEPTANCE_NOT_SATISFIED",
                    severity="high",
                    file="Task Context",
                    evidence=f"{item.criterion}: {item.evidence}",
                    impact="Completion cannot be demonstrated.",
                    remediation="Provide passing evidence or return to implementation.",
                    blocking=True,
                )
            )
    verdict = "rework" if any(item.blocking for item in findings) else "approved"
    return ReviewResult("task", verdict, tuple(criteria), tuple(findings), reviewer_mode)


def code_review(
    findings: Sequence[ReviewFinding],
    *,
    isolated_reviewer_available: bool,
) -> ReviewResult:
    mode = "isolated" if isolated_reviewer_available else "same-agent-clean-context"
    verdict = "rework" if any(finding.blocking for finding in findings) else "approved"
    return ReviewResult("code", verdict, (), tuple(findings), mode)
