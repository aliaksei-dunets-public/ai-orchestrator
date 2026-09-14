from __future__ import annotations

import hashlib
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

    def test_ready_requires_all_evidence_and_current_documents(self) -> None:
        task = self.create()
        task = self.service.start_preparation(task["id"], task["version"], "RUN-PREP-1")
        task = self.service.link_workflow_run(task["id"], task["version"], run_ref="RUN-PREP-1", relation="finished")
        with self.assertRaisesRegex(TaskError, "specification"):
            self.service.mark_ready(task["id"], task["version"])
        self.assertEqual(self.service.get_task(task["id"])["version"], task["version"])
        prepared = self.prepare()
        path = self.root / ".orchestrator/tasks" / prepared["id"] / "plan.md"
        path.write_text("# изменённый план\n", encoding="utf-8")
        with self.assertRaisesRegex(TaskError, "изменился"):
            self.service.mark_ready(prepared["id"], prepared["version"])
        self.assertEqual(self.service.health_check(), [])

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
