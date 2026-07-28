from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.task_manager import TaskManager, TaskManagerError, validate_registry


DRAFT = """---
schema_version: 1
id: null
title: Test task
type: feature
mode: quick
risk: low
created_by: task-creation-workflow
---

# Test task

## Исходный запрос
Create it.

## Цель
Test lifecycle.

## Объём задачи
### Входит в scope
- Lifecycle.
### Не входит в scope
- Concurrency.

## Критерии приёмки
- Lifecycle passes.

## План реализации
- Implement.

## Открытые вопросы
- Нет.
"""


class TaskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.tasks = Path(self.temporary.name) / ".orchestrator" / "tasks"
        self.drafts = self.tasks / "drafts"
        self.drafts.mkdir(parents=True)
        self.manager = TaskManager(self.tasks)
        self.manager.initialize()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def create_draft(self, name: str = "task.md") -> Path:
        path = self.drafts / name
        path.write_text(DRAFT, encoding="utf-8")
        return path

    def test_registration_allocates_id_and_moves_context(self) -> None:
        draft = self.create_draft()
        task = self.manager.register(draft)
        self.assertEqual(task["id"], "TASK-0001")
        self.assertEqual(task["context"], "contexts/TASK-0001.md")
        self.assertFalse(draft.exists())
        context = self.tasks / "contexts" / "TASK-0001.md"
        self.assertIn("id: TASK-0001", context.read_text(encoding="utf-8"))
        self.assertIn("revision: 1", context.read_text(encoding="utf-8"))
        self.assertTrue((self.tasks / "checkpoints").is_dir())
        self.assertEqual(
            self.manager.checkpoint_path("TASK-0001"),
            self.tasks / "checkpoints" / "TASK-0001.checkpoint.lock",
        )
        self.assertEqual(validate_registry(self.tasks), [])

    def test_registration_rejects_critical_open_question(self) -> None:
        draft = self.create_draft()
        draft.write_text(DRAFT.replace("- Нет.", "- CRITICAL: choose migration."), encoding="utf-8")
        with self.assertRaises(TaskManagerError) as raised:
            self.manager.register(draft)
        self.assertIn("Critical open question", str(raised.exception))

    def test_sequential_claim_enforces_single_slot(self) -> None:
        self.manager.register(self.create_draft("one.md"))
        second = self.create_draft("two.md")
        second.write_text(DRAFT.replace("Test task", "Second task"), encoding="utf-8")
        self.manager.register(second)
        first = self.manager.claim_next()
        self.assertEqual(first["status"], "in_progress")
        with self.assertRaises(TaskManagerError) as raised:
            self.manager.claim_next()
        self.assertEqual(raised.exception.code, "ACTIVE_TASK_EXISTS")

    def test_transitions_and_terminal_rules(self) -> None:
        task = self.manager.register(self.create_draft())
        self.manager.claim_next()
        waiting = self.manager.set_status(task["id"], "waiting_user", "Need decision")
        self.assertEqual(waiting["status"], "waiting_user")
        self.manager.resume(task["id"])
        with self.assertRaises(TaskManagerError):
            self.manager.set_status(task["id"], "done")
        done = self.manager.complete(task["id"])
        self.assertEqual(done["status"], "done")
        with self.assertRaises(TaskManagerError):
            self.manager.resume(task["id"])

    def test_complete_removes_checkpoint_but_cancel_preserves_it(self) -> None:
        first = self.manager.register(self.create_draft("complete.md"))
        self.manager.claim_next()
        first_checkpoint = self.manager.checkpoint_path(first["id"])
        first_checkpoint.write_text("checkpoint", encoding="utf-8")
        self.manager.complete(first["id"])
        self.assertFalse(first_checkpoint.exists())

        second_draft = self.create_draft("cancel.md")
        second_draft.write_text(DRAFT.replace("Test task", "Cancelled task"), encoding="utf-8")
        second = self.manager.register(second_draft)
        self.manager.claim_next()
        second_checkpoint = self.manager.checkpoint_path(second["id"])
        second_checkpoint.write_text("checkpoint", encoding="utf-8")
        self.manager.cancel(second["id"], "No longer needed")
        self.assertTrue(second_checkpoint.is_file())

    def test_complete_reports_checkpoint_cleanup_warning_after_status_persists(self) -> None:
        task = self.manager.register(self.create_draft())
        self.manager.claim_next()
        checkpoint = self.manager.checkpoint_path(task["id"])
        checkpoint.write_text("checkpoint", encoding="utf-8")
        original_unlink = Path.unlink

        def failing_unlink(path: Path, *args: object, **kwargs: object) -> None:
            if path == checkpoint:
                raise PermissionError("checkpoint is in use")
            original_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", failing_unlink):
            result = self.manager.complete(task["id"])
        self.assertEqual(result["status"], "done")
        self.assertIn("cleanup_warning", result)
        self.assertEqual(self.manager.show(task["id"])["status"], "done")
        self.assertTrue(checkpoint.is_file())

    def test_complete_reports_checkpoint_path_failure_after_status_persists(self) -> None:
        task = self.manager.register(self.create_draft())
        self.manager.claim_next()
        with mock.patch.object(
            self.manager,
            "checkpoint_path",
            side_effect=TaskManagerError("GENERAL_ERROR", "unsafe checkpoint directory"),
        ):
            result = self.manager.complete(task["id"])
        self.assertEqual(result["status"], "done")
        self.assertIn("cleanup_warning", result)
        self.assertEqual(self.manager.show(task["id"])["status"], "done")

    def test_atomic_write_leaves_no_temporary_file(self) -> None:
        self.manager.register(self.create_draft())
        self.assertEqual(list(self.tasks.glob("*.tmp")), [])
        payload = json.loads((self.tasks / "tasks.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["next_id"], 2)

    def test_registration_rolls_back_context_when_registry_write_fails(self) -> None:
        draft = self.create_draft()
        original_write = self.manager._write

        def fail_write(payload: dict[str, object]) -> None:
            raise OSError("simulated persistence failure")

        self.manager._write = fail_write  # type: ignore[method-assign]
        with self.assertRaises(OSError):
            self.manager.register(draft)
        self.manager._write = original_write  # type: ignore[method-assign]
        self.assertTrue(draft.exists())
        self.assertFalse((self.tasks / "contexts" / "TASK-0001.md").exists())
        self.assertEqual(json.loads((self.tasks / "tasks.json").read_text(encoding="utf-8"))["tasks"], [])

    def test_registration_keeps_registry_valid_when_draft_cleanup_fails(self) -> None:
        draft = self.create_draft()
        original_unlink = Path.unlink

        def failing_unlink(path: Path, *args: object, **kwargs: object) -> None:
            if path == draft:
                raise PermissionError("draft is in use")
            original_unlink(path, *args, **kwargs)

        with mock.patch.object(Path, "unlink", failing_unlink):
            result = self.manager.register(draft)
        self.assertIn("cleanup_warning", result)
        self.assertEqual(self.manager.show("TASK-0001")["context"], "contexts/TASK-0001.md")
        self.assertTrue((self.tasks / "contexts" / "TASK-0001.md").is_file())
        self.assertTrue(draft.is_file())
        self.assertEqual(validate_registry(self.tasks), [])

    def test_validation_detects_orphan_and_missing_context(self) -> None:
        orphan = self.tasks / "contexts" / "TASK-0099.md"
        orphan.write_text("# orphan", encoding="utf-8")
        self.assertTrue(any(issue.code == "ORPHAN_CONTEXT" for issue in validate_registry(self.tasks)))
        orphan.unlink()
        task = self.manager.register(self.create_draft())
        (self.tasks / task["context"]).unlink()
        self.assertTrue(any(issue.code == "MISSING_CONTEXT" for issue in validate_registry(self.tasks)))

    def test_validation_rejects_legacy_context_location(self) -> None:
        task = self.manager.register(self.create_draft())
        payload = json.loads((self.tasks / "tasks.json").read_text(encoding="utf-8"))
        payload["tasks"][0]["context"] = f"{task['id']}.md"
        (self.tasks / "tasks.json").write_text(json.dumps(payload), encoding="utf-8")
        self.assertTrue(
            any(issue.code == "INVALID_CONTEXT_PATH" for issue in validate_registry(self.tasks))
        )

    def test_corrupt_json_has_exit_code_four(self) -> None:
        (self.tasks / "tasks.json").write_text("{", encoding="utf-8")
        with self.assertRaises(TaskManagerError) as raised:
            self.manager.list_tasks()
        self.assertEqual(raised.exception.exit_code, 4)
