from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal, Protocol, Sequence

from .review import ReviewFinding
from .session_report import redact
from .telemetry import RunTelemetry, TelemetryEvent, TelemetrySink, TokenUsage


ReviewerMode = Literal["native", "same-agent-clean-context", "not-admitted"]
TaskMode = Literal["quick", "standard", "deep"]
RiskLevel = Literal["low", "medium", "high", "critical"]
REVIEW_BOUNDARIES = frozenset(
    {
        "security",
        "data",
        "financial",
        "concurrency",
        "authentication",
        "migration",
        "persistence",
        "public-api",
        "irreversible",
    }
)
MAX_LIST_ITEMS = 32
MAX_FIELD_CHARS = 4096
MAX_ITEM_CHARS = 1024
MAX_FINDINGS = 32
TASK_ID_RE = re.compile(r"TASK-[0-9]{4,}")
SENSITIVE_INPUT_RE = re.compile(
    r"(?i)(?:api[_-]?key|password|secret|token|private[_-]?key)\s*[:=]"
)


def _bounded_text(value: str, *, name: str, limit: int = MAX_FIELD_CHARS) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if len(value) > limit:
        raise ValueError(f"{name} exceeds {limit} characters")
    if redact(value) != value or SENSITIVE_INPUT_RE.search(value):
        raise ValueError(f"{name} contains credential-like content")
    return value.strip()


def _bounded_list(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > MAX_LIST_ITEMS:
        raise ValueError(f"{name} exceeds {MAX_LIST_ITEMS} items")
    result: list[str] = []
    for value in values:
        item = _bounded_text(value, name=name, limit=MAX_ITEM_CHARS)
        result.append(item)
    return tuple(result)


def _safe_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if (
        not normalized
        or path.is_absolute()
        or ":" in path.parts[0]
        or ".." in path.parts
    ):
        raise ValueError("changed_paths must contain project-relative paths")
    return path.as_posix()


@dataclass(frozen=True)
class ReviewerAdmission:
    admitted: bool
    reason: str
    max_dispatches: int = 1

    def __post_init__(self) -> None:
        if not self.reason.strip() or self.max_dispatches != 1:
            raise ValueError("reviewer admission must describe exactly one bounded dispatch")


def admit_independent_reviewer(
    *,
    task_mode: str,
    risk: str,
    security_sensitive: bool = False,
    boundaries: Sequence[str] = (),
    challenged_blocking: bool = False,
    dispatch_count: int = 0,
) -> ReviewerAdmission:
    if task_mode not in {"quick", "standard", "deep"}:
        raise ValueError(f"unsupported task mode: {task_mode}")
    if risk not in {"low", "medium", "high", "critical"}:
        raise ValueError(f"unsupported risk level: {risk}")
    if dispatch_count < 0:
        raise ValueError("dispatch_count must be non-negative")
    normalized_boundaries = {str(item).strip().lower() for item in boundaries}
    unknown = normalized_boundaries - REVIEW_BOUNDARIES
    if unknown:
        raise ValueError(f"unsupported review boundaries: {sorted(unknown)}")
    if dispatch_count >= 1:
        return ReviewerAdmission(False, "independent reviewer dispatch limit reached")
    reasons: list[str] = []
    if task_mode == "deep":
        reasons.append("deep task")
    if risk in {"high", "critical"}:
        reasons.append(f"{risk} risk")
    if security_sensitive:
        reasons.append("security-sensitive task")
    reasons.extend(sorted(normalized_boundaries & REVIEW_BOUNDARIES))
    if challenged_blocking:
        reasons.append("challenged blocking finding")
    if not reasons:
        return ReviewerAdmission(False, "task does not meet independent reviewer admission criteria")
    return ReviewerAdmission(True, f"admitted for {', '.join(reasons)}")


@dataclass(frozen=True)
class ReviewerRequest:
    task_id: str
    task_mode: TaskMode
    risk: RiskLevel
    acceptance_criteria: tuple[str, ...]
    context_pack: str
    changed_paths: tuple[str, ...]
    diff_summary: str
    test_evidence: tuple[str, ...]
    read_only: bool = True
    write_authority: Literal["none"] = "none"

    def __post_init__(self) -> None:
        if not TASK_ID_RE.fullmatch(self.task_id):
            raise ValueError("task_id must match TASK-NNNN")
        if self.task_mode not in {"quick", "standard", "deep"}:
            raise ValueError(f"unsupported task mode: {self.task_mode}")
        if self.risk not in {"low", "medium", "high", "critical"}:
            raise ValueError(f"unsupported risk level: {self.risk}")
        if not self.read_only or self.write_authority != "none":
            raise ValueError("independent reviewer requests must be read-only")
        object.__setattr__(self, "acceptance_criteria", _bounded_list(self.acceptance_criteria, name="acceptance_criteria"))
        object.__setattr__(self, "test_evidence", _bounded_list(self.test_evidence, name="test_evidence"))
        object.__setattr__(self, "context_pack", _bounded_text(self.context_pack, name="context_pack"))
        object.__setattr__(self, "diff_summary", _bounded_text(self.diff_summary, name="diff_summary"))
        paths = tuple(_safe_relative_path(value) for value in self.changed_paths)
        if len(paths) > MAX_LIST_ITEMS:
            raise ValueError(f"changed_paths exceeds {MAX_LIST_ITEMS} items")
        object.__setattr__(self, "changed_paths", tuple(dict.fromkeys(paths)))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "task_id": self.task_id,
            "task_mode": self.task_mode,
            "risk": self.risk,
            "acceptance_criteria": list(self.acceptance_criteria),
            "context_pack": self.context_pack,
            "changed_paths": list(self.changed_paths),
            "diff_summary": self.diff_summary,
            "test_evidence": list(self.test_evidence),
            "read_only": self.read_only,
            "write_authority": self.write_authority,
        }


