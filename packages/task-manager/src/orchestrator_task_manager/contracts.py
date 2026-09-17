"""Общие значения, ошибки и базовая валидация Task Manager."""
from __future__ import annotations

import calendar
import json
import re
from datetime import datetime, timezone
from typing import Any

TASK_ID = re.compile(r"TASK-[0-9]{4,}")
SCHEMA_VERSION = 5
ARTIFACT_ROLES = {
    "specification", "plan", "plan_review", "execution_package", "implementation",
    "code_review", "testing", "documentation", "readiness", "acceptance_package",
    "user_acceptance", "completion_decision",
}
TERMINAL = {"completed", "cancelled"}
TASK_TYPES = {"implementation", "analysis", "investigation", "incident", "exploration"}
TASK_STATUSES = {"created", "preparing", "ready", "active", "awaiting_input", "blocked", "awaiting_acceptance", "completed", "cancelled"}
RETENTION_MONTHS = 3


class TaskError(Exception):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": self.details}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise TaskError("validation_failed", "clock должен возвращать datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return _utc(value).isoformat()


def _task_id(value: Any) -> str:
    if not isinstance(value, str) or not TASK_ID.fullmatch(value):
        raise TaskError("validation_failed", "Некорректный ID задачи", value=value)
    return value


def _version(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise TaskError("validation_failed", "Некорректная ожидаемая версия")
    return value


def _limit(value: Any) -> None:
    if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 500):
        raise TaskError("validation_failed", "limit должен быть целым числом в диапазоне 1..500")


def _snapshot(raw: str) -> dict[str, Any]:
    try:
        result = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as exc:
        raise TaskError("repository_failure", "Некорректный снимок задачи; запустите validate") from exc
    if not isinstance(result, dict):
        raise TaskError("repository_failure", "Снимок задачи должен быть объектом; запустите validate")
    return result


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskError("validation_failed", f"Требуется непустое поле {name}")
    return value.strip()


def _event_context(value: dict[str, Any] | None, *, operation_id: str | None = None) -> dict[str, str | None]:
    if value is None:
        value = {}
    if not isinstance(value, dict):
        raise TaskError("validation_failed", "event_context должен быть объектом")
    allowed = {"actor_ref", "source", "correlation_id", "run_ref"}
    unknown = set(value) - allowed
    if unknown:
        raise TaskError("validation_failed", "Неизвестное поле event_context", fields=sorted(unknown))
    result: dict[str, str | None] = {}
    for key in allowed:
        item = value.get(key)
        result[key] = _required(item, key) if item is not None else None
    if result["correlation_id"] is None and operation_id is not None:
        result["correlation_id"] = operation_id
    return result


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.year * 12 + (value.month - 1) + months
    year, month_zero = divmod(month_index, 12)
    month = month_zero + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


