"""SQLite-хранилище: запросы и атомарные snapshot/event/operation."""
from __future__ import annotations

import copy
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .contracts import (
    TASK_TYPES, TASK_STATUSES, TaskError, _task_id, _limit, _snapshot,
)
from .migrations import migrate_database


class SQLiteTaskRepository:
    """Atomic snapshot+event commits. SQLite is the sole operational authority."""

    def __init__(self, project_root: Path) -> None:
        try:
            self.project_root = Path(project_root).resolve(strict=True)
        except OSError as exc:
            raise TaskError("validation_failed", "Корень проекта недоступен", path=str(project_root)) from exc
        if not self.project_root.is_dir():
            raise TaskError("validation_failed", "Корень проекта должен быть каталогом")
        self.path = self.project_root / ".orchestrator/state/tasks.sqlite3"
        self._json_available: bool | None = None
        if not self.path.resolve(strict=False).is_relative_to(self.project_root):
            raise TaskError("validation_failed", "Путь хранилища выходит за пределы проекта")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TaskError("repository_failure", "Не удалось создать каталог состояния", path=str(self.path.parent)) from exc
        with self._connect() as db:
            self._migrate(db)

    @staticmethod
    def _migrate(db: sqlite3.Connection) -> None:
        migrate_database(db)

    @contextmanager
    def _connect(self):
        db = None
        try:
            db = sqlite3.connect(self.path, timeout=15)
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA busy_timeout=15000")
            if self._json_available is None:
                try:
                    db.execute("SELECT json_extract('{}', '$.archive')").fetchone()
                    self._json_available = True
                except sqlite3.OperationalError as exc:
                    if "no such function" not in str(exc).lower():
                        raise
                    self._json_available = False
            if not self._json_available:
                db.create_function("task_is_archived", 1,
                                   lambda raw: int(json.loads(raw).get("archive") is not None), deterministic=True)
            with db:
                yield db
        except sqlite3.Error as exc:
            raise TaskError("repository_failure", "Ошибка SQLite", sqlite_error=str(exc)) from exc
        finally:
            if db is not None:
                db.close()

    @contextmanager
    def read_transaction(self) -> Iterator[sqlite3.Connection]:
        """Единый read-only снимок для инфраструктурных читателей.

        Соединение живёт только внутри контекста. Сервис жизненного цикла
        не получает SQL-соединение. SQLite запрещает записи в этом контексте.
        """
        with self._connect() as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN DEFERRED")
            yield db

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
                    return _snapshot(existing[1])
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
        _task_id(task_id)
        with self._connect() as db:
            row = db.execute("SELECT body FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise TaskError("task_not_found", f"Задача не найдена: {task_id}")
        return _snapshot(row[0])

    def _filters(self, statuses: set[str] | None, task_type: str | None,
                 query: str | None, include_archived: bool) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if not isinstance(include_archived, bool):
            raise TaskError("validation_failed", "include_archived должен быть bool")
        if statuses is not None:
            if not isinstance(statuses, (set, frozenset)) or any(
                not isinstance(item, str) or item not in TASK_STATUSES for item in statuses
            ):
                raise TaskError("validation_failed", "statuses должен быть множеством допустимых статусов")
            clauses.append("status IN (" + ",".join("?" for _ in statuses) + ")" if statuses else "0")
            params.extend(sorted(statuses))
        if task_type is not None:
            if not isinstance(task_type, str) or task_type not in TASK_TYPES:
                raise TaskError("validation_failed", "Неизвестный тип задачи")
            clauses.append("type=?")
            params.append(task_type)
        if query is not None and not isinstance(query, str):
            raise TaskError("validation_failed", "query должен быть строкой")
        if query:
            clauses.append("LOWER(body) LIKE LOWER(?)")
            params.append(f"%{query}%")
        if not include_archived:
            clauses.append(self._archive_filter())
        return clauses, params

    def _archive_filter(self) -> str:
        return "json_extract(body, '$.archive') IS NULL" if self._json_available else "task_is_archived(body)=0"

    def replay_operation(self, operation_id: str, fingerprint: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT fingerprint,result FROM operations WHERE operation_id=?", (operation_id,)).fetchone()
        if row is None:
            return None
        if row[0] != fingerprint:
            raise TaskError("operation_conflict", "Идентификатор операции уже использован иначе", operation_id=operation_id)
        return _snapshot(row[1])

    def list(self, *, statuses: set[str] | None = None, task_type: str | None = None,
             query: str | None = None, limit: int | None = 100,
             cursor: str | None = None, include_archived: bool = False) -> list[dict[str, Any]]:
        _limit(limit)
        if cursor is not None:
            _task_id(cursor)
        clauses, params = self._filters(statuses, task_type, query, include_archived)
        if cursor is not None:
            clauses.append("id < ?")
            params.append(cursor)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        suffix = " LIMIT ?" if limit is not None else ""
        if limit is not None:
            params.append(limit)
        with self._connect() as db:
            rows = db.execute(f"SELECT body FROM tasks{where} ORDER BY id DESC{suffix}", params).fetchall()
        return [_snapshot(row[0]) for row in rows]

    def summary(self, *, statuses: set[str] | None = None, task_type: str | None = None,
                query: str | None = None, include_archived: bool = False) -> dict[str, Any]:
        clauses, params = self._filters(statuses, task_type, query, include_archived)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as db:
            db.execute("BEGIN DEFERRED")
            groups = db.execute(f"SELECT status,type,COUNT(*) FROM tasks{where} GROUP BY status,type", params).fetchall()
            archived = db.execute(f"SELECT COUNT(*) FROM tasks WHERE NOT ({self._archive_filter()})").fetchone()[0]
            purged = db.execute("SELECT COUNT(*) FROM purged_tasks").fetchone()[0]
        by_status: dict[str, int] = {}
        by_type: dict[str, int] = {}
        for status, kind, count in groups:
            by_status[status] = by_status.get(status, 0) + count
            by_type[kind] = by_type.get(kind, 0) + count
        return {"total": sum(by_status.values()), "by_status": by_status, "by_type": by_type,
                "include_archived": include_archived, "archived_total": archived, "purged_total": purged}

    def history(self, task_id: str, after_sequence: int = 0) -> list[dict[str, Any]]:
        if not isinstance(after_sequence, int) or isinstance(after_sequence, bool) or after_sequence < 0:
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
             "type": kind, "at": at, "payload": _snapshot(payload),
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
                    return _snapshot(existing[1])
            row = db.execute("SELECT body FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise TaskError("task_not_found", f"Задача не найдена: {task_id}")
            snapshot = _snapshot(row[0])
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
                    return _snapshot(existing[1])
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
