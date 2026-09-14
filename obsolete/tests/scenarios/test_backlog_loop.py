from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.backlog import (
    BacklogLimits,
    FinalizationRun,
    TaskRun,
    run_backlog,
)
from orchestrator.task_manager import TaskManager
from tests.finalization_support import write_ready_receipt


class BacklogLoopScenarioTests(unittest.TestCase):
    def test_all_limits_are_mandatory(self) -> None:
        with self.assertRaises(ValueError):
            BacklogLimits(0, 10, 10)
        with self.assertRaises(ValueError):
            BacklogLimits(1, 0, 10)
        with self.assertRaises(ValueError):
            BacklogLimits(1, 10, 0)

    def _run(self, statuses: list[str], max_tasks: int = 10):
        queue = [f"TASK-{index:04d}" for index in range(1, len(statuses) + 1)]
        status_by_id = dict(zip(queue, statuses))
        events: list[str] = []

        def claim():
            return queue.pop(0) if queue else None

        def execute(task_id: str, remaining: int) -> TaskRun:
            events.append(f"execute:{task_id}")
            return TaskRun(task_id, status_by_id[task_id], 1)

        def commit(run: TaskRun) -> str:
            events.append(f"commit:{run.task_id}")
            return f"commit-{run.task_id}"

        def finalize(run: TaskRun) -> FinalizationRun:
            events.append(f"finalize:{run.task_id}")
            return FinalizationRun("completed", f"receipt-{run.task_id}")

        def complete(task_id: str, evidence: str, receipt: str) -> None:
            events.append(f"complete:{task_id}:{evidence}:{receipt}")

        def finalize_session(result) -> None:
            events.append(f"session:{result.status}")

        result = run_backlog(
            limits=BacklogLimits(max_tasks, 60, 100),
            claim_next=claim,
            execute_task=execute,
            finalize_task=finalize,
            commit_task=commit,
            complete_task=complete,
            finalize_session=finalize_session,
        )
        return result, events

    def test_empty_limit_waiting_blocked_and_failure_matrix(self) -> None:
        empty, _ = self._run([])
        limited, events = self._run(["done", "done"], max_tasks=1)
        waiting, waiting_events = self._run(["waiting_user", "done"])
        blocked, _ = self._run(["blocked", "done"])
        failed, _ = self._run(["failed", "done"])
        self.assertEqual(empty.status, "empty")
        self.assertEqual(limited.status, "limit")
        self.assertEqual(
            events,
            [
                "execute:TASK-0001",
                "finalize:TASK-0001",
                "commit:TASK-0001",
                "complete:TASK-0001:commit-TASK-0001:receipt-TASK-0001",
                "session:limit",
            ],
        )
        self.assertEqual(waiting.status, "waiting_user")
        self.assertEqual(waiting_events, ["execute:TASK-0001", "session:waiting_user"])
        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(failed.status, "failed")

    def test_successful_two_task_run_commits_before_complete(self) -> None:
        result, events = self._run(["done", "done"])
        self.assertEqual(result.status, "completed")
        self.assertEqual(
            events,
            [
                "execute:TASK-0001",
                "finalize:TASK-0001",
                "commit:TASK-0001",
                "complete:TASK-0001:commit-TASK-0001:receipt-TASK-0001",
                "execute:TASK-0002",
                "finalize:TASK-0002",
                "commit:TASK-0002",
                "complete:TASK-0002:commit-TASK-0002:receipt-TASK-0002",
                "session:completed",
            ],
        )

    def test_finalization_waiting_user_prevents_commit_and_complete(self) -> None:
        events: list[str] = []
        result = run_backlog(
            limits=BacklogLimits(1, 60, 10),
            claim_next=lambda: "TASK-0001",
            execute_task=lambda task_id, remaining: TaskRun(task_id, "done", 1),
            finalize_task=lambda run: FinalizationRun(
                "waiting_user", reason="memory approval required"
            ),
            commit_task=lambda run: events.append("commit") or "commit",
            complete_task=lambda task_id, commit, receipt: events.append("complete"),
            finalize_session=lambda result: events.append("session"),
        )
        self.assertEqual(result.status, "waiting_user")
        self.assertEqual(events, ["session"])

    def test_finalization_exception_fails_before_commit(self) -> None:
        events: list[str] = []
        result = run_backlog(
            limits=BacklogLimits(1, 60, 10),
            claim_next=lambda: "TASK-0001",
            execute_task=lambda task_id, remaining: TaskRun(task_id, "done", 1),
            finalize_task=lambda run: (_ for _ in ()).throw(
                ValueError("invalid receipt")
            ),
            commit_task=lambda run: events.append("commit") or "commit",
            complete_task=lambda task_id, commit, receipt: events.append("complete"),
            finalize_session=lambda result: events.append("session"),
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("invalid receipt", result.reason)
        self.assertEqual(events, ["session"])

    def test_complete_after_commit_creates_no_tracked_git_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tasks = root / ".orchestrator/tasks"
            tasks.mkdir(parents=True)
            (root / ".gitignore").write_text(
                ".orchestrator/tasks/tasks.json\n"
                ".orchestrator/tasks/*.tmp\n"
                ".orchestrator/tasks/checkpoints/\n"
                ".orchestrator/tasks/finalization/\n",
                encoding="utf-8",
            )
            context = tasks / "contexts" / "TASK-0001.md"
            context.parent.mkdir()
            context.write_text(
                "---\n"
                "schema_version: 1\n"
                "id: TASK-0001\n"
                "revision: 1\n"
                "title: Committed task\n"
                "type: feature\n"
                "mode: quick\n"
                "risk: low\n"
                "created_by: task-creation-workflow\n"
                "---\n\n"
                "# TASK-0001 — Committed task\n\n"
                "# Execution Record\n\n"
                "Status: completed.\n",
                encoding="utf-8",
            )
            checkpoints = tasks / "checkpoints"
            checkpoints.mkdir()
            checkpoint = checkpoints / "TASK-0001.checkpoint.lock"
            checkpoint.write_text("checkpoint", encoding="utf-8")
            registry = {
                "schema_version": 1,
                "next_id": 2,
                "tasks": [
                    {
                        "id": "TASK-0001",
                        "title": "Committed task",
                        "status": "in_progress",
                        "context": "contexts/TASK-0001.md",
                        "status_note": None,
                        "created_at": "2026-07-27T00:00:00+00:00",
                        "updated_at": "2026-07-27T00:00:00+00:00",
                    }
                ],
            }
            (tasks / "tasks.json").write_text(json.dumps(registry), encoding="utf-8")

            def git(*args: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["git", *args],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    check=True,
                )

            git("init", "-q")
            git("config", "user.email", "orchestrator@example.invalid")
            git("config", "user.name", "Orchestrator Acceptance")
            git("add", ".")
            git("commit", "-q", "-m", "implementation commit")
            self.assertEqual(git("status", "--porcelain").stdout, "")
            TaskManager(tasks).complete(
                "TASK-0001",
                finalization_receipt=write_ready_receipt(tasks, "TASK-0001"),
            )
            self.assertFalse(checkpoint.exists())
            self.assertEqual(git("status", "--porcelain").stdout, "")
