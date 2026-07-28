from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Literal


LoopStatus = Literal["empty", "limit", "waiting_user", "blocked", "failed", "completed"]


@dataclass(frozen=True)
class BacklogLimits:
    max_tasks: int
    max_seconds: float
    max_steps: int

    def __post_init__(self) -> None:
        if self.max_tasks < 1 or self.max_seconds <= 0 or self.max_steps < 1:
            raise ValueError("Every backlog limit must be explicitly positive")


@dataclass(frozen=True)
class TaskRun:
    task_id: str
    status: Literal["done", "waiting_user", "blocked", "failed"]
    steps: int
    commit_evidence: str | None = None


@dataclass(frozen=True)
class BacklogResult:
    status: LoopStatus
    tasks: tuple[TaskRun, ...]
    steps: int
    reason: str


@dataclass(frozen=True)
class AssignedTask:
    task_id: str
    workspace_kind: Literal["main", "worktree"]
    workspace_path: str


def run_backlog(
    *,
    limits: BacklogLimits,
    claim_next: Callable[[], str | None],
    execute_task: Callable[[str, int], TaskRun],
    commit_task: Callable[[TaskRun], str],
    complete_task: Callable[[str, str], None],
    monotonic: Callable[[], float] = time.monotonic,
) -> BacklogResult:
    started = monotonic()
    runs: list[TaskRun] = []
    steps = 0
    while len(runs) < limits.max_tasks:
        if monotonic() - started >= limits.max_seconds or steps >= limits.max_steps:
            return BacklogResult("limit", tuple(runs), steps, "time or step budget reached")
        task_id = claim_next()
        if task_id is None:
            status: LoopStatus = "empty" if not runs else "completed"
            return BacklogResult(status, tuple(runs), steps, "backlog is empty")
        remaining = limits.max_steps - steps
        run = execute_task(task_id, remaining)
        if run.steps < 0 or run.steps > remaining:
            return BacklogResult("failed", tuple(runs), steps, "executor exceeded step budget")
        steps += run.steps
        runs.append(run)
        if run.status in {"waiting_user", "blocked", "failed"}:
            return BacklogResult(run.status, tuple(runs), steps, f"{task_id}: {run.status}")
        commit_evidence = commit_task(run)
        if not commit_evidence.strip():
            return BacklogResult("failed", tuple(runs), steps, f"{task_id}: missing commit evidence")
        complete_task(task_id, commit_evidence)
    return BacklogResult("limit", tuple(runs), steps, "task budget reached")


def run_isolated_backlog(
    *,
    limits: BacklogLimits,
    max_workers: int,
    claim_next: Callable[[], AssignedTask | None],
    execute_task: Callable[[AssignedTask, int], TaskRun],
    commit_task: Callable[[TaskRun, AssignedTask], str],
    integrate_task: Callable[[TaskRun, AssignedTask, str], str],
    complete_task: Callable[[str, str], None],
    monotonic: Callable[[], float] = time.monotonic,
) -> BacklogResult:
    if not 2 <= max_workers <= 16:
        raise ValueError("isolated max_workers must be between 2 and 16")
    started = monotonic()
    runs: list[TaskRun] = []
    steps = 0

    bootstrap = claim_next()
    if bootstrap is None:
        return BacklogResult("empty", (), 0, "backlog is empty")
    if bootstrap.workspace_kind != "main":
        return BacklogResult("failed", (), 0, "isolated run must bootstrap in main")
    first = execute_task(bootstrap, limits.max_steps)
    runs.append(first)
    steps += first.steps
    if first.steps < 0 or steps > limits.max_steps:
        return BacklogResult("failed", tuple(runs), steps, "executor exceeded step budget")
    if first.status != "done":
        return BacklogResult(first.status, tuple(runs), steps, f"{first.task_id}: {first.status}")
    first_commit = commit_task(first, bootstrap)
    if not first_commit.strip():
        return BacklogResult("failed", tuple(runs), steps, f"{first.task_id}: missing commit evidence")
    first_integration = integrate_task(first, bootstrap, first_commit)
    if not first_integration.strip():
        return BacklogResult("failed", tuple(runs), steps, f"{first.task_id}: integration failed")
    complete_task(first.task_id, first_commit)

    while len(runs) < limits.max_tasks:
        if monotonic() - started >= limits.max_seconds or steps >= limits.max_steps:
            return BacklogResult("limit", tuple(runs), steps, "time or step budget reached")
        batch: list[AssignedTask] = []
        while len(batch) < max_workers and len(runs) + len(batch) < limits.max_tasks:
            assignment = claim_next()
            if assignment is None:
                break
            if assignment.workspace_kind != "worktree":
                return BacklogResult("failed", tuple(runs), steps, "task 2+ must use a worktree")
            if assignment.workspace_path in {item.workspace_path for item in batch}:
                return BacklogResult("failed", tuple(runs), steps, "duplicate active workspace")
            batch.append(assignment)
        if not batch:
            return BacklogResult("completed", tuple(runs), steps, "backlog is empty")
        remaining = limits.max_steps - steps
        per_task_budget = max(1, remaining // len(batch))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(execute_task, assignment, per_task_budget)
                for assignment in batch
            ]
            outcomes = [future.result() for future in futures]
        for assignment, run in zip(batch, outcomes):
            runs.append(run)
            if run.task_id != assignment.task_id:
                return BacklogResult("failed", tuple(runs), steps, "executor returned the wrong task")
            if run.steps < 0 or run.steps > per_task_budget:
                return BacklogResult(
                    "failed",
                    tuple(runs),
                    steps,
                    "executor exceeded its assigned step budget",
                )
            steps += run.steps
            if steps > limits.max_steps:
                return BacklogResult("failed", tuple(runs), steps, "executor exceeded step budget")
            if run.status != "done":
                return BacklogResult(run.status, tuple(runs), steps, f"{run.task_id}: {run.status}")
            commit = commit_task(run, assignment)
            if not commit.strip():
                return BacklogResult("failed", tuple(runs), steps, f"{run.task_id}: missing commit evidence")
            integrated = integrate_task(run, assignment, commit)
            if not integrated.strip():
                return BacklogResult("failed", tuple(runs), steps, f"{run.task_id}: integration failed")
            complete_task(run.task_id, commit)
    return BacklogResult("limit", tuple(runs), steps, "task budget reached")
