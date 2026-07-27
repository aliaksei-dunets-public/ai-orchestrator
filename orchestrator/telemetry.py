from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Mapping, Protocol


USAGE_FIELDS = (
    "static_prompt_tokens",
    "dynamic_context_tokens",
    "retrieved_context_tokens",
    "tool_result_tokens",
    "subagent_input_tokens",
    "subagent_output_tokens",
    "final_output_tokens",
    "total_tokens",
)
EVENT_FIELDS = {
    "schema_version",
    "event",
    "run_id",
    "status",
    "recorded_at",
    "metrics",
    "step_id",
    "attempt",
}
METRIC_FIELDS = {
    "duration_ms",
    "attempts",
    "retries",
    "tool_calls",
    "agent_handoffs",
    "usage",
}


class TelemetryError(ValueError):
    pass


class TelemetrySink(Protocol):
    def emit(self, event: TelemetryEvent) -> None: ...


@dataclass(frozen=True)
class TokenUsage:
    static_prompt_tokens: int | None = None
    dynamic_context_tokens: int | None = None
    retrieved_context_tokens: int | None = None
    tool_result_tokens: int | None = None
    subagent_input_tokens: int | None = None
    subagent_output_tokens: int | None = None
    final_output_tokens: int | None = None
    total_tokens: int | None = None

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                raise TelemetryError(f"{item.name} must be a non-negative integer or null")

    def to_dict(self) -> dict[str, int]:
        return {
            item.name: value
            for item in fields(self)
            if (value := getattr(self, item.name)) is not None
        }

    def merge(self, other: TokenUsage | None) -> TokenUsage:
        if other is None:
            return self
        values: dict[str, int | None] = {}
        for name in USAGE_FIELDS:
            left = getattr(self, name)
            right = getattr(other, name)
            values[name] = None if left is None and right is None else (left or 0) + (right or 0)
        return TokenUsage(**values)


@dataclass(frozen=True)
class RunTelemetry:
    duration_ms: int = 0
    attempts: int = 0
    retries: int = 0
    tool_calls: int = 0
    agent_handoffs: int = 0
    usage: TokenUsage = TokenUsage()

    def __post_init__(self) -> None:
        for name in ("duration_ms", "attempts", "retries", "tool_calls", "agent_handoffs"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise TelemetryError(f"{name} must be a non-negative integer")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["usage"] = self.usage.to_dict()
        return payload


@dataclass(frozen=True)
class TelemetryEvent:
    event: str
    run_id: str
    status: str
    metrics: RunTelemetry
    step_id: str | None = None
    attempt: int | None = None
    recorded_at: str | None = None

    def __post_init__(self) -> None:
        if not self.event.strip() or not self.run_id.strip() or not self.status.strip():
            raise TelemetryError("event, run_id, and status are required")
        if self.attempt is not None and self.attempt < 1:
            raise TelemetryError("attempt must be at least one")

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema_version": 1,
            "event": self.event,
            "run_id": self.run_id,
            "status": self.status,
            "recorded_at": self.recorded_at or datetime.now(UTC).isoformat(),
            "metrics": self.metrics.to_dict(),
        }
        if self.step_id is not None:
            payload["step_id"] = self.step_id
        if self.attempt is not None:
            payload["attempt"] = self.attempt
        return payload


class JsonlTelemetrySink:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def emit(self, event: TelemetryEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n"
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())


