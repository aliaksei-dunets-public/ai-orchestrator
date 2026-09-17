from __future__ import annotations

import json
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TaskCliTests(unittest.TestCase):
    def cli(self, root, *arguments, ok=True):
        result = subprocess.run([sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", str(root),
                                 *arguments], capture_output=True, text=True, encoding="utf-8", check=False)
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)["result"]
        self.assertEqual(result.returncode, 2, result.stderr)
        return json.loads(result.stderr)["error"]

    def create(self, root):
        return self.cli(root, "create", "--title", "Задача", "--objective", "Проверить", "--request", "Запрос",
                        "--criterion", "Результат проверен")

    def test_resources_are_available_without_creating_project_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "resources"],
                capture_output=True, text=True, encoding="utf-8", check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = json.loads(result.stdout)["result"]
            self.assertEqual(set(paths), {"contract", "usage", "example_skill"})
            self.assertTrue(all(Path(path).is_file() for path in paths.values()))
            self.assertFalse((Path(directory) / ".orchestrator").exists())

    def test_create_and_list_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            environment = os.environ.copy()
            environment["PYTHONIOENCODING"] = "cp1252"
            create = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "create",
                 "--title", "Задача", "--objective", "Проверить", "--request", "Сделай проверку",
                 "--criterion", "Проверка прошла"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            self.assertEqual(json.loads(create.stdout)["result"]["id"], "TASK-0001")
            listing = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "list", "--status", "created"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertEqual(len(json.loads(listing.stdout)["result"]), 1)
            validation = subprocess.run(
                [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", directory, "validate"],
                capture_output=True, text=True, encoding="utf-8", env=environment, check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stderr)
            self.assertEqual(json.loads(validation.stdout), {"ok": True, "result": []})

    def test_full_guarded_lifecycle_through_cli(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self.create(root)
            task_id = task["id"]
            self.cli(root, "start", task_id, "--run-ref", "test-session-preparation")
            folder = root / ".orchestrator/tasks" / task_id
            folder.mkdir(parents=True)
            plan = folder / "plan.md"
            plan.write_text("# Проверяемый план", encoding="utf-8")
            digest = hashlib.sha256(plan.read_bytes()).hexdigest()
            self.cli(root, "artifact", task_id, "--role", "plan", "--ref", "plan",
                     "--path", plan.relative_to(root).as_posix(), "--sha256", digest)
            self.assertEqual(self.cli(root, "document", task_id), "# Проверяемый план")
            self.cli(root, "artifact", task_id, "--role", "plan_review", "--ref", "review", "--metadata",
                     json.dumps({"status": "approved", "plan_sha256": digest}))
            self.cli(root, "execution-package", task_id, "--ref", "package", "--plan-sha256", digest,
                     "--prepared-source-revision", "source-rev")
            self.cli(root, "run-link", task_id, "--run-ref", "test-session-preparation", "--relation", "finished")
            self.cli(root, "ready", task_id)
            task = self.cli(root, "claim", task_id, "--worker-ref", "agent", "--lease-seconds", "60")
            claim = task["active_claim"]["ref"]
            self.cli(root, "renew", task_id, "--claim-ref", claim, "--lease-seconds", "60")
            self.cli(root, "release", task_id, "--claim-ref", claim, "--to", "ready", "--reason", "pause")
            self.cli(root, "claim", task_id, "--worker-ref", "agent")
            self.cli(root, "artifact", task_id, "--role", "readiness", "--ref", "ready", "--metadata",
                     json.dumps({"status": "ready", "candidate_revision": "rev-1"}))
            self.cli(root, "artifact", task_id, "--role", "acceptance_package", "--ref", "accept-package")
            task = self.cli(root, "awaiting-acceptance", task_id)
            version = str(task["version"])
            error = self.cli(root, "accept", task_id, "--candidate-revision", "old", "--completion-decision-ref", "done", ok=False)
            self.assertEqual(error["code"], "guard_failed")
            self.assertEqual(self.cli(root, "show", task_id)["user_decisions"], [])
            arguments = ("accept", task_id, "--candidate-revision", "rev-1", "--completion-decision-ref", "done",
                         "--expected-version", version, "--operation-id", "accept-cli")
            completed = self.cli(root, *arguments)
            self.assertEqual(completed["status"], "completed")
            self.assertEqual(self.cli(root, *arguments), completed)
            history = self.cli(root, "history", task_id)
            self.assertEqual(len(history), completed["version"])
            self.assertEqual(self.cli(root, "validate"), [])

    def test_blockers_decisions_versions_and_archive_summary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            task = self.create(directory)
            task_id = task["id"]
            blocked = self.cli(directory, "blocker-add", task_id, "--type", "access", "--summary", "Нет доступа",
                               "--evidence-ref", "request-1")
            self.assertEqual(blocked["status"], "blocked")
            self.cli(directory, "blocker-resolve", task_id, "--blocker-ref", "BLOCK-01", "--resolution", "Доступ получен")
            self.cli(directory, "transition", task_id, "--to", "created", "--reason", "Продолжить")
            self.cli(directory, "metadata", task_id, "--title", "Новое название")
            self.cli(directory, "refine", task_id, "--objective", "Уточнённая цель", "--criterion", "Новый критерий")
            error = self.cli(directory, "cancel", task_id, "--reason", "done", "--expected-version", "1", ok=False)
            self.assertEqual(error["code"], "task_version_conflict")
            self.assertIn("hint", error["details"])
            self.cli(directory, "start", task_id, "--run-ref", "preparation")
            self.cli(directory, "transition", task_id, "--to", "awaiting_input", "--reason", "question")
            self.cli(directory, "decision", task_id, "--decision-type", "clarification", "--value", "answer")
            self.cli(directory, "run-link", task_id, "--run-ref", "preparation", "--relation", "finished")
            self.cli(directory, "transition", task_id, "--to", "preparing", "--reason", "answered")
            self.cli(directory, "cancel", task_id, "--reason", "done")
            self.cli(directory, "archive", task_id, "--reason", "hide")
            self.assertEqual(self.cli(directory, "summary")["total"], 0)
            summary = self.cli(directory, "summary", "--include-archived")
            self.assertEqual(summary["by_status"], {"cancelled": 1})
            self.assertEqual(summary["archived_total"], 1)
            self.cli(directory, "unarchive", task_id, "--reason", "show")
            self.assertEqual(self.cli(directory, "summary")["total"], 1)

    def test_parse_errors_are_json_and_do_not_create_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            for arguments in (("claim", "TASK-0001"), ("list", "--limit", "wrong"),
                              ("artifact", "TASK-0001", "--role", "testing", "--ref", "r", "--metadata", "[]"),
                              ("unknown",), ("list", "--format", "unknown")):
                with self.subTest(arguments=arguments):
                    error = self.cli(directory, *arguments, ok=False)
                    self.assertEqual(error["code"], "validation_failed")
            self.assertFalse((Path(directory) / ".orchestrator").exists())
            signatures = self.cli(directory, "api")
            self.assertIn("candidate_revision", signatures["accept_task"])
            self.assertFalse((Path(directory) / ".orchestrator").exists())

    def test_table_options_before_and_after_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.create(directory)
            for arguments in (("--project", directory, "--format", "table", "list"),
                              ("list", "--project", directory, "--format", "table"),
                              ("--format", "json", "list", "--project", directory, "--format", "table")):
                result = subprocess.run([sys.executable, "-m", "orchestrator_task_manager.task_cli", *arguments],
                                        capture_output=True, text=True, encoding="utf-8", check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("TASK-0001", result.stdout)
                self.assertIn("created", result.stdout)
                self.assertIn("Задача", result.stdout)

    def test_create_operation_id_replays_one_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            arguments = ("create", "--title", "Задача", "--objective", "Цель", "--request", "Запрос", "--criterion", "A",
                         "--operation-id", "create-cli", "--event-context", '{"actor_ref":"agent"}')
            first = self.cli(directory, *arguments)
            self.assertEqual(self.cli(directory, *arguments), first)
            self.assertEqual(self.cli(directory, "summary")["total"], 1)
            self.assertEqual(self.cli(directory, "history", first["id"])[0]["actor_ref"], "agent")

    def test_export_json_snapshot_does_not_mutate_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            active = self.create(root)
            archived = self.create(root)
            self.cli(root, "cancel", archived["id"], "--reason", "Не требуется")
            self.cli(root, "archive", archived["id"], "--reason", "Скрыть")
            before = self.cli(root, "list", "--include-archived")
            histories = {task["id"]: self.cli(root, "history", task["id"]) for task in before}
            destination = root / "новый каталог" / "задачи.json"
            for attempt in range(2):
                with self.subTest(attempt=attempt):
                    result = subprocess.run(
                        [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", str(root),
                         "export", str(destination)], capture_output=True, text=True, encoding="utf-8", check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    response = json.loads(result.stdout)
                    self.assertTrue(response["ok"])
                    self.assertEqual(response["result"]["task_count"], 2)
                    self.assertEqual(response["result"]["event_count"], sum(map(len, histories.values())))
                    self.assertEqual(response["result"]["purged_task_count"], 0)
                    snapshot = json.loads(destination.read_text(encoding="utf-8"))
                    self.assertEqual(snapshot["format"], "orchestrator-task-manager-export-v1")
                    self.assertEqual(snapshot["tasks"], sorted(before, key=lambda task: task["id"]))
                    self.assertEqual(snapshot["schema_version"], response["result"]["schema_version"])
            self.assertEqual(self.cli(root, "list", "--include-archived"), before)
            for task_id, history in histories.items():
                self.assertEqual(self.cli(root, "history", task_id), history)
            self.assertEqual(self.cli(root, "show", active["id"]), active)
            self.assertEqual(self.cli(root, "validate"), [])

    def test_export_destination_errors_are_json_and_preserve_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self.create(root)
            database = root / ".orchestrator/state/tasks.sqlite3"
            before = database.read_bytes()
            occupied = root / "occupied"
            occupied.mkdir()
            marker = occupied / "keep.txt"
            marker.write_text("Не удалять", encoding="utf-8")
            for destination, code in ((database, "validation_failed"), (occupied, "repository_failure")):
                with self.subTest(destination=destination):
                    result = subprocess.run(
                        [sys.executable, "-m", "orchestrator_task_manager.task_cli", "--project", str(root),
                         "export", str(destination)], capture_output=True, text=True, encoding="utf-8", check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, "")
                    response = json.loads(result.stderr)
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], code)
                    self.assertEqual(database.read_bytes(), before)
                    self.assertEqual(self.cli(root, "show", task["id"]), task)
            self.assertEqual(marker.read_text(encoding="utf-8"), "Не удалять")
            self.assertEqual(list(root.glob("occupied.*.tmp")), [])

    def test_transfer_commands_match_public_api_and_backup_restore_roundtrip(self) -> None:
        from orchestrator_task_manager import TaskManagerService
        from orchestrator_task_manager.task_cli import TRANSFER_COMMANDS, _parser

        self.assertEqual(TRANSFER_COMMANDS, {"export": "export_state", "backup": "backup", "restore": "restore"})
        for command, method in TRANSFER_COMMANDS.items():
            with self.subTest(command=command):
                self.assertTrue(callable(getattr(TaskManagerService, method)))
                arguments = _parser().parse_args([command, "state-copy"])
                self.assertEqual(getattr(arguments, "source" if command == "restore" else "destination"), Path("state-copy"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            task = self.create(root)
            history = self.cli(root, "history", task["id"])
            backup_path = root / "backup.sqlite3"
            backup = self.cli(root, "backup", str(backup_path))
            self.assertTrue(backup_path.is_file())
            digest = hashlib.sha256(backup_path.read_bytes()).hexdigest()
            self.cli(root, "metadata", task["id"], "--title", "Изменено после backup")
            restored = self.cli(root, "restore", str(backup_path))
            self.assertEqual(restored["schema_version"], backup["schema_version"])
            self.assertTrue(Path(restored["safety_copy"]).is_file())
            self.assertEqual(hashlib.sha256(backup_path.read_bytes()).hexdigest(), digest)
            self.assertEqual(self.cli(root, "show", task["id"]), task)
            self.assertEqual(self.cli(root, "history", task["id"]), history)
            self.assertEqual(self.cli(root, "validate"), [])


if __name__ == "__main__":
    unittest.main()
