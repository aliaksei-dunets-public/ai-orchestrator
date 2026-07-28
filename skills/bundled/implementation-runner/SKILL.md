---
name: implementation-runner
description: Execute an approved Task Context plan step by step with a freshness gate, bounded retries, checkpoint recovery, and evidence; stop for scope changes, approvals, or blockers.
---

# Implementation Runner

1. Read the registered Task Context and capture its revision and baseline hash.
2. Apply the atomic `coding-discipline` skill to source, test, configuration, migration, and refactoring steps.
3. Convert the approved plan into ordered `ExecutionStep` values with explicit retry limits.
4. Resolve the checkpoint with `TaskManager.checkpoint_path(task_id)`; never construct or relocate the path manually.
5. Call `orchestrator.execution.execute_plan` with that checkpoint; never bypass the freshness gate.
6. Record non-empty evidence for every attempt and resume only from the last completed checkpoint.
7. Treat any baseline or scope change as `waiting_user`; never rewrite the approved baseline during execution.
8. Return `blocked` when progress requires unavailable authority or tooling.
