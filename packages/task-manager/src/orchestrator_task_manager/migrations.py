"""Схема SQLite и последовательные транзакционные миграции."""
from __future__ import annotations

import sqlite3
from typing import Callable
from .contracts import SCHEMA_VERSION, TaskError

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



def migrate_database(db: sqlite3.Connection) -> None:
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

