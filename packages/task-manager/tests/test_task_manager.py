from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from orchestrator_task_manager import TaskError, TaskManagerService


class TaskManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.current_time = datetime(2026, 9, 14, tzinfo=timezone.utc)
        self.service = TaskManagerService(self.root, clock=lambda: self.current_time)

    def create(self) -> dict:
        return self.service.create_task(
            title="Исправить расчёт", task_type="implementation", objective="Исправить сценарий X",
            original_request="Исправь расчёт X", acceptance_criteria=["X возвращает ожидаемое значение"],
        )

    def prepare(self) -> dict:
        task = self.create()
        task = self.service.start_preparation(task["id"], task["version"], "RUN-PREP-1")
        folder = self.root / ".orchestrator/tasks" / task["id"]
        folder.mkdir(parents=True)
        hashes = {}
        for role, name in (("specification", "specification.md"), ("plan", "plan.md")):
            path = folder / name
            path.write_text(f"# {role}\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[role] = digest
            task = self.service.attach_artifact(
                task["id"], task["version"], role=role, ref=f"{role}-v1",
                path=path.relative_to(self.root).as_posix(), sha256=digest,
            )
        binding = {"specification_sha256": hashes["specification"], "plan_sha256": hashes["plan"]}
        task = self.service.attach_artifact(
            task["id"], task["version"], role="plan_review", ref="review-v1",
            metadata={**binding, "status": "approved"},
        )
        task = self.service.attach_execution_package(
            task["id"], task["version"], ref="package-v1",
            specification_sha256=hashes["specification"], plan_sha256=hashes["plan"],
            prepared_source_revision="abc123",
        )
        task = self.service.link_workflow_run(
            task["id"], task["version"], run_ref="RUN-PREP-1", relation="finished"
        )
        return task

    def test_create_is_persistent_and_evented(self) -> None:
        first = self.create()
        second = self.create()
        self.assertEqual((first["id"], second["id"]), ("TASK-0001", "TASK-0002"))
        reopened = TaskManagerService(self.root)
        self.assertEqual(reopened.get_task(first["id"])["objective"], "Исправить сценарий X")
        self.assertEqual(reopened.get_history(first["id"])[0]["type"], "task_created")
        self.assertEqual([task["id"] for task in reopened.list_tasks(query="расчёт")], [second["id"], first["id"]])
        self.assertEqual(reopened.health_check(), [])

    def test_unsupported_schema_version_is_rejected_without_writes(self) -> None:
        database = self.root / ".orchestrator/state/tasks.sqlite3"
        database.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(database)
        try:
            db.execute("PRAGMA user_version=99")
        finally:
            db.close()

        with self.assertRaises(TaskError) as caught:
            TaskManagerService(self.root)

        self.assertEqual(caught.exception.code, "repository_failure")
        db = sqlite3.connect(database)
        try:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 99)
        finally:
            db.close()

    def test_operation_id_replays_result_and_rejects_different_payload(self) -> None:
        first = self.service.create_task(
            title="Идемпотентная задача", task_type="analysis", objective="Проверить повтор",
            original_request="Проверить повтор", acceptance_criteria=["Остаётся одна задача"],
            operation_id="op-create-1",
        )
        replay = self.service.create_task(
            title="Идемпотентная задача", task_type="analysis", objective="Проверить повтор",
            original_request="Проверить повтор", acceptance_criteria=["Остаётся одна задача"],
            operation_id="op-create-1",
        )
        self.assertEqual(replay["id"], first["id"])
        self.assertEqual(len(self.service.list_tasks()), 1)
        with self.assertRaisesRegex(TaskError, "уже использован"):
            self.service.create_task(
                title="Другая задача", task_type="analysis", objective="Другая цель",
                original_request="Другой запрос", acceptance_criteria=["Другой результат"],
                operation_id="op-create-1",
            )

        prepared = self.service.start_preparation(first["id"], first["version"], "RUN-1",
                                                  operation_id="op-prepare-1")
        replayed_preparation = self.service.start_preparation(
            first["id"], first["version"], "RUN-1", operation_id="op-prepare-1"
        )
        self.assertEqual(replayed_preparation["version"], prepared["version"])
        self.assertEqual(len(self.service.get_history(first["id"])), 2)

    def test_export_backup_and_restore_round_trip(self) -> None:
        first = self.create()
        export_path = self.root / "artifacts" / "tasks.json"
        backup_path = self.root / "artifacts" / "tasks.sqlite3"
        exported = self.service.export_state(export_path)
        self.assertEqual(exported["task_count"], 1)
        payload = json.loads(export_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["tasks"][0]["id"], first["id"])
        self.service.backup(backup_path)
        second = self.create()
        self.assertEqual(self.service.list_tasks(limit=None)[0]["id"], second["id"])
        restored = self.service.restore(backup_path)
        self.assertEqual(restored["schema_version"], 5)
        self.assertEqual([task["id"] for task in self.service.list_tasks(limit=None)], [first["id"]])
        self.assertTrue((self.root / ".orchestrator/state/tasks.sqlite3.pre-restore").is_file())

    def test_sql_filters_and_cursor_pagination(self) -> None:
        first = self.create()
        second = self.service.create_task(
            title="Документировать API", task_type="analysis",
            objective="Найти SQL фильтр", original_request="Найти SQL", acceptance_criteria=["Есть результат"],
        )
        third = self.service.create_task(
            title="Исправить расчёт", task_type="implementation", objective="Другая задача",
            original_request="Исправить X", acceptance_criteria=["X работает"],
        )
        page = self.service.list_tasks(limit=2)
        self.assertEqual([item["id"] for item in page], [third["id"], second["id"]])
        next_page = self.service.list_tasks(limit=2, cursor=page[-1]["id"])
        self.assertEqual([item["id"] for item in next_page], [first["id"]])
        self.assertEqual([item["id"] for item in self.service.list_tasks(task_type="implementation")], [third["id"], first["id"]])
        self.assertEqual([item["id"] for item in self.service.list_tasks(query="SQL")], [second["id"]])
        with self.assertRaises(TaskError):
            self.service.list_tasks(cursor="bad")

    def test_restore_rejects_corrupt_backup_without_changing_current_state(self) -> None:
        first = self.create()
        backup_path = self.root / "bad.sqlite3"
        backup_path.write_bytes(b"not a sqlite database")
        with self.assertRaises(TaskError) as caught:
            self.service.restore(backup_path)
        self.assertEqual(caught.exception.code, "repository_failure")
        self.assertEqual(self.service.get_task(first["id"])["id"], first["id"])

    def test_event_context_is_persisted_and_operation_is_correlation(self) -> None:
        task = self.service.create_task(
            title="Контекст", task_type="analysis", objective="Проверить события",
            original_request="Проверить события", acceptance_criteria=["Контекст виден"],
            operation_id="op-context", event_context={"actor_ref": "agent-1", "source": "router", "run_ref": "RUN-1"},
        )
        event = self.service.get_history(task["id"])[0]
        self.assertEqual(event["actor_ref"], "agent-1")
        self.assertEqual(event["source"], "router")
        self.assertEqual(event["run_ref"], "RUN-1")
        self.assertEqual(event["correlation_id"], "op-context")
        prepared = self.service.start_preparation(
            task["id"], task["version"], "RUN-CONTEXT", event_context={"actor_ref": "agent-2", "source": "runtime"}
        )
        mutation_event = self.service.get_history(task["id"])[-1]
        self.assertEqual(mutation_event["actor_ref"], "agent-2")
        self.assertEqual(mutation_event["source"], "runtime")
        self.assertIsNone(mutation_event["correlation_id"])
        with self.assertRaises(TaskError):
            self.service.create_task(
                title="Контекст", task_type="analysis", objective="x", original_request="x",
                acceptance_criteria=["x"], event_context={"unexpected": "field"},
            )

    def test_validate_detects_snapshot_mismatch_and_orphan_event(self) -> None:
        task = self.create()
        database = self.root / ".orchestrator/state/tasks.sqlite3"
        db = sqlite3.connect(database)
        try:
            raw = db.execute("SELECT body FROM tasks WHERE id=?", (task["id"],)).fetchone()[0]
            snapshot = json.loads(raw)
            snapshot["status"] = "not-a-status"
            db.execute("UPDATE tasks SET body=? WHERE id=?", (json.dumps(snapshot), task["id"]))
            db.execute("INSERT INTO events(task_id,sequence,task_version,type,at,payload) VALUES(?,?,?,?,?,?)",
                       ("TASK-9999", 1, 1, "orphan", "2026-09-15T00:00:00+00:00", "{}"))
            db.commit()
        finally:
            db.close()
        codes = {issue["code"] for issue in self.service.health_check()}
        self.assertIn("snapshot_column_mismatch", codes)
        self.assertIn("status_invalid", codes)
        self.assertIn("orphan_event", codes)

    def test_concurrent_same_operation_id_creates_one_task(self) -> None:
        def create_once() -> tuple[str, str | None]:
            service = TaskManagerService(self.root)
            try:
                result = service.create_task(
                    title="Конкурентная операция", task_type="analysis", objective="Одна запись",
                    original_request="Повтор", acceptance_criteria=["Одна задача"], operation_id="op-concurrent",
                )
                return result["id"], None
            except TaskError as exc:
                return "", exc.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _item: create_once(), (1, 2)))
        self.assertEqual({item[0] for item in results}, {"TASK-0001"})
        self.assertEqual([item[1] for item in results].count(None), 2)
        self.assertEqual(len(self.service.get_history("TASK-0001")), 1)

    def test_archive_hides_task_and_purge_requires_three_calendar_months(self) -> None:
        task = self.create()
        task = self.service.cancel_task(task["id"], task["version"], reason="Не требуется")
        task = self.service.archive_task(
            task["id"], task["version"], reason="Архивируем завершённую задачу", actor_ref="agent-1"
        )
        self.assertEqual(task["status"], "cancelled")
        self.assertEqual(self.service.list_tasks(), [])
        self.assertEqual(self.service.list_tasks(include_archived=True)[0]["id"], task["id"])
        with self.assertRaisesRegex(TaskError, "Срок хранения"):
            self.service.purge_task(task["id"], task["version"], reason="Слишком рано")

        task = self.service.unarchive_task(task["id"], task["version"], reason="Проверка возврата")
        self.assertEqual(self.service.list_tasks()[0]["id"], task["id"])
        task = self.service.archive_task(task["id"], task["version"], reason="Повторная архивация")
        self.current_time += timedelta(days=91)
        result = self.service.purge_task(
            task["id"], task["version"], reason="Истёк retention", actor_ref="admin",
            operation_id="op-purge-1",
        )
        self.assertTrue(result["purged"])
        with self.assertRaises(TaskError) as caught:
            self.service.get_task(task["id"])
        self.assertEqual(caught.exception.code, "task_not_found")
        export_path = self.root / "purge-export.json"
        exported = self.service.export_state(export_path)
        self.assertEqual(exported["purged_task_count"], 1)
        with self.assertRaises(TaskError) as caught:
            self.service.purge_task(task["id"], task["version"], reason="Повтор")
        self.assertEqual(caught.exception.code, "task_not_found")

    def test_completed_task_can_be_physically_purged(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        task = self.service.claim_task(task["id"], task["version"], worker_ref="worker-a")
        task = self.service.attach_artifact(
            task["id"], task["version"], role="readiness", ref="ready-v1",
            metadata={"status": "ready", "candidate_revision": "abc123"},
        )
        task = self.service.attach_artifact(task["id"], task["version"], role="acceptance_package", ref="accept-v1")
        task = self.service.mark_awaiting_acceptance(task["id"], task["version"])
        task = self.service.record_user_decision(
            task["id"], task["version"], decision_type="acceptance", value="approved",
            candidate_revision="abc123",
        )
        task = self.service.complete_task(task["id"], task["version"], completion_decision_ref="done-v1")
        task = self.service.archive_task(task["id"], task["version"], reason="Архив")
        self.current_time += timedelta(days=91)
        result = self.service.purge_task(task["id"], task["version"], reason="Удаление")
        self.assertTrue(result["purged"])
        with self.assertRaises(TaskError) as caught:
            self.service.get_task(task["id"])
        self.assertEqual(caught.exception.code, "task_not_found")

    def test_failed_transition_leaves_snapshot_and_history_unchanged(self) -> None:
        task = self.create()
        before = self.service.get_task(task["id"])
        before_history = self.service.get_history(task["id"])
        with self.assertRaises(TaskError):
            self.service.transition_status(task["id"], task["version"], to="blocked", reason="нет блокера")
        self.assertEqual(self.service.get_task(task["id"]), before)
        self.assertEqual(self.service.get_history(task["id"]), before_history)

    def test_ready_requires_all_evidence_and_current_documents(self) -> None:
        task = self.create()
        task = self.service.start_preparation(task["id"], task["version"], "RUN-PREP-1")
        task = self.service.link_workflow_run(task["id"], task["version"], run_ref="RUN-PREP-1", relation="finished")
        with self.assertRaisesRegex(TaskError, "plan"):
            self.service.mark_ready(task["id"], task["version"])
        self.assertEqual(self.service.get_task(task["id"])["version"], task["version"])
        prepared = self.prepare()
        path = self.root / ".orchestrator/tasks" / prepared["id"] / "plan.md"
        path.write_text("# изменённый план\n", encoding="utf-8")
        with self.assertRaisesRegex(TaskError, "изменился"):
            self.service.mark_ready(prepared["id"], prepared["version"])
        self.assertEqual(self.service.health_check(), [])

    def test_ready_does_not_require_separate_specification(self) -> None:
        task = self.create()
        task = self.service.start_preparation(task["id"], task["version"], "RUN-PLAN-ONLY")
        folder = self.root / ".orchestrator/tasks" / task["id"]
        folder.mkdir(parents=True)
        plan = folder / "plan.md"
        plan.write_text("# plan\n", encoding="utf-8")
        plan_hash = hashlib.sha256(plan.read_bytes()).hexdigest()
        task = self.service.attach_artifact(
            task["id"], task["version"], role="plan", ref="plan-v1",
            path=plan.relative_to(self.root).as_posix(), sha256=plan_hash,
        )
        task = self.service.attach_artifact(
            task["id"], task["version"], role="plan_review", ref="review-v1",
            metadata={"plan_sha256": plan_hash, "status": "approved"},
        )
        task = self.service.attach_execution_package(
            task["id"], task["version"], ref="package-v1", plan_sha256=plan_hash,
            prepared_source_revision="plan-only-v1",
        )
        task = self.service.link_workflow_run(
            task["id"], task["version"], run_ref="RUN-PLAN-ONLY", relation="finished"
        )
        ready = self.service.mark_ready(task["id"], task["version"])
        self.assertEqual(ready["status"], "ready")

    def test_claim_is_atomic_and_versioned(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        other = TaskManagerService(self.root)
        claimed = self.service.claim_task(task["id"], task["version"], worker_ref="worker-a", lease_seconds=60)
        self.assertEqual(claimed["status"], "active")
        self.assertEqual(claimed["active_claim"]["execution_package_ref"], "package-v1")
        with self.assertRaises(TaskError) as caught:
            other.claim_task(task["id"], task["version"], worker_ref="worker-b")
        self.assertEqual(caught.exception.code, "task_version_conflict")
        self.assertEqual(len(other.get_history(task["id"])), claimed["version"])

    def test_concurrent_claim_has_exactly_one_winner(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])

        def attempt(worker: str) -> str:
            service = TaskManagerService(self.root, clock=lambda: self.current_time)
            try:
                service.claim_task(task["id"], task["version"], worker_ref=worker)
                return "claimed"
            except TaskError as exc:
                return exc.code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, ("worker-a", "worker-b")))
        self.assertCountEqual(results, ["claimed", "task_version_conflict"])
        self.assertEqual(self.service.get_task(task["id"])["status"], "active")

    def test_health_check_detects_stale_ready_document(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        plan = self.root / ".orchestrator/tasks" / task["id"] / "plan.md"
        plan.write_text("# изменённый план\n", encoding="utf-8")
        issues = self.service.health_check()
        self.assertEqual([issue["code"] for issue in issues], ["ready_guard"])
        self.assertEqual(self.service.get_task(task["id"])["version"], task["version"])

    def test_expired_claim_recovery_requires_no_active_run(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        task = self.service.claim_task(task["id"], task["version"], worker_ref="worker-a", lease_seconds=60)
        claim_ref = task["active_claim"]["ref"]
        self.current_time += timedelta(seconds=61)
        with self.assertRaises(TaskError) as caught:
            self.service.renew_claim(task["id"], task["version"], claim_ref=claim_ref)
        self.assertEqual(caught.exception.code, "claim_expired")
        task = self.service.link_workflow_run(task["id"], task["version"], run_ref="RUN-EXEC-1", relation="active")
        with self.assertRaises(TaskError) as caught:
            self.service.recover_expired_claim(task["id"], task["version"])
        self.assertEqual(caught.exception.code, "guard_failed")
        task = self.service.link_workflow_run(task["id"], task["version"], run_ref="RUN-EXEC-1", relation="finished")
        task = self.service.recover_expired_claim(task["id"], task["version"])
        self.assertEqual(task["status"], "ready")
        self.assertIsNone(task["active_claim"])

    def test_blocker_prevents_readiness_and_resume(self) -> None:
        task = self.prepare()
        task = self.service.add_blocker(task["id"], task["version"], blocker_type="missing_access", summary="Нет доступа")
        self.assertEqual(task["status"], "blocked")
        with self.assertRaises(TaskError):
            self.service.transition_status(task["id"], task["version"], to="preparing", reason="retry")
        task = self.service.resolve_blocker(task["id"], task["version"], blocker_ref="BLOCK-01", resolution="Доступ восстановлен")
        task = self.service.transition_status(task["id"], task["version"], to="preparing", reason="resume")
        self.assertEqual(task["status"], "preparing")
        self.assertEqual(self.service.mark_ready(task["id"], task["version"])["status"], "ready")

    def test_completion_requires_acceptance_of_current_revision(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        task = self.service.claim_task(task["id"], task["version"], worker_ref="worker-a")
        task = self.service.attach_artifact(
            task["id"], task["version"], role="readiness", ref="ready-v1",
            metadata={"status": "ready", "candidate_revision": "commit-1"},
        )
        task = self.service.attach_artifact(task["id"], task["version"], role="acceptance_package", ref="accept-v1")
        task = self.service.mark_awaiting_acceptance(task["id"], task["version"])
        with self.assertRaises(TaskError) as caught:
            self.service.complete_task(task["id"], task["version"], completion_decision_ref="done-v1")
        self.assertEqual(caught.exception.code, "guard_failed")
        task = self.service.record_user_decision(
            task["id"], task["version"], decision_type="acceptance", value="approved",
            candidate_revision="commit-1",
        )
        task = self.service.complete_task(task["id"], task["version"], completion_decision_ref="done-v1")
        self.assertEqual(task["status"], "completed")
        with self.assertRaises(TaskError):
            self.service.cancel_task(task["id"], task["version"], reason="late")

    def test_definition_change_after_ready_invalidates_package(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        task = self.service.refine_task_definition(task["id"], task["version"], objective="Новая цель")
        self.assertEqual(task["status"], "preparing")
        self.assertNotIn("execution_package", task["artifacts"])
        self.assertEqual(task["definition_version"], 2)

    def test_paused_active_task_keeps_status_after_claim_recovery(self) -> None:
        task = self.prepare()
        task = self.service.mark_ready(task["id"], task["version"])
        task = self.service.claim_task(task["id"], task["version"], worker_ref="worker-a", lease_seconds=60)
        task = self.service.transition_status(task["id"], task["version"], to="awaiting_input", reason="question")
        self.assertEqual(task["resume_status"], "ready")
        self.current_time += timedelta(seconds=61)
        task = self.service.recover_expired_claim(task["id"], task["version"])
        self.assertEqual(task["status"], "awaiting_input")
        task = self.service.record_user_decision(task["id"], task["version"], decision_type="clarification", value="answer")
        task = self.service.transition_status(task["id"], task["version"], to="ready", reason="answered")
        self.assertEqual(task["status"], "ready")

    def test_waiting_requires_new_user_decision(self) -> None:
        task = self.prepare()
        task = self.service.record_user_decision(
            task["id"], task["version"], decision_type="scope", value="old answer"
        )
        task = self.service.transition_status(task["id"], task["version"], to="awaiting_input", reason="new question")
        with self.assertRaisesRegex(TaskError, "Нет решения"):
            self.service.transition_status(task["id"], task["version"], to="preparing", reason="resume")


if __name__ == "__main__":
    unittest.main()
