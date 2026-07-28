---
language: en
---

# ADR-0003: Workspace execution modes

- Status: accepted
- Date: 2026-07-28

## Context

Serial Task Manager permits one active task and one modifying process. Simply
increasing the number of active tasks would mix uncommitted changes,
checkpoints, and Git state in one workspace.

## Decision

Two modes are supported:

- `serial` remains the default and preserves the single-slot contract;
- `isolated_parallel` requires `run_id`, `max_workers`, and `worktree_root`.

Serial runs in the primary workspace on the user-selected current branch. Its
agent policy forbids task-branch creation or switching, task worktrees,
integration, and cleanup. It does not force a checkout of `main`; task-owned
Git lifecycle belongs only to an explicit isolated assignment.

In an isolated run, `sequence=1` executes in the main workspace. No later task
is assigned until its commit succeeds. Tasks with `sequence>=2` receive unique
branches and Git worktrees based on the verified first-task commit.

Task Registry stores run, sequence, worker limit, workspace kind, path, branch,
base commit, and commit evidence. Registry mutations use a bounded owner-aware
lock. Freshness and checkpoints are checked against the assigned workspace.

Worktree integration is explicit. A conflict, missing commit, or ownership
mismatch stops the run. Failed worktrees are preserved for recovery. Cleanup
never targets main and is allowed only after ownership-manifest validation.

## Consequences

- One workspace still permits only one writer.
- Parallelism is bounded by `max_workers` and requires Git CLI.
- Locks, worktrees, and ownership metadata are excluded from Git.
- Selecting `serial` restores historical behavior; existing registry records do
  not require migration.

## Rollback

Select `serial` to disable isolated assignment. Preserve any failed worktree for
diagnosis and remove it only through guarded cleanup after ownership review.
