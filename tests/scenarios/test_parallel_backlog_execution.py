from __future__ import annotations

import threading
import time
import unittest

from orchestrator.backlog import (
    AssignedTask,
    BacklogLimits,
    TaskRun,
    run_isolated_backlog,
)


class ParallelBacklogExecutionScenarioTests(unittest.TestCase):
    def test_bootstrap_commits_before_bounded_fanout(self) -> None:
        assignments = [
            AssignedTask("TASK-0001", "main", "main"),
            AssignedTask("TASK-0002", "worktree", "worktree-2"),
            AssignedTask("TASK-0003", "worktree", "worktree-3"),
        ]
        events: list[str] = []
        lock = threading.Lock()
        active = 0
        peak = 0

        def claim() -> AssignedTask | None:
            return assignments.pop(0) if assignments else None

        def execute(assignment: AssignedTask, remaining: int) -> TaskRun:
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
                events.append(f"execute:{assignment.task_id}")
            if assignment.workspace_kind == "worktree":
                time.sleep(0.02)
            with lock:
                active -= 1
            return TaskRun(assignment.task_id, "done", 1)

        def commit(run: TaskRun, assignment: AssignedTask) -> str:
            events.append(f"commit:{run.task_id}")
            return f"commit-{run.task_id}"

        def integrate(run: TaskRun, assignment: AssignedTask, commit: str) -> str:
            events.append(f"integrate:{run.task_id}")
            return commit

        def complete(task_id: str, evidence: str) -> None:
            events.append(f"complete:{task_id}")

        result = run_isolated_backlog(
            limits=BacklogLimits(3, 60, 20),
            max_workers=2,
            claim_next=claim,
            execute_task=execute,
            commit_task=commit,
            integrate_task=integrate,
            complete_task=complete,
        )
        self.assertEqual(result.status, "limit")
        self.assertEqual(peak, 2)
        bootstrap_complete = events.index("complete:TASK-0001")
        self.assertGreater(events.index("execute:TASK-0002"), bootstrap_complete)

    def test_conflict_or_missing_commit_stops_without_completion(self) -> None:
        assignments = [
            AssignedTask("TASK-0001", "main", "main"),
            AssignedTask("TASK-0002", "worktree", "worktree-2"),
        ]
        completed: list[str] = []

        result = run_isolated_backlog(
            limits=BacklogLimits(5, 60, 20),
            max_workers=2,
            claim_next=lambda: assignments.pop(0) if assignments else None,
            execute_task=lambda assignment, remaining: TaskRun(
                assignment.task_id, "done", 1
            ),
            commit_task=lambda run, assignment: (
                "bootstrap-commit" if assignment.workspace_kind == "main" else ""
            ),
            integrate_task=lambda run, assignment, commit: commit,
            complete_task=lambda task_id, evidence: completed.append(task_id),
        )
        self.assertEqual(result.status, "failed")
        self.assertEqual(completed, ["TASK-0001"])

    def test_non_main_bootstrap_fails_closed(self) -> None:
        result = run_isolated_backlog(
            limits=BacklogLimits(1, 60, 10),
            max_workers=2,
            claim_next=lambda: AssignedTask("TASK-0001", "worktree", "bad"),
            execute_task=lambda assignment, remaining: TaskRun(
                assignment.task_id, "done", 1
            ),
            commit_task=lambda run, assignment: "commit",
            integrate_task=lambda run, assignment, commit: commit,
            complete_task=lambda task_id, evidence: None,
        )
        self.assertEqual(result.status, "failed")
