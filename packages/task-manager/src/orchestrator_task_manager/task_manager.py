"""Deterministic task lifecycle backed by a transactional SQLite repository."""

from __future__ import annotations

import copy
import calendar
import hashlib
import json
import os
import re
import sqlite3
import shutil
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


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


def _stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskError("validation_failed", f"Требуется непустое поле {name}")
    return value.strip()


def _create_schema_v1(db: sqlite3.Connection) -> None:
    """Create the baseline schema. Future changes must be separate migrations."""
    db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value INTEGER NOT NULL)")
    db.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('next_id', 1)")
    db.execute(
        """CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            version INTEGER NOT NULL CHECK(version > 0),
            status TEXT NOT NULL,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            body TEXT NOT NULL
        )"""
    )
    db.execute(
        """CREATE TABLE IF NOT EXISTS events (
            task_id TEXT NOT NULL REFERENCES tasks(id),
            sequence INTEGER NOT NULL,
            task_version INTEGER NOT NULL,
            type TEXT NOT NULL,
            at TEXT NOT NULL,
            payload TEXT NOT NULL,
            PRIMARY KEY(task_id, sequence)
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS tasks_status ON tasks(status)")


SCHEMA_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    0: _create_schema_v1,
}


def _create_schema_v2(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS operations (
            operation_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )


SCHEMA_MIGRATIONS[1] = _create_schema_v2


def _create_schema_v3(db: sqlite3.Connection) -> None:
    db.execute("CREATE INDEX IF NOT EXISTS tasks_type ON tasks(type)")


SCHEMA_MIGRATIONS[2] = _create_schema_v3


def _create_schema_v4(db: sqlite3.Connection) -> None:
    for column in ("actor_ref", "source", "correlation_id", "run_ref"):
        db.execute(f"ALTER TABLE events ADD COLUMN {column} TEXT")


SCHEMA_MIGRATIONS[3] = _create_schema_v4


def _create_schema_v5(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS purged_tasks (
            task_id TEXT PRIMARY KEY,
            terminal_at TEXT NOT NULL,
            archived_at TEXT NOT NULL,
            purged_at TEXT NOT NULL,
            reason TEXT NOT NULL,
            actor_ref TEXT
        )"""
    )
    db.execute("CREATE INDEX IF NOT EXISTS purged_tasks_purged_at ON purged_tasks(purged_at)")


