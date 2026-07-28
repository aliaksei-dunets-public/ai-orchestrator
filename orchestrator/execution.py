from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal

from .telemetry import RunTelemetry, TelemetryEvent, TelemetrySink, TokenUsage
from .retrieval import build_context_pack


StepStatus = Literal["completed", "failed", "scope_change", "waiting_user", "blocked"]
RunStatus = Literal["in_progress", "completed", "failed", "waiting_user", "blocked"]
MAX_EVIDENCE_CHARS = 2048
MAX_EVIDENCE_REF_CHARS = 512
MAX_STEP_ATTEMPTS = 10


class ExecutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExecutionStep:
    id: str
    description: str
    max_attempts: int = 1

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.description.strip():
            raise ValueError("Execution step id and description are required")
        if not 1 <= self.max_attempts <= MAX_STEP_ATTEMPTS:
            raise ValueError(
                f"max_attempts must be between 1 and {MAX_STEP_ATTEMPTS}"
            )


@dataclass(frozen=True)
class StepOutcome:
    status: StepStatus
    evidence: str
    evidence_ref: str | None = None
    usage: TokenUsage = TokenUsage()
    tool_calls: int = 0
    agent_handoffs: int = 0

    def __post_init__(self) -> None:
        for name in ("tool_calls", "agent_handoffs"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass
class StepRecord:
    id: str
    status: StepStatus
    attempts: int
    evidence: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    duration_ms: int = 0
    tool_calls: int = 0
    agent_handoffs: int = 0
    usage: TokenUsage = field(default_factory=TokenUsage)


@dataclass
class ExecutionResult:
    status: RunStatus
    records: list[StepRecord]
    reason: str | None = None
    telemetry: RunTelemetry = field(default_factory=RunTelemetry)
    telemetry_errors: tuple[str, ...] = ()


def bound_evidence(value: str, *, limit: int = MAX_EVIDENCE_CHARS) -> str:
    evidence = value.strip()
    if not evidence:
        raise ExecutionError("Execution evidence must not be empty")
    if limit < 256:
        raise ValueError("Evidence limit must be at least 256 characters")
    if len(evidence) <= limit:
        return evidence
    digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
    marker = f"\n...[truncated chars={len(evidence)} sha256={digest}]...\n"
    tail_size = min(512, max(64, (limit - len(marker)) // 3))
    head_size = limit - len(marker) - tail_size
    return evidence[:head_size] + marker + evidence[-tail_size:]


def _bound_reference(value: str) -> str:
    reference = value.strip()
    if not reference:
        raise ExecutionError("Evidence reference must not be empty")
    if len(reference) > MAX_EVIDENCE_REF_CHARS:
        raise ExecutionError(
            f"Evidence reference exceeds {MAX_EVIDENCE_REF_CHARS} characters"
        )
    return reference


def _record_metrics(records: list[StepRecord], *, duration_ms: int) -> RunTelemetry:
    usage = TokenUsage()
    for record in records:
        usage = usage.merge(record.usage)
    attempts = sum(record.attempts for record in records)
    return RunTelemetry(
        duration_ms=duration_ms,
        attempts=attempts,
        retries=sum(max(0, record.attempts - 1) for record in records),
        tool_calls=sum(record.tool_calls for record in records),
        agent_handoffs=sum(record.agent_handoffs for record in records),
        usage=usage,
    )


def _frontmatter_revision(text: str) -> int:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ExecutionError("Task Context has no frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ExecutionError("Task Context frontmatter is not closed") from exc
    for line in lines[1:end]:
        if line.startswith("revision:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError as exc:
                raise ExecutionError("Task Context revision must be an integer") from exc
    raise ExecutionError("Task Context has no revision")


def baseline_hash(text: str) -> str:
    baseline = text.split("# Execution Record", 1)[0].rstrip() + "\n"
    return hashlib.sha256(baseline.encode("utf-8")).hexdigest()


def validate_freshness(
    context_path: Path | str,
    *,
    expected_revision: int,
    expected_baseline_hash: str,
) -> str:
    text = Path(context_path).read_text(encoding="utf-8")
    revision = _frontmatter_revision(text)
    digest = baseline_hash(text)
    if revision != expected_revision or digest != expected_baseline_hash:
        raise ExecutionError(
            "Task Context is stale: expected "
            f"revision {expected_revision}/{expected_baseline_hash}, got {revision}/{digest}"
        )
    return digest


def _load_checkpoint(path: Path) -> dict[str, StepRecord]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"Cannot read execution checkpoint: {exc}") from exc
    records: dict[str, StepRecord] = {}
    for item in payload.get("records", []):
        raw_evidence = item.get("evidence", [])
        raw_references = item.get("evidence_refs", [])
        if (
            not isinstance(raw_evidence, list)
            or len(raw_evidence) > MAX_STEP_ATTEMPTS
            or not all(isinstance(value, str) and value.strip() for value in raw_evidence)
            or not isinstance(raw_references, list)
            or len(raw_references) > MAX_STEP_ATTEMPTS
            or not all(isinstance(value, str) and value.strip() for value in raw_references)
        ):
            raise ExecutionError(f"Invalid bounded evidence in checkpoint step {item.get('id')}")
        record = StepRecord(
            id=item["id"],
            status=item["status"],
            attempts=item["attempts"],
            evidence=[bound_evidence(value) for value in raw_evidence],
            evidence_refs=[_bound_reference(value) for value in raw_references],
            duration_ms=int(item.get("duration_ms", 0)),
            tool_calls=int(item.get("tool_calls", 0)),
            agent_handoffs=int(item.get("agent_handoffs", 0)),
            usage=TokenUsage(**item.get("usage", {})),
        )
        records[record.id] = record
    return records


def _write_checkpoint(path: Path, status: RunStatus, records: list[StepRecord], reason: str | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    payload = {
        "schema_version": 1,
        "status": status,
        "reason": reason,
        "records": [asdict(record) for record in records],
    }
    data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def execute_plan(
    *,
    context_path: Path | str,
    expected_revision: int,
    expected_baseline_hash: str,
    steps: list[ExecutionStep],
    run_step: Callable[[ExecutionStep, int], StepOutcome],
    checkpoint_path: Path | str,
    telemetry_sink: TelemetrySink | None = None,
    run_id: str | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> ExecutionResult:
    validate_freshness(
        context_path,
        expected_revision=expected_revision,
        expected_baseline_hash=expected_baseline_hash,
    )
    checkpoint = Path(checkpoint_path)
    stored = _load_checkpoint(checkpoint)
    records: list[StepRecord] = []
    telemetry_errors: list[str] = []
    started = clock()
    resolved_run_id = run_id or f"{Path(context_path).stem}:{expected_baseline_hash[:12]}"

    def emit(event: TelemetryEvent) -> None:
        if telemetry_sink is None:
            return
        try:
            telemetry_sink.emit(event)
        except Exception as exc:  # observational telemetry must not corrupt execution
            telemetry_errors.append(f"{type(exc).__name__}: {exc}")

    def finish(status: RunStatus, reason: str | None = None) -> ExecutionResult:
        duration_ms = max(0, int((clock() - started) * 1000))
        metrics = _record_metrics(records, duration_ms=duration_ms)
        emit(
            TelemetryEvent(
                event="run_completed",
                run_id=resolved_run_id,
                status=status,
                metrics=metrics,
            )
        )
        return ExecutionResult(
            status,
            records,
            reason,
            telemetry=metrics,
            telemetry_errors=tuple(telemetry_errors),
        )

    for step in steps:
        previous = stored.get(step.id)
        if previous and previous.status == "completed":
            if not previous.evidence:
                raise ExecutionError(f"Completed checkpoint for {step.id} has no evidence")
            records.append(previous)
            continue

        evidence = list(previous.evidence) if previous else []
        evidence_refs = list(previous.evidence_refs) if previous else []
        attempts = previous.attempts if previous else 0
        duration_ms = previous.duration_ms if previous else 0
        tool_calls = previous.tool_calls if previous else 0
        agent_handoffs = previous.agent_handoffs if previous else 0
        usage = previous.usage if previous else TokenUsage()
        outcome: StepOutcome | None = None
        while attempts < step.max_attempts:
            attempts += 1
            attempt_started = clock()
            try:
                outcome = run_step(step, attempts)
            except Exception:
                attempt_duration = max(0, int((clock() - attempt_started) * 1000))
                emit(
                    TelemetryEvent(
                        event="step_attempt",
                        run_id=resolved_run_id,
                        status="error",
                        step_id=step.id,
                        attempt=attempts,
                        metrics=RunTelemetry(
                            duration_ms=attempt_duration,
                            attempts=1,
                            retries=int(attempts > 1),
                        ),
                    )
                )
                raise
            attempt_duration = max(0, int((clock() - attempt_started) * 1000))
            bounded = bound_evidence(outcome.evidence)
            evidence.append(bounded)
            if outcome.evidence_ref is not None:
                evidence_refs.append(_bound_reference(outcome.evidence_ref))
            duration_ms += attempt_duration
            tool_calls += outcome.tool_calls
            agent_handoffs += outcome.agent_handoffs
            usage = usage.merge(outcome.usage)
            emit(
                TelemetryEvent(
                    event="step_attempt",
                    run_id=resolved_run_id,
                    status=outcome.status,
                    step_id=step.id,
                    attempt=attempts,
                    metrics=RunTelemetry(
                        duration_ms=attempt_duration,
                        attempts=1,
                        retries=int(attempts > 1),
                        tool_calls=outcome.tool_calls,
                        agent_handoffs=outcome.agent_handoffs,
                        usage=outcome.usage,
                    ),
                )
            )
            if outcome.status != "failed":
                break

        if outcome is None:
            outcome = StepOutcome("failed", "Retry budget was exhausted before execution")
        record = StepRecord(
            step.id,
            outcome.status,
            attempts,
            evidence,
            evidence_refs,
            duration_ms,
            tool_calls,
            agent_handoffs,
            usage,
        )
        records.append(record)

        if outcome.status == "completed":
            _write_checkpoint(checkpoint, "in_progress", records, None)
            continue
        if outcome.status in {"scope_change", "waiting_user"}:
            reason = evidence[-1]
            _write_checkpoint(checkpoint, "waiting_user", records, reason)
            return finish("waiting_user", reason)
        if outcome.status == "blocked":
            reason = evidence[-1]
            _write_checkpoint(checkpoint, "blocked", records, reason)
            return finish("blocked", reason)

        reason = f"Step {step.id} exhausted {step.max_attempts} attempt(s)"
        _write_checkpoint(checkpoint, "failed", records, reason)
        return finish("failed", reason)

    _write_checkpoint(checkpoint, "completed", records, None)
    return finish("completed")


def retrieve_execution_context(
    project_root: Path | str,
    *,
    mode: str,
    task_context: str,
    affected_paths: list[str] | tuple[str, ...] = (),
) -> dict[str, object]:
    budgets = {"quick": 2048, "standard": 6144, "deep": 12288}
    if mode not in budgets:
        raise ExecutionError(f"Unsupported execution mode: {mode}")
    return build_context_pack(
        project_root,
        task_context=task_context,
        affected_paths=affected_paths,
        budget_chars=budgets[mode],
    )