def _validate_event(payload: dict[str, object], *, line: int) -> None:
    unknown = set(payload) - EVENT_FIELDS
    required = {"schema_version", "event", "run_id", "status", "recorded_at", "metrics"}
    missing = required - set(payload)
    if unknown or missing or payload.get("schema_version") != 1:
        raise TelemetryError(
            f"Invalid telemetry event at line {line}: "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if payload.get("event") not in {"step_attempt", "run_completed"}:
        raise TelemetryError(f"Invalid telemetry event type at line {line}")
    if any(
        not isinstance(payload.get(name), str) or not str(payload[name]).strip()
        for name in ("run_id", "status", "recorded_at")
    ):
        raise TelemetryError(f"Invalid telemetry identifiers at line {line}")
    if payload["event"] == "step_attempt" and (
        not isinstance(payload.get("step_id"), str)
        or not str(payload["step_id"]).strip()
        or not isinstance(payload.get("attempt"), int)
        or isinstance(payload.get("attempt"), bool)
        or int(payload["attempt"]) < 1
    ):
        raise TelemetryError(f"Invalid step attempt identity at line {line}")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise TelemetryError(f"Invalid telemetry metrics at line {line}")
    metric_unknown = set(metrics) - METRIC_FIELDS
    metric_missing = METRIC_FIELDS - set(metrics)
    if metric_unknown or metric_missing:
        raise TelemetryError(
            f"Invalid telemetry metrics at line {line}: "
            f"missing={sorted(metric_missing)}, unknown={sorted(metric_unknown)}"
        )
    usage = metrics.get("usage")
    if not isinstance(usage, dict) or set(usage) - set(USAGE_FIELDS):
        raise TelemetryError(f"Invalid telemetry usage at line {line}")
    try:
        TokenUsage(**usage)
        RunTelemetry(
            duration_ms=metrics["duration_ms"],
            attempts=metrics["attempts"],
            retries=metrics["retries"],
            tool_calls=metrics["tool_calls"],
            agent_handoffs=metrics["agent_handoffs"],
            usage=TokenUsage(**usage),
        )
    except (TypeError, TelemetryError) as exc:
        raise TelemetryError(f"Invalid telemetry counters at line {line}: {exc}") from exc


def load_events(path: Path | str) -> tuple[dict[str, object], ...]:
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return ()
    events: list[dict[str, object]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise TelemetryError(f"Invalid telemetry JSONL at line {number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise TelemetryError(f"Invalid telemetry event at line {number}")
        _validate_event(payload, line=number)
        events.append(payload)
    return tuple(events)


def summarize_events(events: Iterable[Mapping[str, object]]) -> dict[str, object]:
    usage_totals: dict[str, int | None] = {name: 0 for name in USAGE_FIELDS}
    usage_samples = {name: 0 for name in USAGE_FIELDS}
    totals = {
        "events": 0,
        "runs": 0,
        "duration_ms": 0,
        "attempts": 0,
        "retries": 0,
        "tool_calls": 0,
        "agent_handoffs": 0,
        "usage": usage_totals,
        "usage_samples": usage_samples,
    }
    run_ids: set[str] = set()
    for event in events:
        totals["events"] += 1
        run_id = event.get("run_id")
        if isinstance(run_id, str):
            run_ids.add(run_id)
        metrics = event.get("metrics", {})
        if not isinstance(metrics, Mapping):
            continue
        if event.get("event") == "run_completed":
            for name in ("duration_ms", "attempts", "retries", "tool_calls", "agent_handoffs"):
                value = metrics.get(name)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    totals[name] += value
            usage = metrics.get("usage", {})
            if isinstance(usage, Mapping):
                for name in USAGE_FIELDS:
                    value = usage.get(name)
                    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                        usage_totals[name] = int(usage_totals[name] or 0) + value
                        usage_samples[name] += 1
    totals["runs"] = len(run_ids)
    for name in USAGE_FIELDS:
        if usage_samples[name] == 0:
            usage_totals[name] = None
    return totals


def format_summary_text(summary: Mapping[str, object]) -> str:
    usage = summary.get("usage", {})
    total_tokens = usage.get("total_tokens") if isinstance(usage, Mapping) else None
    rendered_tokens = "unknown" if total_tokens is None else str(total_tokens)
    return (
        f"runs={summary.get('runs', 0)} "
        f"events={summary.get('events', 0)} "
        f"attempts={summary.get('attempts', 0)} "
        f"retries={summary.get('retries', 0)} "
        f"tool_calls={summary.get('tool_calls', 0)} "
        f"agent_handoffs={summary.get('agent_handoffs', 0)} "
        f"reported_total_tokens={rendered_tokens}"
    )