SCHEMA_MIGRATIONS[4] = _create_schema_v5


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SQLiteTaskRepository:
    """Atomic snapshot+event commits. SQLite is the sole operational authority."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve(strict=True)
        if not self.project_root.is_dir():
            raise TaskError("validation_failed", "Корень проекта должен быть каталогом")
        self.path = self.project_root / ".orchestrator/state/tasks.sqlite3"
        if not self.path.resolve(strict=False).is_relative_to(self.project_root):
            raise TaskError("validation_failed", "Путь хранилища выходит за пределы проекта")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            self._migrate(db)

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise TaskError("repository_failure", "Неподдерживаемая версия схемы SQLite", version=version)
        if version == SCHEMA_VERSION:
            return

        db.execute("BEGIN IMMEDIATE")
        try:
            for source_version in range(version, SCHEMA_VERSION):
                migration = SCHEMA_MIGRATIONS.get(source_version)
                if migration is None:
                    raise TaskError(
                        "repository_failure",
                        "Отсутствует миграция схемы SQLite",
                        version=source_version,
                    )
                migration(db)
                db.execute(f"PRAGMA user_version={source_version + 1}")
            db.commit()
        except Exception:
            db.rollback()
            raise

    @contextmanager
    def _connect(self):
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=15)
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=15000")
            with db:
                yield db
        except sqlite3.Error as exc:
            raise TaskError("repository_failure", "Ошибка SQLite", sqlite_error=str(exc)) from exc
        finally:
            if db is not None:
                db.close()

    def create(self, snapshot: dict[str, Any], at: str, *, operation_id: str | None = None,
               fingerprint: str | None = None, event_context: dict[str, str | None] | None = None) -> dict[str, Any]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if operation_id is not None:
                existing = db.execute(
                    "SELECT fingerprint,result FROM operations WHERE operation_id=?", (operation_id,)
                ).fetchone()
                if existing is not None:
                    if existing[0] != fingerprint:
                        raise TaskError("operation_conflict", "Идентификатор операции уже использован иначе",
                                        operation_id=operation_id)
                    return json.loads(existing[1])
            next_id = db.execute("SELECT value FROM meta WHERE key='next_id'").fetchone()[0]
            task_id = f"TASK-{next_id:04d}"
            db.execute("UPDATE meta SET value=? WHERE key='next_id'", (next_id + 1,))
            snapshot = copy.deepcopy(snapshot)
            snapshot.update(id=task_id, version=1, created_at=at, updated_at=at)
            body = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
            db.execute(
                "INSERT INTO tasks(id,version,status,title,type,body) VALUES(?,?,?,?,?,?)",
                (task_id, 1, snapshot["status"], snapshot["title"], snapshot["type"], body),
            )
            context = event_context or {}
            db.execute(
                "INSERT INTO events(task_id,sequence,task_version,type,at,payload,actor_ref,source,correlation_id,run_ref) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (task_id, 1, 1, "task_created", at, json.dumps({"title": snapshot["title"]}, ensure_ascii=False),
                 context.get("actor_ref"), context.get("source"), context.get("correlation_id"), context.get("run_ref")),
            )
            if operation_id is not None:
                db.execute(
                    "INSERT INTO operations(operation_id,fingerprint,result,created_at) VALUES(?,?,?,?)",
                    (operation_id, fingerprint, json.dumps(snapshot, ensure_ascii=False, sort_keys=True), at),
                )
        return snapshot

    def get(self, task_id: str) -> dict[str, Any]:
        with self._connect() as db:
            row = db.execute("SELECT body FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise TaskError("task_not_found", f"Задача не найдена: {task_id}")
        return json.loads(row[0])

    def list(self, *, statuses: set[str] | None = None, task_type: str | None = None,
             query: str | None = None, limit: int | None = 100,
             cursor: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        if limit is not None and not 1 <= limit <= 500:
            raise TaskError("validation_failed", "limit должен быть в диапазоне 1..500")
        if cursor is not None and not TASK_ID.fullmatch(cursor):
            raise TaskError("validation_failed", "Некорректный cursor")
        clauses: list[str] = []
        params: list[Any] = []
        if statuses is not None:
            if not statuses:
                return []
            placeholders = ",".join("?" for _ in statuses)
            clauses.append(f"status IN ({placeholders})")
            params.extend(sorted(statuses))
        if task_type is not None:
            clauses.append("type=?")
            params.append(task_type)
        if query:
            clauses.append("LOWER(body) LIKE LOWER(?)")
            params.append(f"%{query}%")
        if cursor is not None:
            clauses.append("id < ?")
            params.append(cursor)
        if not include_archived:
            # Snapshots are canonical JSON; archived snapshots contain an object
            # under archive, while active/legacy snapshots contain null/missing.
            clauses.append("body NOT LIKE ?")
            params.append('%"archive": {%')
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        suffix = " LIMIT ?" if limit is not None else ""
        if limit is not None:
            params.append(limit)
        with self._connect() as db:
            rows = db.execute(f"SELECT body FROM tasks{where} ORDER BY id DESC{suffix}", params).fetchall()
        tasks = [json.loads(row[0]) for row in rows]
        if not include_archived:
            tasks = [task for task in tasks if not task.get("archive")]
        return tasks

    def history(self, task_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        if not isinstance(after_sequence, int) or after_sequence < 0:
            raise TaskError("validation_failed", "after_sequence должен быть неотрицательным числом")
        self.get(task_id)
        with self._connect() as db:
            rows = db.execute(
                "SELECT sequence,task_version,type,at,payload,actor_ref,source,correlation_id,run_ref FROM events "
                "WHERE task_id=? AND sequence>? ORDER BY sequence",
                (task_id, after_sequence),
            ).fetchall()
        return [
            {"task_ref": task_id, "sequence": seq, "task_version": version,
             "type": kind, "at": at, "payload": json.loads(payload),
             "actor_ref": actor_ref, "source": source, "correlation_id": correlation_id, "run_ref": run_ref}
            for seq, version, kind, at, payload, actor_ref, source, correlation_id, run_ref in rows
        ]

    def mutate(self, task_id: str, expected_version: int, event_type: str,
               change: Callable[[dict[str, Any]], dict[str, Any]], at: str, *,
               operation_id: str | None = None, fingerprint: str | None = None,
               event_context: dict[str, str | None] | None = None) -> dict[str, Any]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if operation_id is not None:
                existing = db.execute(
                    "SELECT fingerprint,result FROM operations WHERE operation_id=?", (operation_id,)
                ).fetchone()
                if existing is not None:
                    if existing[0] != fingerprint:
                        raise TaskError("operation_conflict", "Идентификатор операции уже использован иначе",
                                        operation_id=operation_id)
                    return json.loads(existing[1])
            row = db.execute("SELECT body FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise TaskError("task_not_found", f"Задача не найдена: {task_id}")
            snapshot = json.loads(row[0])
            if snapshot["version"] != expected_version:
                raise TaskError("task_version_conflict", "Версия задачи изменилась",
                                expected=expected_version, actual=snapshot["version"])
            payload = change(snapshot)
            snapshot["version"] += 1
            snapshot["updated_at"] = at
            db.execute(
                "UPDATE tasks SET version=?,status=?,title=?,type=?,body=? WHERE id=? AND version=?",
                (snapshot["version"], snapshot["status"], snapshot["title"], snapshot["type"],
                 json.dumps(snapshot, ensure_ascii=False, sort_keys=True), task_id, expected_version),
            )
            context = event_context or {}
            db.execute(
                "INSERT INTO events(task_id,sequence,task_version,type,at,payload,actor_ref,source,correlation_id,run_ref) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (task_id, snapshot["version"], snapshot["version"], event_type, at,
                 json.dumps(payload, ensure_ascii=False, sort_keys=True), context.get("actor_ref"),
                 context.get("source"), context.get("correlation_id"), context.get("run_ref")),
            )
            if operation_id is not None:
                db.execute(
                    "INSERT INTO operations(operation_id,fingerprint,result,created_at) VALUES(?,?,?,?)",
                    (operation_id, fingerprint, json.dumps(snapshot, ensure_ascii=False, sort_keys=True), at),
                )
        return snapshot

    def purge(self, task_id: str, expected_version: int, *, terminal_at: str,
              archived_at: str, purged_at: str, reason: str, actor_ref: str | None = None,
              operation_id: str | None = None, fingerprint: str | None = None) -> dict[str, Any]:
        """Delete a task and its events atomically, retaining a minimal tombstone."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if operation_id is not None:
                existing = db.execute(
                    "SELECT fingerprint,result FROM operations WHERE operation_id=?", (operation_id,)
                ).fetchone()
                if existing is not None:
                    if existing[0] != fingerprint:
                        raise TaskError("operation_conflict", "Идентификатор операции уже использован иначе",
                                        operation_id=operation_id)
                    return json.loads(existing[1])
            row = db.execute("SELECT version FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                tombstone = db.execute(
                    "SELECT task_id,purged_at FROM purged_tasks WHERE task_id=?", (task_id,)
                ).fetchone()
                if tombstone is not None:
                    raise TaskError("task_purged", f"Задача уже удалена: {task_id}", purged_at=tombstone[1])
                raise TaskError("task_not_found", f"Задача не найдена: {task_id}")
            if row[0] != expected_version:
                raise TaskError("task_version_conflict", "Версия задачи изменилась",
                                expected=expected_version, actual=row[0])
            db.execute(
                "INSERT INTO purged_tasks(task_id,terminal_at,archived_at,purged_at,reason,actor_ref) VALUES(?,?,?,?,?,?)",
                (task_id, terminal_at, archived_at, purged_at, reason, actor_ref),
            )
            db.execute("DELETE FROM events WHERE task_id=?", (task_id,))
            db.execute("DELETE FROM tasks WHERE id=? AND version=?", (task_id, expected_version))
            result = {"id": task_id, "purged": True, "purged_at": purged_at}
            if operation_id is not None:
                db.execute(
                    "INSERT INTO operations(operation_id,fingerprint,result,created_at) VALUES(?,?,?,?)",
                    (operation_id, fingerprint, json.dumps(result, ensure_ascii=False, sort_keys=True), purged_at),
                )
        return result


