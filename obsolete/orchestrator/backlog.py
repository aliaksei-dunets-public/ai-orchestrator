from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
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
    post_loop_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssignedTask:
    task_id: str
    workspace_kind: Literal["main", "worktree"]
    workspace_path: str


@dataclass(frozen=True)
class FinalizationRun:
    status: Literal["completed", "waiting_user", "blocked", "failed"]
    receipt_evidence: str | None = None
    reason: str | None = None


def run_backlog(
    *,
    limits: BacklogLimits,
    claim_next: Callable[[], str | None],
    execute_task: Callable[[str, int], TaskRun],
    finalize_task: Callable[[TaskRun], FinalizationRun],
    commit_task: Callable[[TaskRun], str],
    complete_task: Callable[[str, str, str], None],
    finalize_session: Callable[[BacklogResult], None],
    monotonic: Callable[[], float] = time.monotonic,
) -> BacklogResult:
    started = monotonic()
    runs: list[TaskRun] = []
    steps = 0

    def finish(result: BacklogResult) -> BacklogResult:
        try:
            finalize_session(result)
            return result
        except Exception as exc:
            return replace(
                result,
                post_loop_errors=(f"{type(exc).__name__}: {exc}",),
            )

    while len(runs) < limits.max_tasks:
        if monotonic() - started >= limits.max_seconds or steps >= limits.max_steps:
            return finish(
                BacklogResult("limit", tuple(runs), steps, "time or step budget reached")
            )
        task_id = claim_next()
        if task_id is None:
            status: LoopStatus = "empty" if not runs else "completed"
            return finish(
                BacklogResult(status, tuple(runs), steps, "backlog is empty")
            )
        remaining = limits.max_steps - steps
        run = execute_task(task_id, remaining)
        if run.steps < 0 or run.steps > remaining:
            return finish(
                BacklogResult(
                    "failed", tuple(runs), steps, "executor exceeded step budget"
                )
            )
        steps += run.steps
        runs.append(run)
        if run.status in {"waiting_user", "blocked", "failed"}:
            return finish(
                BacklogResult(
                    run.status, tuple(runs), steps, f"{task_id}: {run.status}"
                )
            )
        try:
            finalization = finalize_task(run)
        except Exception as exc:
            return finish(
                BacklogResult(
                    "failed",
                    tuple(runs),
                    steps,
                    f"{task_id}: finalization error: {type(exc).__name__}: {exc}",
                )
            )
        if finalization.status != "completed":
            return finish(
                BacklogResult(
                    finalization.status,
                    tuple(runs),
                    steps,
                    finalization.reason
                    or f"{task_id}: finalization {finalization.status}",
                )
            )
        receipt = (finalization.receipt_evidence or "").strip()
        if not receipt:
            return finish(
                BacklogResult(
                    "failed",
                    tuple(runs),
                    steps,
                    f"{task_id}: missing finalization receipt",
                )
            )
        commit_evidence = commit_task(run)
        if not commit_evidence.strip():
            return finish(
                BacklogResult(
                    "failed",
                    tuple(runs),
                    steps,
                    f"{task_id}: missing commit evidence",
                )
            )
        complete_task(task_id, commit_evidence, receipt)
    return finish(BacklogResult("limit", tuple(runs), steps, "task budget reached"))


