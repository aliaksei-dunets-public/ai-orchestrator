from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Literal


StepStatus = Literal["completed", "failed", "scope_change", "waiting_user", "blocked"]
RunStatus = Literal["in_progress", "completed", "failed", "waiting_user", "blocked"]


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
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")


@dataclass(frozen=True)
class StepOutcome:
    status: StepStatus
    evidence: str


@dataclass
class StepRecord:
    id: str
    status: StepStatus
    attempts: int
    evidence: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    status: RunStatus
    records: list[StepRecord]
    reason: str | None = None


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
        record = StepRecord(
            id=item["id"],
            status=item["status"],
            attempts=item["attempts"],
            evidence=list(item.get("evidence", [])),
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
) -> ExecutionResult:
    validate_freshness(
        context_path,
        expected_revision=expected_revision,
        expected_baseline_hash=expected_baseline_hash,
    )
    checkpoint = Path(checkpoint_path)
    stored = _load_checkpoint(checkpoint)
    records: list[StepRecord] = []

    for step in steps:
        previous = stored.get(step.id)
        if previous and previous.status == "completed":
            if not previous.evidence:
                raise ExecutionError(f"Completed checkpoint for {step.id} has no evidence")
            records.append(previous)
            continue

        evidence = list(previous.evidence) if previous else []
        attempts = previous.attempts if previous else 0
        outcome: StepOutcome | None = None
        while attempts < step.max_attempts:
            attempts += 1
            outcome = run_step(step, attempts)
            if not outcome.evidence.strip():
                raise ExecutionError(f"Step {step.id} returned empty evidence")
            evidence.append(outcome.evidence.strip())
            if outcome.status != "failed":
                break

        if outcome is None:
            outcome = StepOutcome("failed", "Retry budget was exhausted before execution")
        record = StepRecord(step.id, outcome.status, attempts, evidence)
        records.append(record)

        if outcome.status == "completed":
            _write_checkpoint(checkpoint, "in_progress", records, None)
            continue
        if outcome.status in {"scope_change", "waiting_user"}:
            reason = evidence[-1]
            _write_checkpoint(checkpoint, "waiting_user", records, reason)
            return ExecutionResult("waiting_user", records, reason)
        if outcome.status == "blocked":
            reason = evidence[-1]
            _write_checkpoint(checkpoint, "blocked", records, reason)
            return ExecutionResult("blocked", records, reason)

        reason = f"Step {step.id} exhausted {step.max_attempts} attempt(s)"
        _write_checkpoint(checkpoint, "failed", records, reason)
        return ExecutionResult("failed", records, reason)

    _write_checkpoint(checkpoint, "completed", records, None)
    return ExecutionResult("completed", records)
