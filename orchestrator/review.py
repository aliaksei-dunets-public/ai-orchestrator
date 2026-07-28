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
    reviewer_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = {
            "schema_version": 1,
            "kind": self.kind,
            "verdict": self.verdict,
            "criteria": [asdict(item) for item in self.criteria],
            "findings": [asdict(item) for item in self.findings],
            "reviewer_mode": self.reviewer_mode,
        }
        if self.reviewer_reason is not None:
            payload["reviewer_reason"] = self.reviewer_reason
        return payload


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
    isolated_reviewer_available: bool | None = None,
    reviewer_request: object | None = None,
    reviewer_capability_mode: str | None = None,
    reviewer_capability_adapter: str | None = None,
    reviewer_adapter: object | None = None,
    reviewer_telemetry_sink: object | None = None,
    reviewer_run_id: str = "independent-reviewer",
    reviewer_security_sensitive: bool = False,
    reviewer_boundaries: Sequence[str] = (),
    reviewer_challenged_blocking: bool = False,
    reviewer_dispatch_count: int = 0,
) -> ReviewResult:
    if reviewer_request is not None:
        from .reviewer import ReviewerRequest, dispatch_independent_reviewer

        if not isinstance(reviewer_request, ReviewerRequest):
            raise TypeError("reviewer_request must be a ReviewerRequest")
        if reviewer_capability_mode is None:
            reviewer_capability_mode = "native" if isolated_reviewer_available else "fallback"
        dispatch = dispatch_independent_reviewer(
            reviewer_request,
            capability_mode=reviewer_capability_mode,
            capability_adapter=reviewer_capability_adapter,
            adapter=reviewer_adapter,
            security_sensitive=reviewer_security_sensitive,
            boundaries=reviewer_boundaries,
            challenged_blocking=reviewer_challenged_blocking,
            dispatch_count=reviewer_dispatch_count,
            telemetry_sink=reviewer_telemetry_sink,
            run_id=reviewer_run_id,
        )
        all_findings = tuple(findings) + dispatch.result.findings
        verdict = "rework" if any(finding.blocking for finding in all_findings) else "approved"
        return ReviewResult(
            "code",
            verdict,
            (),
            all_findings,
            dispatch.mode,
            dispatch.fallback_reason,
        )
    if isolated_reviewer_available is None:
        raise TypeError("isolated_reviewer_available is required without a reviewer request")
    mode = "isolated" if isolated_reviewer_available else "same-agent-clean-context"
    verdict = "rework" if any(finding.blocking for finding in findings) else "approved"
    return ReviewResult("code", verdict, (), tuple(findings), mode)