def run_isolated_backlog(
    *,
    limits: BacklogLimits,
    max_workers: int,
    claim_next: Callable[[], AssignedTask | None],
    execute_task: Callable[[AssignedTask, int], TaskRun],
    finalize_task: Callable[[TaskRun, AssignedTask], FinalizationRun],
    commit_task: Callable[[TaskRun, AssignedTask], str],
    integrate_task: Callable[[TaskRun, AssignedTask, str], str],
    complete_task: Callable[[str, str, str], None],
    finalize_session: Callable[[BacklogResult], None],
    monotonic: Callable[[], float] = time.monotonic,
) -> BacklogResult:
    if not 2 <= max_workers <= 16:
        raise ValueError("isolated max_workers must be between 2 and 16")
    started = monotonic()
    runs: list[TaskRun] = []
    steps = 0

    def finish(result: BacklogResult) -> BacklogResult:
        try:
            finalize_session(result)
            return result
        except Exception as exc:
            return replace(
                result,
                post_loop_errors=(f"{type(exc).__name__}: {exc}",),
            )

    bootstrap = claim_next()
    if bootstrap is None:
        return finish(BacklogResult("empty", (), 0, "backlog is empty"))
    if bootstrap.workspace_kind != "main":
        return finish(
            BacklogResult("failed", (), 0, "isolated run must bootstrap in main")
        )
    first = execute_task(bootstrap, limits.max_steps)
    runs.append(first)
    steps += first.steps
    if first.steps < 0 or steps > limits.max_steps:
        return finish(
            BacklogResult(
                "failed", tuple(runs), steps, "executor exceeded step budget"
            )
        )
    if first.status != "done":
        return finish(
            BacklogResult(
                first.status, tuple(runs), steps, f"{first.task_id}: {first.status}"
            )
        )
    try:
        first_finalization = finalize_task(first, bootstrap)
    except Exception as exc:
        return finish(
            BacklogResult(
                "failed",
                tuple(runs),
                steps,
                f"{first.task_id}: finalization error: {type(exc).__name__}: {exc}",
            )
        )
    if first_finalization.status != "completed":
        return finish(
            BacklogResult(
                first_finalization.status,
                tuple(runs),
                steps,
                first_finalization.reason
                or f"{first.task_id}: finalization {first_finalization.status}",
            )
        )
    first_receipt = (first_finalization.receipt_evidence or "").strip()
    if not first_receipt:
        return finish(
            BacklogResult(
                "failed",
                tuple(runs),
                steps,
                f"{first.task_id}: missing finalization receipt",
            )
        )
    first_commit = commit_task(first, bootstrap)
    if not first_commit.strip():
        return finish(
            BacklogResult(
                "failed",
                tuple(runs),
                steps,
                f"{first.task_id}: missing commit evidence",
            )
        )
    first_integration = integrate_task(first, bootstrap, first_commit)
    if not first_integration.strip():
        return finish(
            BacklogResult(
                "failed", tuple(runs), steps, f"{first.task_id}: integration failed"
            )
        )
    complete_task(first.task_id, first_commit, first_receipt)

    while len(runs) < limits.max_tasks:
        if monotonic() - started >= limits.max_seconds or steps >= limits.max_steps:
            return finish(
                BacklogResult("limit", tuple(runs), steps, "time or step budget reached")
            )
        batch: list[AssignedTask] = []
        while len(batch) < max_workers and len(runs) + len(batch) < limits.max_tasks:
            assignment = claim_next()
            if assignment is None:
                break
            if assignment.workspace_kind != "worktree":
                return finish(
                    BacklogResult(
                        "failed", tuple(runs), steps, "task 2+ must use a worktree"
                    )
                )
            if assignment.workspace_path in {item.workspace_path for item in batch}:
                return finish(
                    BacklogResult(
                        "failed", tuple(runs), steps, "duplicate active workspace"
                    )
                )
            batch.append(assignment)
        if not batch:
            return finish(
                BacklogResult("completed", tuple(runs), steps, "backlog is empty")
            )
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
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        "executor returned the wrong task",
                    )
                )
            if run.steps < 0 or run.steps > per_task_budget:
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        "executor exceeded its assigned step budget",
                    )
                )
            steps += run.steps
            if steps > limits.max_steps:
                return finish(
                    BacklogResult(
                        "failed", tuple(runs), steps, "executor exceeded step budget"
                    )
                )
            if run.status != "done":
                return finish(
                    BacklogResult(
                        run.status,
                        tuple(runs),
                        steps,
                        f"{run.task_id}: {run.status}",
                    )
                )
            try:
                finalization = finalize_task(run, assignment)
            except Exception as exc:
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        f"{run.task_id}: finalization error: "
                        f"{type(exc).__name__}: {exc}",
                    )
                )
            if finalization.status != "completed":
                return finish(
                    BacklogResult(
                        finalization.status,
                        tuple(runs),
                        steps,
                        finalization.reason
                        or f"{run.task_id}: finalization {finalization.status}",
                    )
                )
            receipt = (finalization.receipt_evidence or "").strip()
            if not receipt:
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        f"{run.task_id}: missing finalization receipt",
                    )
                )
            commit = commit_task(run, assignment)
            if not commit.strip():
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        f"{run.task_id}: missing commit evidence",
                    )
                )
            integrated = integrate_task(run, assignment, commit)
            if not integrated.strip():
                return finish(
                    BacklogResult(
                        "failed",
                        tuple(runs),
                        steps,
                        f"{run.task_id}: integration failed",
                    )
                )
            complete_task(run.task_id, commit, receipt)
    return finish(BacklogResult("limit", tuple(runs), steps, "task budget reached"))
