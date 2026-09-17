"""Совместимый вход Task Manager; реализация разделена по ответственности.

Публичный API — три класса. Переэкспорты приватных функций сохраняют старые
импорты, но не обещают прежние точки monkeypatch."""
from __future__ import annotations

from .contracts import (
    TASK_ID, SCHEMA_VERSION, ARTIFACT_ROLES, TERMINAL, TASK_TYPES,
    TASK_STATUSES, RETENTION_MONTHS, TaskError, _now, _utc, _stamp,
    _task_id, _version, _limit, _snapshot, _required, _event_context, _add_months,
)
from .migrations import (
    SCHEMA_MIGRATIONS, _create_schema_v1, _create_schema_v2,
    _create_schema_v3, _create_schema_v4, _create_schema_v5,
)
from .repository import SQLiteTaskRepository
from .service import TaskManagerService, _sha256, _artifact_digest
from .storage_transfer import _temporary_path, _cleanup

__all__ = [
    "SQLiteTaskRepository", "TaskError", "TaskManagerService", "TASK_ID",
    "SCHEMA_VERSION", "ARTIFACT_ROLES", "TERMINAL", "TASK_TYPES",
    "TASK_STATUSES", "RETENTION_MONTHS", "SCHEMA_MIGRATIONS",
]
