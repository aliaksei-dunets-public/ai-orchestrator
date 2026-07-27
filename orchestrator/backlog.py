from __future__ import annotations

import time
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