@dataclass(frozen=True)
class IndependentReviewerResult:
    findings: tuple[ReviewFinding, ...] = ()
    evidence: tuple[str, ...] = ()
    usage: TokenUsage = TokenUsage()

    def __post_init__(self) -> None:
        if len(self.findings) > MAX_FINDINGS or not all(
            isinstance(item, ReviewFinding) for item in self.findings
        ):
            raise ValueError("reviewer findings are invalid or exceed the bound")
        for finding in self.findings:
            for field in (finding.evidence, finding.impact, finding.remediation):
                if redact(field) != field or SENSITIVE_INPUT_RE.search(field):
                    raise ValueError("reviewer findings contain credential-like content")
        object.__setattr__(self, "evidence", _bounded_list(self.evidence, name="evidence"))

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "findings": [item.to_dict() for item in self.findings],
            "evidence": list(self.evidence),
            "usage": self.usage.to_dict(),
        }


class IndependentReviewerAdapter(Protocol):
    def review(self, request: ReviewerRequest) -> IndependentReviewerResult: ...


@dataclass(frozen=True)
class ReviewerDispatch:
    mode: ReviewerMode
    admission: ReviewerAdmission
    result: IndependentReviewerResult
    fallback_reason: str | None = None
    handoffs: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "mode": self.mode,
            "admitted": self.admission.admitted,
            "admission_reason": self.admission.reason,
            "fallback_reason": self.fallback_reason,
            "handoffs": self.handoffs,
            "result": self.result.to_dict(),
        }


def _emit_telemetry(
    sink: TelemetrySink | None,
    *,
    run_id: str,
    status: str,
    handoffs: int,
    usage: TokenUsage,
) -> None:
    if sink is None:
        return
    try:
        sink.emit(
            TelemetryEvent(
                event="run_completed",
                run_id=run_id,
                status=status,
                metrics=RunTelemetry(agent_handoffs=handoffs, usage=usage),
            )
        )
    except Exception:
        return


def dispatch_independent_reviewer(
    request: ReviewerRequest,
    *,
    capability_mode: str,
    capability_adapter: str | None,
    adapter: IndependentReviewerAdapter | None,
    security_sensitive: bool = False,
    boundaries: Sequence[str] = (),
    challenged_blocking: bool = False,
    dispatch_count: int = 0,
    telemetry_sink: TelemetrySink | None = None,
    run_id: str = "independent-reviewer",
) -> ReviewerDispatch:
    admission = admit_independent_reviewer(
        task_mode=request.task_mode,
        risk=request.risk,
        security_sensitive=security_sensitive,
        boundaries=boundaries,
        challenged_blocking=challenged_blocking,
        dispatch_count=dispatch_count,
    )
    if not admission.admitted:
        return ReviewerDispatch("not-admitted", admission, IndependentReviewerResult())
    if capability_mode == "native" and capability_adapter and adapter is not None:
        try:
            result = adapter.review(request)
            if not isinstance(result, IndependentReviewerResult):
                raise TypeError("native adapter returned an invalid result")
            _emit_telemetry(
                telemetry_sink,
                run_id=run_id,
                status="completed",
                handoffs=1,
                usage=result.usage,
            )
            return ReviewerDispatch("native", admission, result, handoffs=1)
        except Exception:
            pass
    reason = "native reviewer capability unavailable; clean-context fallback required"
    _emit_telemetry(
        telemetry_sink,
        run_id=run_id,
        status="fallback",
        handoffs=0,
        usage=TokenUsage(),
    )
    return ReviewerDispatch(
        "same-agent-clean-context",
        admission,
        IndependentReviewerResult(),
        fallback_reason=reason,
    )