class TaskManagerService:
    def __init__(self, project_root: Path, *, clock: Callable[[], datetime] = _now,
                 acceptance_required: bool = True) -> None:
        self.repository = SQLiteTaskRepository(project_root)
        self.clock = clock
        self.acceptance_required = acceptance_required

    @staticmethod
    def _operation_fingerprint(*parts: Any) -> str:
        body = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()

    def _mutate(self, task_id: str, expected_version: int, event_type: str,
                change: Callable[[dict[str, Any]], dict[str, Any]], *,
                operation_id: str | None = None, operation_payload: Any = None,
                event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if not TASK_ID.fullmatch(task_id):
            raise TaskError("validation_failed", "Некорректный ID задачи")
        if not isinstance(expected_version, int) or isinstance(expected_version, bool) or expected_version < 1:
            raise TaskError("validation_failed", "Некорректная ожидаемая версия")
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        fingerprint = self._operation_fingerprint(event_type, task_id, expected_version, operation_payload)
        context = _event_context(event_context, operation_id=operation_id)
        return self.repository.mutate(
            task_id, expected_version, event_type, change, _stamp(self.clock()),
            operation_id=operation_id, fingerprint=fingerprint, event_context=context,
        )

    def create_task(self, *, title: str, task_type: str, objective: str,
                    original_request: str, acceptance_criteria: list[str],
                    constraints: list[str] | None = None, target_workflow: str = "development",
                    handoff_mode: str = "deferred", operation_id: str | None = None,
                    event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        if handoff_mode not in {"immediate", "deferred"}:
            raise TaskError("validation_failed", "Неизвестный режим передачи")
        if task_type not in TASK_TYPES:
            raise TaskError("validation_failed", "Неизвестный тип задачи")
        if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
            raise TaskError("validation_failed", "Нужен хотя бы один критерий приёмки")
        criteria = [
            {"id": f"AC-{index:02d}", "text": _required(text, "acceptance_criteria")}
            for index, text in enumerate(acceptance_criteria, 1)
        ]
        constraints = constraints or []
        if not isinstance(constraints, list):
            raise TaskError("validation_failed", "constraints должен быть списком")
        snapshot = {
            "title": _required(title, "title"), "type": _required(task_type, "task_type"),
            "status": "created", "original_request": _required(original_request, "original_request"),
            "objective": _required(objective, "objective"), "problem_statement": None,
            "acceptance_criteria": criteria,
            "constraints": [_required(item, "constraint") for item in constraints],
            "definition_version": 1, "target_workflow": _required(target_workflow, "target_workflow"),
            "handoff_mode": handoff_mode, "prepared_source_revision": None,
            "terminal_at": None, "archive": None,
            "artifacts": {}, "workflow_runs": [], "active_run_ref": None,
            "active_claim": None, "blockers": [], "user_decisions": [], "external_links": [],
            "resume_status": None, "pending_decision_count": None,
        }
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        fingerprint = self._operation_fingerprint("task_created", snapshot)
        context = _event_context(event_context, operation_id=operation_id)
        return self.repository.create(
            snapshot, _stamp(self.clock()), operation_id=operation_id, fingerprint=fingerprint,
            event_context=context,
        )

    def get_task(self, task_id: str) -> dict[str, Any]:
        return self.repository.get(task_id)

    def list_tasks(self, *, statuses: set[str] | None = None, task_type: str | None = None,
                   query: str | None = None, limit: int | None = 100,
                   cursor: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        return self.repository.list(statuses=statuses, task_type=task_type, query=query,
                                    limit=limit, cursor=cursor, include_archived=include_archived)

    def get_history(self, task_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        return self.repository.history(task_id, after_sequence)

    def get_document(self, task_id: str, role: str) -> str:
        if role not in {"specification", "plan"}:
            raise TaskError("validation_failed", "Можно читать только plan или legacy specification")
        task = self.get_task(task_id)
        artifact = task["artifacts"].get(role)
        if not artifact or not artifact.get("path"):
            raise TaskError("task_not_found", "Документ задачи не найден")
        path = self._artifact_path(task_id, artifact["path"])
        if _sha256(path) != artifact.get("sha256"):
            raise TaskError("guard_failed", "Документ изменился после привязки")
        return path.read_text(encoding="utf-8")

    def get_claim(self, task_id: str) -> dict[str, Any] | None:
        return self.get_task(task_id)["active_claim"]

    def export_state(self, destination: Path) -> dict[str, Any]:
        """Write a deterministic, read-only JSON export of task state and events."""
        destination = Path(destination)
        if destination.resolve(strict=False) == self.repository.path.resolve():
            raise TaskError("validation_failed", "Экспорт нельзя записать поверх SQLite")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.repository._connect() as db:
            schema_version = db.execute("PRAGMA user_version").fetchone()[0]
            tasks = [json.loads(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY id")]
            events = []
            for task_id, sequence, task_version, kind, at, payload, actor_ref, source, correlation_id, run_ref in db.execute(
                "SELECT task_id,sequence,task_version,type,at,payload,actor_ref,source,correlation_id,run_ref FROM events ORDER BY task_id,sequence"
            ):
                events.append({"task_ref": task_id, "sequence": sequence, "task_version": task_version,
                               "type": kind, "at": at, "payload": json.loads(payload),
                               "actor_ref": actor_ref, "source": source,
                               "correlation_id": correlation_id, "run_ref": run_ref})
            purged_tasks = [dict(zip(("task_id", "terminal_at", "archived_at", "purged_at", "reason", "actor_ref"), row))
                            for row in db.execute(
                                "SELECT task_id,terminal_at,archived_at,purged_at,reason,actor_ref FROM purged_tasks ORDER BY task_id"
                            )]
        export = {"format": "orchestrator-task-manager-export-v1", "schema_version": schema_version,
                  "tasks": tasks, "events": events, "purged_tasks": purged_tasks}
        temporary = destination.with_name(destination.name + ".tmp")
        temporary.write_text(json.dumps(export, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        return {"path": str(destination), "schema_version": schema_version,
                "task_count": len(tasks), "event_count": len(events),
                "purged_task_count": len(purged_tasks)}

    def backup(self, destination: Path) -> dict[str, Any]:
        """Create a consistent SQLite backup without changing task state."""
        destination = Path(destination)
        if destination.resolve(strict=False) == self.repository.path.resolve():
            raise TaskError("validation_failed", "Backup нельзя записать поверх рабочей БД")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(destination.name + ".tmp")
        if temporary.exists():
            temporary.unlink()
        source = sqlite3.connect(self.repository.path)
        target = sqlite3.connect(temporary)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        self._validate_database(temporary)
        os.replace(temporary, destination)
        return {"path": str(destination), "schema_version": self._database_version(destination)}

    def restore(self, source: Path) -> dict[str, Any]:
        """Validate a backup and atomically replace the active database."""
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise TaskError("validation_failed", "Backup-файл отсутствует или является ссылкой")
        self._validate_database(source)
        current = self.repository.path
        safety_copy = current.with_name(current.name + ".pre-restore")
        temporary = current.with_name(current.name + ".restore.tmp")
        if temporary.exists():
            temporary.unlink()
        shutil.copy2(source, temporary)
        try:
            self._validate_database(temporary)
            if current.exists():
                shutil.copy2(current, safety_copy)
            os.replace(temporary, current)
        except Exception:
            if temporary.exists():
                temporary.unlink()
            raise
        return {"path": str(current), "backup": str(source),
                "safety_copy": str(safety_copy) if safety_copy.exists() else None,
                "schema_version": self._database_version(current)}

    @staticmethod
    def _database_version(path: Path) -> int:
        db = sqlite3.connect(path)
        try:
            return int(db.execute("PRAGMA user_version").fetchone()[0])
        finally:
            db.close()

    @staticmethod
    def _validate_database(path: Path) -> None:
        db = None
        try:
            db = sqlite3.connect(path)
            if int(db.execute("PRAGMA user_version").fetchone()[0]) > SCHEMA_VERSION:
                raise TaskError("repository_failure", "Неподдерживаемая версия схемы SQLite")
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise TaskError("repository_failure", "Backup SQLite не прошёл integrity_check")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not {"tasks", "events", "meta"}.issubset(tables):
                raise TaskError("repository_failure", "Backup SQLite не содержит таблицы Task Manager")
        except sqlite3.Error as exc:
            raise TaskError("repository_failure", "Некорректный backup SQLite", sqlite_error=str(exc)) from exc
        finally:
            if db is not None:
                db.close()

    def health_check(self) -> list[dict[str, str]]:
        """Read-only integrity diagnostics; never invents evidence or repairs state."""
        issues: list[dict[str, str]] = []
        with self.repository._connect() as db:
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            if integrity != "ok":
                issues.append({"severity": "critical", "code": "sqlite_integrity", "detail": integrity})
            rows = db.execute("SELECT id,body FROM tasks ORDER BY id").fetchall()
            for task_id, raw in rows:
                try:
                    task = json.loads(raw)
                except json.JSONDecodeError:
                    issues.append({"severity": "critical", "code": "snapshot_invalid", "detail": task_id})
                    continue
                if task.get("id") != task_id:
                    issues.append({"severity": "error", "code": "snapshot_id_mismatch", "detail": task_id})
                columns = db.execute("SELECT version,status,title,type FROM tasks WHERE id=?", (task_id,)).fetchone()
                if columns and (task.get("version"), task.get("status"), task.get("title"), task.get("type")) != columns:
                    issues.append({"severity": "error", "code": "snapshot_column_mismatch", "detail": task_id})
                if task.get("status") not in TASK_STATUSES:
                    issues.append({"severity": "error", "code": "status_invalid", "detail": task_id})
                status = task.get("status")
                archive = task.get("archive")
                if archive is not None:
                    if status not in {"completed", "cancelled"}:
                        issues.append({"severity": "error", "code": "archive_status_invalid", "detail": task_id})
                    if not isinstance(archive, dict) or not archive.get("archived_at") or not archive.get("terminal_at"):
                        issues.append({"severity": "error", "code": "archive_metadata_invalid", "detail": task_id})
                events = db.execute(
                    "SELECT sequence,task_version,payload FROM events WHERE task_id=? ORDER BY sequence", (task_id,)
                ).fetchall()
                if len(events) != task.get("version") or any(
                    sequence != index or version != index
                    for index, (sequence, version, _payload) in enumerate(events, 1)
                ):
                    issues.append({"severity": "error", "code": "event_sequence", "detail": task_id})
                for sequence, _version, payload in events:
                    try:
                        json.loads(payload)
                    except json.JSONDecodeError:
                        issues.append({"severity": "error", "code": "event_payload_invalid", "detail": f"{task_id}:{sequence}"})
                if status == "ready":
                    try:
                        self._ready_guard(task)
                    except (TaskError, KeyError, TypeError) as exc:
                        issues.append({"severity": "error", "code": "ready_guard", "detail": f"{task_id}: {exc}"})
                if status == "active" and not task.get("active_claim"):
                    issues.append({"severity": "error", "code": "active_without_claim", "detail": task_id})
                if status == "blocked" and not any(
                    item.get("blocking") and item.get("status") == "open" for item in task.get("blockers", [])
                ):
                    issues.append({"severity": "warning", "code": "blocked_without_open_blocker", "detail": task_id})
                if status == "completed" and "completion_decision" not in task.get("artifacts", {}):
                    issues.append({"severity": "error", "code": "completion_evidence", "detail": task_id})
            orphan = db.execute(
                "SELECT task_id,sequence FROM events WHERE task_id NOT IN (SELECT id FROM tasks)"
            ).fetchall()
            for task_id, sequence in orphan:
                issues.append({"severity": "error", "code": "orphan_event", "detail": f"{task_id}:{sequence}"})
            if "operations" in {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
                for operation_id, fingerprint, result in db.execute("SELECT operation_id,fingerprint,result FROM operations"):
                    if not operation_id or not fingerprint:
                        issues.append({"severity": "error", "code": "operation_metadata_invalid", "detail": operation_id or "<empty>"})
                    try:
                        json.loads(result)
                    except json.JSONDecodeError:
                        issues.append({"severity": "error", "code": "operation_result_invalid", "detail": operation_id})
        return issues

    def list_executable_tasks(self, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 500:
            raise TaskError("validation_failed", "limit должен быть в диапазоне 1..500")
        return [task for task in self.list_tasks(statuses={"ready"}, limit=None)
                if task["target_workflow"] == "development"][:limit]

    def start_preparation(self, task_id: str, expected_version: int, run_ref: str,
                          *, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        run_ref = _required(run_ref, "run_ref")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "created":
                raise TaskError("invalid_transition", "Подготовка начинается только из created")
            task["status"] = "preparing"
            task["active_run_ref"] = run_ref
            task["workflow_runs"].append(run_ref)
            return {"from": "created", "to": "preparing", "run_ref": run_ref}

        return self._mutate(task_id, expected_version, "preparation_started", change,
                            operation_id=operation_id, operation_payload={"run_ref": run_ref},
                            event_context=event_context)

    def refine_task_definition(self, task_id: str, expected_version: int, *, objective: str | None = None,
                               problem_statement: str | None = None,
                               acceptance_criteria: list[str] | None = None,
                               constraints: list[str] | None = None,
                               evidence_refs: list[str] | None = None) -> dict[str, Any]:
        if all(value is None for value in (objective, problem_statement, acceptance_criteria, constraints)):
            raise TaskError("validation_failed", "Нет изменений определения")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] not in {"created", "preparing", "ready"}:
                raise TaskError("invalid_transition", "Определение нельзя уточнить в текущем статусе")
            if task["status"] == "ready":
                task["status"] = "preparing"
                task["artifacts"].clear()
                task["prepared_source_revision"] = None
            if objective is not None:
                task["objective"] = _required(objective, "objective")
            if problem_statement is not None:
                task["problem_statement"] = _required(problem_statement, "problem_statement")
            if acceptance_criteria is not None:
                if not isinstance(acceptance_criteria, list) or not acceptance_criteria:
                    raise TaskError("validation_failed", "Нужны критерии приёмки")
                task["acceptance_criteria"] = [
                    {"id": f"AC-{index:02d}", "text": _required(text, "acceptance_criteria")}
                    for index, text in enumerate(acceptance_criteria, 1)
                ]
            if constraints is not None:
                if not isinstance(constraints, list):
                    raise TaskError("validation_failed", "constraints должен быть списком")
                task["constraints"] = [_required(item, "constraint") for item in constraints]
            task["definition_version"] += 1
            return {"definition_version": task["definition_version"], "evidence_refs": evidence_refs or []}

        return self._mutate(task_id, expected_version, "definition_refined", change)

    def update_metadata(self, task_id: str, expected_version: int, *, title: str) -> dict[str, Any]:
        title = _required(title, "title")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя изменить")
            task["title"] = title
            return {"title": title}

        return self._mutate(task_id, expected_version, "metadata_updated", change)

    def _artifact_path(self, task_id: str, path: str) -> Path:
        root = self.repository.project_root / ".orchestrator/tasks" / task_id
        candidate = self.repository.project_root / path
        if not candidate.resolve(strict=False).is_relative_to(root.resolve(strict=False)):
            raise TaskError("validation_failed", "Артефакт должен находиться в каталоге задачи")
        if candidate.is_symlink() or not candidate.is_file():
            raise TaskError("validation_failed", "Файл артефакта отсутствует или является ссылкой")
        return candidate

    def attach_artifact(self, task_id: str, expected_version: int, *, role: str, ref: str,
                        path: str | None = None, sha256: str | None = None,
                        metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if role not in ARTIFACT_ROLES:
            raise TaskError("validation_failed", "Неизвестная роль артефакта")
        ref = _required(ref, "ref")
        metadata = metadata or {}
        if not isinstance(metadata, dict):
            raise TaskError("validation_failed", "metadata должен быть объектом")
        if role in {"specification", "plan"}:
            if not path or not sha256:
                raise TaskError("validation_failed", "Для документа требуются путь и хеш")
            candidate = self._artifact_path(task_id, path)
            if _sha256(candidate) != sha256:
                raise TaskError("validation_failed", "Хеш документа не совпадает")
        artifact = {"ref": ref, "path": path, "sha256": sha256, "metadata": metadata}

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "К конечной задаче нельзя добавить артефакт")
            if role in {"specification", "plan", "plan_review", "execution_package"} and task["status"] not in {
                "created", "preparing", "ready"
            }:
                raise TaskError("invalid_transition", "Артефакт подготовки нельзя менять во время исполнения")
            if role in {"plan_review", "execution_package"} and task["status"] != "preparing":
                raise TaskError("invalid_transition", "Одобрение и пакет добавляются только при подготовке")
            task["artifacts"][role] = artifact
            if role in {"specification", "plan"}:
                task["artifacts"].pop("plan_review", None)
                task["artifacts"].pop("execution_package", None)
                task["prepared_source_revision"] = None
                if task["status"] == "ready":
                    task["status"] = "preparing"
            return {"role": role, "ref": ref}

        return self._mutate(task_id, expected_version, "artifact_attached", change)

    def attach_execution_package(self, task_id: str, expected_version: int, *, ref: str,
                                 plan_sha256: str, prepared_source_revision: str,
                                 specification_sha256: str | None = None) -> dict[str, Any]:
        metadata = {
            "plan_sha256": _required(plan_sha256, "plan_sha256"),
            "prepared_source_revision": _required(prepared_source_revision, "prepared_source_revision"),
        }
        # Legacy callers may still provide this value. It is retained as metadata
        # but is no longer required for readiness.
        if specification_sha256 is not None:
            metadata["specification_sha256"] = _required(specification_sha256, "specification_sha256")
        return self.attach_artifact(
            task_id, expected_version, role="execution_package", ref=ref,
            metadata=metadata,
        )

    def _ready_guard(self, task: dict[str, Any]) -> None:
        if any(item["status"] == "open" and item["blocking"] for item in task["blockers"]):
            raise TaskError("guard_failed", "Есть открытый блокирующий фактор")
        artifacts = task["artifacts"]
        for role in ("plan", "plan_review", "execution_package"):
            if role not in artifacts:
                raise TaskError("guard_failed", f"Нет артефакта {role}")
        document = artifacts["plan"]
        try:
            candidate = self._artifact_path(task["id"], document["path"])
        except TaskError as exc:
            raise TaskError("guard_failed", "Документ plan недоступен") from exc
        if _sha256(candidate) != document["sha256"]:
            raise TaskError("guard_failed", "Документ plan изменился")
        plan_hash = artifacts["plan"]["sha256"]
        review = artifacts["plan_review"]["metadata"]
        package = artifacts["execution_package"]["metadata"]
        for binding in (review, package):
            if binding.get("plan_sha256") != plan_hash:
                raise TaskError("guard_failed", "Одобрение или пакет привязаны к другой версии plan")
        if review.get("status") != "approved":
            raise TaskError("guard_failed", "План не одобрен")
        _required(package.get("prepared_source_revision"), "prepared_source_revision")

    def mark_ready(self, task_id: str, expected_version: int, *, operation_id: str | None = None,
                   event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "preparing":
                raise TaskError("invalid_transition", "В ready можно перейти только из preparing")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Сначала завершите запуск подготовки")
            self._ready_guard(task)
            task["status"] = "ready"
            task["prepared_source_revision"] = task["artifacts"]["execution_package"]["metadata"]["prepared_source_revision"]
            return {"from": "preparing", "to": "ready"}

        return self._mutate(task_id, expected_version, "status_changed", change,
                            operation_id=operation_id, operation_payload={"to": "ready"},
                            event_context=event_context)

    def claim_task(self, task_id: str, expected_version: int, *, worker_ref: str,
                   lease_seconds: int = 900, operation_id: str | None = None,
                   event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        worker_ref = _required(worker_ref, "worker_ref")
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 30 <= lease_seconds <= 86400:
            raise TaskError("validation_failed", "lease_seconds должен быть в диапазоне 30..86400")
        now = self.clock()
        claim_ref = f"CLAIM-{task_id}-{uuid.uuid4().hex[:12]}"

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "ready" or task["active_claim"] is not None:
                raise TaskError("task_not_ready", "Задача уже занята или не готова")
            self._ready_guard(task)
            task["status"] = "active"
            task["active_claim"] = {
                "ref": claim_ref, "worker_ref": worker_ref,
                "lease_until": _stamp(now + timedelta(seconds=lease_seconds)),
                "execution_package_ref": task["artifacts"]["execution_package"]["ref"],
            }
            return {"from": "ready", "to": "active", "claim_ref": claim_ref, "worker_ref": worker_ref}

        return self._mutate(task_id, expected_version, "task_claimed", change,
                            operation_id=operation_id,
                            operation_payload={"worker_ref": worker_ref, "lease_seconds": lease_seconds},
                            event_context=event_context)

    def renew_claim(self, task_id: str, expected_version: int, *, claim_ref: str,
                    lease_seconds: int = 900) -> dict[str, Any]:
        if not isinstance(lease_seconds, int) or isinstance(lease_seconds, bool) or not 30 <= lease_seconds <= 86400:
            raise TaskError("validation_failed", "Некорректная длительность lease")
        now = self.clock()

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            if not claim or claim["ref"] != claim_ref:
                raise TaskError("claim_conflict", "Закрепление не найдено")
            if datetime.fromisoformat(claim["lease_until"]) <= now:
                raise TaskError("claim_expired", "Срок закрепления истёк")
            claim["lease_until"] = _stamp(now + timedelta(seconds=lease_seconds))
            return {"claim_ref": claim_ref, "lease_until": claim["lease_until"]}

        return self._mutate(task_id, expected_version, "claim_renewed", change)

    def release_claim(self, task_id: str, expected_version: int, *, claim_ref: str,
                      target_status: str, reason: str) -> dict[str, Any]:
        reason = _required(reason, "reason")
        if target_status not in {"ready", "preparing", "blocked", "awaiting_input"}:
            raise TaskError("validation_failed", "Недопустимый статус после освобождения")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            current_status = task["status"]
            if current_status not in {"active", "blocked", "awaiting_input"} or not claim or claim["ref"] != claim_ref:
                raise TaskError("claim_conflict", "Закрепление не принадлежит задаче")
            if current_status in {"blocked", "awaiting_input"} and target_status != current_status:
                raise TaskError("invalid_transition", "При паузе сохраняйте её статус до возобновления")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Сначала завершите связанный запуск графа")
            if target_status == "ready":
                self._ready_guard(task)
            if target_status == "blocked" and current_status != "blocked" and not any(
                item["blocking"] and item["status"] == "open" for item in task["blockers"]
            ):
                raise TaskError("guard_failed", "Для blocked нужен открытый блокер")
            task["active_claim"] = None
            task["status"] = target_status
            if current_status == "active" and target_status in {"blocked", "awaiting_input"}:
                task["resume_status"] = "ready"
            if target_status == "preparing":
                task["artifacts"].pop("plan_review", None)
                task["artifacts"].pop("execution_package", None)
                task["prepared_source_revision"] = None
            return {"claim_ref": claim_ref, "to": target_status, "reason": reason}

        return self._mutate(task_id, expected_version, "claim_released", change)

    def recover_expired_claim(self, task_id: str, expected_version: int) -> dict[str, Any]:
        now = self.clock()

        def change(task: dict[str, Any]) -> dict[str, Any]:
            claim = task["active_claim"]
            if not claim or datetime.fromisoformat(claim["lease_until"]) > now:
                raise TaskError("claim_conflict", "Нет истёкшего закрепления")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Связанный запуск требует ручной проверки")
            if task["status"] == "active":
                self._ready_guard(task)
            task["active_claim"] = None
            if task["status"] == "active":
                task["status"] = "ready"
            return {"claim_ref": claim["ref"], "to": task["status"]}

        return self._mutate(task_id, expected_version, "claim_recovered", change)

    def link_workflow_run(self, task_id: str, expected_version: int, *, run_ref: str,
                          relation: str, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        run_ref = _required(run_ref, "run_ref")
        if relation not in {"active", "finished"}:
            raise TaskError("validation_failed", "Неизвестное отношение запуска")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if relation == "active":
                if task["status"] not in {"preparing", "active"} or task["active_run_ref"]:
                    raise TaskError("guard_failed", "Нельзя привязать второй активный запуск")
                task["active_run_ref"] = run_ref
                if run_ref not in task["workflow_runs"]:
                    task["workflow_runs"].append(run_ref)
            elif task["active_run_ref"] != run_ref:
                raise TaskError("guard_failed", "Активный запуск не совпадает")
            else:
                task["active_run_ref"] = None
            return {"run_ref": run_ref, "relation": relation}

        return self._mutate(task_id, expected_version, "workflow_run_linked", change,
                            operation_id=operation_id, operation_payload={"run_ref": run_ref, "relation": relation},
                            event_context=event_context)

    def add_blocker(self, task_id: str, expected_version: int, *, blocker_type: str,
                    summary: str, evidence_refs: list[str] | None = None,
                    blocking: bool = True) -> dict[str, Any]:
        blocker_type = _required(blocker_type, "blocker_type")
        summary = _required(summary, "summary")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя блокировать")
            blocker_id = f"BLOCK-{len(task['blockers']) + 1:02d}"
            task["blockers"].append({"id": blocker_id, "type": blocker_type, "summary": summary,
                                     "blocking": bool(blocking), "status": "open",
                                     "evidence_refs": evidence_refs or []})
            if blocking and task["status"] != "blocked":
                task["resume_status"] = "ready" if task["status"] == "active" else task["status"]
                task["status"] = "blocked"
            return {"blocker_ref": blocker_id, "blocking": blocking}

        return self._mutate(task_id, expected_version, "blocker_added", change)

    def resolve_blocker(self, task_id: str, expected_version: int, *, blocker_ref: str,
                        resolution: str) -> dict[str, Any]:
        resolution = _required(resolution, "resolution")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            blocker = next((item for item in task["blockers"] if item["id"] == blocker_ref), None)
            if not blocker or blocker["status"] != "open":
                raise TaskError("validation_failed", "Открытый блокер не найден")
            blocker["status"] = "resolved"
            blocker["resolution"] = resolution
            return {"blocker_ref": blocker_ref, "resolution": resolution}

        return self._mutate(task_id, expected_version, "blocker_resolved", change)

    def record_user_decision(self, task_id: str, expected_version: int, *, decision_type: str,
                             value: str, artifact_ref: str | None = None,
                             candidate_revision: str | None = None,
                             operation_id: str | None = None,
                             event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        decision_type = _required(decision_type, "decision_type")
        value = _required(value, "value")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Конечную задачу нельзя изменить")
            if decision_type == "acceptance" and task["status"] != "awaiting_acceptance":
                raise TaskError("invalid_transition", "Решение о приёмке фиксируется только на этапе приёмки")
            decision = {"type": decision_type, "value": value,
                        "artifact_ref": artifact_ref, "candidate_revision": candidate_revision}
            task["user_decisions"].append(decision)
            return decision

        return self._mutate(task_id, expected_version, "user_decision_recorded", change,
                            operation_id=operation_id,
                            operation_payload={"decision_type": decision_type, "value": value,
                                                "artifact_ref": artifact_ref, "candidate_revision": candidate_revision},
                            event_context=event_context)

    def transition_status(self, task_id: str, expected_version: int, *, to: str,
                          reason: str, operation_id: str | None = None,
                          event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            before = task["status"]
            if to == "awaiting_input" and before in {"preparing", "active"}:
                task["resume_status"] = "ready" if before == "active" else before
                task["pending_decision_count"] = len(task["user_decisions"])
            elif to == "blocked" and before in {"preparing", "ready", "active"}:
                if not any(item["blocking"] and item["status"] == "open" for item in task["blockers"]):
                    raise TaskError("guard_failed", "Для blocked нужен открытый блокер")
                task["resume_status"] = "ready" if before == "active" else before
            elif before in {"awaiting_input", "blocked"} and to == task["resume_status"]:
                if task["active_claim"] or task["active_run_ref"]:
                    raise TaskError("guard_failed", "Сначала завершите запуск и освободите закрепление")
                if before == "blocked" and any(
                    item["blocking"] and item["status"] == "open" for item in task["blockers"]
                ):
                    raise TaskError("guard_failed", "Не все блокеры разрешены")
                if before == "awaiting_input" and len(task["user_decisions"]) <= (task["pending_decision_count"] or 0):
                    raise TaskError("guard_failed", "Нет решения пользователя")
                if to == "ready":
                    self._ready_guard(task)
                task["pending_decision_count"] = None
                task["resume_status"] = None
            else:
                raise TaskError("invalid_transition", f"Переход {before} → {to} запрещён")
            task["status"] = to
            return {"from": before, "to": to, "reason": reason}

        return self._mutate(task_id, expected_version, "status_changed", change,
                            operation_id=operation_id, operation_payload={"to": to, "reason": reason},
                            event_context=event_context)

    def mark_awaiting_acceptance(self, task_id: str, expected_version: int) -> dict[str, Any]:
        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] != "active":
                raise TaskError("invalid_transition", "Приёмка возможна только после исполнения")
            readiness = task["artifacts"].get("readiness", {}).get("metadata", {})
            if readiness.get("status") != "ready" or "acceptance_package" not in task["artifacts"]:
                raise TaskError("guard_failed", "Нет свидетельства готовности или пакета приёмки")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Активный запуск ещё не завершён")
            task["status"] = "awaiting_acceptance"
            task["active_claim"] = None
            return {"from": "active", "to": "awaiting_acceptance"}

        return self._mutate(task_id, expected_version, "status_changed", change)

    def complete_task(self, task_id: str, expected_version: int, *, completion_decision_ref: str,
                      operation_id: str | None = None,
                      event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        completion_decision_ref = _required(completion_decision_ref, "completion_decision_ref")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            allowed = {"awaiting_acceptance"} if self.acceptance_required else {"active", "awaiting_acceptance"}
            if task["status"] not in allowed:
                raise TaskError("invalid_transition", "Задача не находится в состоянии завершения")
            if any(item["blocking"] and item["status"] == "open" for item in task["blockers"]):
                raise TaskError("guard_failed", "Открытый блокер мешает завершению")
            readiness = task["artifacts"].get("readiness", {}).get("metadata", {})
            if readiness.get("status") != "ready":
                raise TaskError("guard_failed", "Нет подтверждённой готовности")
            if self.acceptance_required:
                revision = readiness.get("candidate_revision")
                if not revision or not any(
                    decision["type"] == "acceptance" and decision["value"] == "approved"
                    and decision["candidate_revision"] == revision
                    for decision in task["user_decisions"]
                ):
                    raise TaskError("guard_failed", "Нет приёмки текущей ревизии пользователем")
            if task["active_run_ref"]:
                raise TaskError("guard_failed", "Запуск графа ещё активен")
            task["status"] = "completed"
            task["active_claim"] = None
            task["terminal_at"] = _stamp(self.clock())
            task["artifacts"]["completion_decision"] = {"ref": completion_decision_ref}
            return {"to": "completed", "completion_decision_ref": completion_decision_ref}

        return self._mutate(task_id, expected_version, "task_completed", change,
                            operation_id=operation_id,
                            operation_payload={"completion_decision_ref": completion_decision_ref},
                            event_context=event_context)

    def cancel_task(self, task_id: str, expected_version: int, *, reason: str) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] in TERMINAL:
                raise TaskError("invalid_transition", "Задача уже завершена")
            if task["active_run_ref"] or task["active_claim"]:
                raise TaskError("guard_failed", "Сначала остановите запуск и освободите закрепление")
            task["status"] = "cancelled"
            task["terminal_at"] = _stamp(self.clock())
            return {"to": "cancelled", "reason": reason}

        return self._mutate(task_id, expected_version, "task_cancelled", change)

    def _terminal_time(self, task: dict[str, Any]) -> datetime:
        raw = task.get("terminal_at")
        if raw:
            return datetime.fromisoformat(raw)
        history = self.get_history(task["id"])
        terminal_event = next(
            (event for event in reversed(history) if event["type"] in {"task_completed", "task_cancelled"}),
            None,
        )
        if terminal_event is not None:
            return datetime.fromisoformat(terminal_event["at"])
        return datetime.fromisoformat(task["updated_at"])

    def archive_task(self, task_id: str, expected_version: int, *, reason: str,
                     actor_ref: str | None = None, operation_id: str | None = None,
                     event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")
        actor_ref = _required(actor_ref, "actor_ref") if actor_ref is not None else None
        current = self.get_task(task_id)
        terminal_at = _stamp(self._terminal_time(current))
        archived_at = _stamp(self.clock())

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if task["status"] not in TERMINAL:
                raise TaskError("invalid_transition", "Архивировать можно только completed или cancelled")
            if task.get("active_run_ref") or task.get("active_claim"):
                raise TaskError("guard_failed", "Сначала остановите запуск и освободите закрепление")
            if task.get("archive"):
                raise TaskError("invalid_transition", "Задача уже архивирована")
            task["archive"] = {"archived_at": archived_at, "archived_by": actor_ref,
                                "reason": reason, "terminal_at": terminal_at}
            return {"archived_at": archived_at, "terminal_at": terminal_at, "reason": reason}

        return self._mutate(task_id, expected_version, "task_archived", change,
                            operation_id=operation_id,
                            operation_payload={"reason": reason, "actor_ref": actor_ref},
                            event_context=event_context)

    def unarchive_task(self, task_id: str, expected_version: int, *, reason: str,
                       operation_id: str | None = None,
                       event_context: dict[str, Any] | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")

        def change(task: dict[str, Any]) -> dict[str, Any]:
            archive = task.get("archive")
            if not archive:
                raise TaskError("invalid_transition", "Задача не архивирована")
            task["archive"] = None
            return {"reason": reason}

        return self._mutate(task_id, expected_version, "task_unarchived", change,
                            operation_id=operation_id,
                            operation_payload={"reason": reason}, event_context=event_context)

    def purge_task(self, task_id: str, expected_version: int, *, reason: str,
                   actor_ref: str | None = None, operation_id: str | None = None) -> dict[str, Any]:
        reason = _required(reason, "reason")
        actor_ref = _required(actor_ref, "actor_ref") if actor_ref is not None else None
        task = self.get_task(task_id)
        if task["status"] not in TERMINAL:
            raise TaskError("invalid_transition", "Физически удалять можно только завершённые или отменённые задачи")
        archive = task.get("archive")
        if not archive:
            raise TaskError("guard_failed", "Сначала архивируйте задачу")
        if task.get("active_run_ref") or task.get("active_claim"):
            raise TaskError("guard_failed", "Активный запуск или claim блокирует удаление")
        terminal_at = datetime.fromisoformat(archive["terminal_at"])
        eligible_at = _add_months(terminal_at, RETENTION_MONTHS)
        now = self.clock()
        if now < eligible_at:
            raise TaskError("retention_not_elapsed", "Срок хранения ещё не истёк",
                            eligible_at=_stamp(eligible_at), terminal_at=_stamp(terminal_at))
        if operation_id is not None:
            operation_id = _required(operation_id, "operation_id")
        fingerprint = self._operation_fingerprint("task_purged", task_id, expected_version, reason, actor_ref)
        return self.repository.purge(
            task_id, expected_version, terminal_at=_stamp(terminal_at),
            archived_at=_required(archive["archived_at"], "archived_at"), purged_at=_stamp(now),
            reason=reason, actor_ref=actor_ref, operation_id=operation_id, fingerprint=fingerprint,
        )

    def register_external_link(self, task_id: str, expected_version: int, *, tracker: str,
                               external_ref: str) -> dict[str, Any]:
        link = {"tracker": _required(tracker, "tracker"),
                "external_ref": _required(external_ref, "external_ref"), "relation": "projection"}

        def change(task: dict[str, Any]) -> dict[str, Any]:
            if link not in task["external_links"]:
                task["external_links"].append(link)
            return link

        return self._mutate(task_id, expected_version, "external_link_registered", change)
