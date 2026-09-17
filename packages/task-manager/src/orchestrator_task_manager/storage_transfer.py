"""Согласованный экспорт и безопасный перенос базы Task Manager."""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import suppress
from pathlib import Path
from typing import Any

from .contracts import SCHEMA_VERSION, TaskError, _snapshot
from .migrations import migrate_database
from .repository import SQLiteTaskRepository


def _temporary_path(destination: Path) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=destination.name + ".", suffix=".tmp", dir=destination.parent)
    os.close(descriptor)
    return Path(name)


def _cleanup(path: Path | None) -> None:
    if path is not None:
        with suppress(OSError):
            path.unlink(missing_ok=True)


class StorageTransfer:
    def __init__(self, repository: SQLiteTaskRepository) -> None:
        self.repository = repository

    def export_state(self, destination: Path) -> dict[str, Any]:
        """Write a deterministic, read-only JSON export of task state and events."""
        destination = Path(destination)
        if destination.resolve(strict=False) == self.repository.path.resolve():
            raise TaskError("validation_failed", "Экспорт нельзя записать поверх SQLite")
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TaskError("repository_failure", "Не удалось создать каталог экспорта", path=str(destination.parent)) from exc
        with self.repository.read_transaction() as db:
            schema_version = db.execute("PRAGMA user_version").fetchone()[0]
            tasks = [_snapshot(row[0]) for row in db.execute("SELECT body FROM tasks ORDER BY id")]
            events = []
            for task_id, sequence, task_version, kind, at, payload, actor_ref, source, correlation_id, run_ref in db.execute(
                "SELECT task_id,sequence,task_version,type,at,payload,actor_ref,source,correlation_id,run_ref FROM events ORDER BY task_id,sequence"
            ):
                events.append({"task_ref": task_id, "sequence": sequence, "task_version": task_version,
                               "type": kind, "at": at, "payload": _snapshot(payload),
                               "actor_ref": actor_ref, "source": source,
                               "correlation_id": correlation_id, "run_ref": run_ref})
            purged_tasks = [dict(zip(("task_id", "terminal_at", "archived_at", "purged_at", "reason", "actor_ref"), row))
                            for row in db.execute(
                                "SELECT task_id,terminal_at,archived_at,purged_at,reason,actor_ref FROM purged_tasks ORDER BY task_id"
                            )]
        export = {"format": "orchestrator-task-manager-export-v1", "schema_version": schema_version,
                  "tasks": tasks, "events": events, "purged_tasks": purged_tasks}
        temporary = None
        try:
            temporary = _temporary_path(destination)
            temporary.write_text(json.dumps(export, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            os.replace(temporary, destination)
        except OSError as exc:
            raise TaskError("repository_failure", "Не удалось записать экспорт", path=str(destination), os_error=str(exc)) from exc
        finally:
            _cleanup(temporary)
        return {"path": str(destination), "schema_version": schema_version,
                "task_count": len(tasks), "event_count": len(events),
                "purged_task_count": len(purged_tasks)}


    def backup(self, destination: Path) -> dict[str, Any]:
        """Create a consistent SQLite backup without changing task state."""
        destination = Path(destination)
        if destination.resolve(strict=False) == self.repository.path.resolve():
            raise TaskError("validation_failed", "Backup нельзя записать поверх рабочей БД")
        temporary = None
        source = target = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = _temporary_path(destination)
            source = sqlite3.connect(self.repository.path, timeout=15)
            target = sqlite3.connect(temporary)
            source.backup(target)
            target.close()
            target = None
            source.close()
            source = None
            self._validate_database(temporary)
            os.replace(temporary, destination)
        except (OSError, sqlite3.Error) as exc:
            raise TaskError("repository_failure", "Не удалось создать backup", path=str(destination), reason=str(exc)) from exc
        finally:
            if target is not None:
                target.close()
            if source is not None:
                source.close()
            _cleanup(temporary)
        return {"path": str(destination), "schema_version": self._database_version(destination)}


    def restore(self, source: Path) -> dict[str, Any]:
        """Validate a backup and atomically replace the active database."""
        source = Path(source)
        if not source.is_file() or source.is_symlink():
            raise TaskError("validation_failed", "Backup-файл отсутствует или является ссылкой")
        self._validate_database(source)
        current = self.repository.path
        if source.resolve() == current.resolve():
            raise TaskError("validation_failed", "Для restore нужен отдельный backup-файл")
        safety_copy = current.with_name(current.name + ".pre-restore")
        if source.resolve() == safety_copy.resolve(strict=False):
            safety_copy = current.with_name(current.name + ".pre-restore." + uuid.uuid4().hex)
        temporary = None
        safety_created = False
        try:
            temporary = _temporary_path(current)
            shutil.copy2(source, temporary)
            self._validate_database(temporary)
            staged = sqlite3.connect(temporary)
            try:
                migrate_database(staged)
            finally:
                staged.close()
            if current.exists():
                self.backup(safety_copy)
                safety_created = True
            os.replace(temporary, current)
        except (OSError, sqlite3.Error) as exc:
            raise TaskError("repository_failure", "Не удалось восстановить базу. Остановите другие процессы Task Manager и повторите restore.",
                            path=str(current), reason=str(exc),
                            safety_copy=str(safety_copy) if safety_created else None) from exc
        finally:
            _cleanup(temporary)
        return {"path": str(current), "backup": str(source),
                "safety_copy": str(safety_copy) if safety_created else None,
                "schema_version": self._database_version(current)}


    @staticmethod
    def _database_version(path: Path) -> int:
        db = None
        try:
            db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            return int(db.execute("PRAGMA user_version").fetchone()[0])
        except (sqlite3.Error, OSError) as exc:
            raise TaskError("repository_failure", "Не удалось прочитать версию SQLite", path=str(path), reason=str(exc)) from exc
        finally:
            if db is not None:
                db.close()


    @staticmethod
    def _validate_database(path: Path) -> None:
        db = None
        try:
            db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
            version = int(db.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise TaskError("repository_failure", "Неподдерживаемая версия схемы SQLite")
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise TaskError("repository_failure", "Backup SQLite не прошёл integrity_check")
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            required = {"tasks", "events", "meta"}
            if version >= 2:
                required.add("operations")
            if version >= 5:
                required.add("purged_tasks")
            if not required.issubset(tables):
                raise TaskError("repository_failure", "Backup SQLite не содержит таблицы Task Manager")
            expected_columns = {"tasks": {"id", "version", "status", "title", "type", "body"},
                                "events": {"task_id", "sequence", "task_version", "type", "at", "payload"},
                                "meta": {"key", "value"}}
            if version >= 2:
                expected_columns["operations"] = {"operation_id", "fingerprint", "result", "created_at"}
            if version >= 4:
                expected_columns["events"].update({"actor_ref", "source", "correlation_id", "run_ref"})
            if version >= 5:
                expected_columns["purged_tasks"] = {"task_id", "terminal_at", "archived_at", "purged_at", "reason", "actor_ref"}
            for table, columns in expected_columns.items():
                actual = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                if not columns.issubset(actual):
                    raise TaskError("repository_failure", "Backup SQLite содержит несовместимую таблицу", table=table)
            if db.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise TaskError("repository_failure", "Backup SQLite содержит нарушенные ссылки")
            if db.execute("SELECT value FROM meta WHERE key='next_id'").fetchone() is None:
                raise TaskError("repository_failure", "Backup SQLite не содержит счётчик ID")
        except (sqlite3.Error, OSError) as exc:
            raise TaskError("repository_failure", "Некорректный backup SQLite", sqlite_error=str(exc)) from exc
        finally:
            if db is not None:
                db.close()
