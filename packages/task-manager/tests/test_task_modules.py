"""Регрессии API, направления зависимостей и транзакционной границы."""
from __future__ import annotations

import ast
import inspect
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

import orchestrator_task_manager as package
from orchestrator_task_manager import contracts, migrations, repository, service
from orchestrator_task_manager import task_manager as legacy


class TaskModuleTests(unittest.TestCase):
    def test_legacy_and_package_imports_are_identical(self) -> None:
        for name, module in (("TaskError", contracts),
                             ("SQLiteTaskRepository", repository),
                             ("TaskManagerService", service)):
            self.assertIs(getattr(package, name), getattr(legacy, name))
            self.assertIs(getattr(package, name), getattr(module, name))
        for name in ("TASK_ID", "SCHEMA_VERSION", "ARTIFACT_ROLES", "TERMINAL",
                     "TASK_TYPES", "TASK_STATUSES", "RETENTION_MONTHS"):
            self.assertIs(getattr(legacy, name), getattr(contracts, name))
        self.assertIs(legacy._sha256, service._sha256)
        self.assertIs(legacy._create_schema_v1, migrations._create_schema_v1)
        namespace = {}
        exec("from orchestrator_task_manager.task_manager import *", namespace)
        self.assertIs(namespace["TASK_ID"], contracts.TASK_ID)
        self.assertIs(namespace["TaskManagerService"], service.TaskManagerService)
        error = contracts.TaskError("validation_failed", "Проверка", field="title")
        self.assertIsInstance(error, legacy.TaskError)
        self.assertEqual(error.as_dict()["details"], {"field": "title"})

    def test_public_parameter_contracts_match_pre_split_snapshot(self) -> None:
        expected = json.loads((Path(__file__).parent / "fixtures" / "public_signatures.json")
                              .read_text(encoding="utf-8"))
        for cls in (repository.SQLiteTaskRepository, service.TaskManagerService):
            tree = ast.parse(inspect.getsource(cls))
            methods = {node.name: {"arguments": ast.unparse(node.args),
                                   "returns": ast.unparse(node.returns) if node.returns else None}
                       for node in tree.body[0].body
                       if isinstance(node, ast.FunctionDef)
                       and (not node.name.startswith("_") or node.name == "__init__")}
            for name, signature in expected[cls.__name__].items():
                self.assertEqual(methods[name], signature, f"{cls.__name__}.{name}")
            additions = set(methods) - set(expected[cls.__name__])
            self.assertEqual(additions, {"read_transaction"}
                             if cls is repository.SQLiteTaskRepository else set())

    def test_dependency_layers_do_not_import_facade_or_service_upward(self) -> None:
        root = Path(service.__file__).parent
        allowed = {
            "contracts": set(), "migrations": {"contracts"},
            "repository": {"contracts", "migrations"},
            "storage_transfer": {"contracts", "migrations", "repository"},
            "diagnostics": {"contracts", "repository"},
            "service": {"contracts", "repository", "storage_transfer", "diagnostics"},
        }
        for name, dependencies in allowed.items():
            tree = ast.parse((root / f"{name}.py").read_text(encoding="utf-8"))
            actual = {node.module for node in ast.walk(tree)
                      if isinstance(node, ast.ImportFrom) and node.level}
            self.assertLessEqual(actual, dependencies, name)
        tree = ast.parse(inspect.getsource(service))
        self.assertFalse(any(isinstance(node, ast.Import)
                             and any(alias.name == "sqlite3" for alias in node.names)
                             for node in ast.walk(tree)))
        self.assertFalse(any(isinstance(node, ast.Attribute)
                             and isinstance(node.value, ast.Attribute)
                             and node.value.attr == "repository" and node.attr.startswith("_")
                             for node in ast.walk(tree)))

    def test_read_transaction_rejects_writes_and_closes_connection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = package.TaskManagerService(Path(directory))
            task = manager.create_task(title="T", task_type="analysis", objective="O",
                                       original_request="R", acceptance_criteria=["A"])
            with manager.repository.read_transaction() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)
                self.assertTrue(db.in_transaction)
            with self.assertRaises(sqlite3.ProgrammingError):
                db.execute("SELECT 1")
            with self.assertRaises(package.TaskError) as caught:
                with manager.repository.read_transaction() as db:
                    db.execute("DELETE FROM tasks")
            self.assertEqual(caught.exception.code, "repository_failure")
            self.assertEqual(manager.get_task(task["id"]), task)
            self.assertEqual(len(manager.get_history(task["id"])), 1)
            changed = manager.update_metadata(task["id"], task["version"], title="После чтения")
            self.assertEqual(changed["version"], 2)

    def test_diagnostics_keep_one_snapshot_across_concurrent_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = package.TaskManagerService(root)
            task = manager.create_task(title="T", task_type="analysis", objective="O",
                                       original_request="R", acceptance_criteria=["A"])
            with closing(sqlite3.connect(manager.repository.path)) as db:
                db.execute("PRAGMA journal_mode=WAL")
            other = package.TaskManagerService(root)
            original = manager.repository.read_transaction

            class InterleavedConnection:
                def __init__(self, db):
                    self.db = db

                def execute(self, sql, *args):
                    if sql.startswith("SELECT task_id,COUNT(*)"):
                        other.update_metadata(task["id"], task["version"], title="Новая версия")
                    return self.db.execute(sql, *args)

            @contextmanager
            def read_transaction():
                with original() as db:
                    yield InterleavedConnection(db)

            with patch.object(manager.repository, "read_transaction", read_transaction):
                self.assertEqual(manager.health_check(), [])
            self.assertEqual(other.get_task(task["id"])["version"], 2)


if __name__ == "__main__":
    unittest.main()
