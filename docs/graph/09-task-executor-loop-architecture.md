# Task Executor Loop — Architecture

**Status:** Accepted design v0.1  
**Scope:** Asynchronous execution of prepared `ready` tasks

## 1. Purpose

`Task Executor Loop` is infrastructure that picks executable Tasks from TaskManagerService and starts the appropriate workflow execution phase.

It is not an AI reasoning subgraph.

```text
TaskManagerService
      ↓
list ready tasks
      ↓
Task Executor Loop
      ↓
claim task
      ↓
Workflow Router
      ↓
Execution Preflight
      ↓
Development Execution Phase
```

---

## 2. Core responsibilities

The executor loop may:

```text
query executable tasks
select a task according to scheduling policy
atomically claim it
create/link a Workflow Run
start the configured workflow entrypoint
heartbeat/renew the claim while running
release/recover abandoned claims
```

It must not:

```text
analyze requirements
rewrite the task
skip preparation guards
approve plans
modify canonical task files directly
```

---

## 3. Executable query

Candidate query:

```yaml
query:
  type: list_executable_tasks

  filters:
    status: ready
    target_workflow: development

  limit: 10
```

Scheduling policy may later consider:

```text
priority
age
risk
project
worker capability
cost limits
```

v1 may simply select the oldest/highest-priority ready task.

---

## 4. Atomic claim

Two workers must not execute the same Task concurrently.

Recommended command:

```yaml
command:
  type: claim_task

  task_ref: TASK-0042
  expected_version: 11

  worker_ref: WORKER-03
  lease_seconds: 900
```

Successful claim atomically performs:

```text
ready → active
```

and creates a lease.

---

## 5. Claim model

```yaml
execution_claim:
  claim_id: CLAIM-0042-01
  task_ref: TASK-0042
  worker_ref: WORKER-03

  claimed_at: timestamp
  lease_until: timestamp

  execution_package_ref: EXEC-PKG-0042-v1
  task_version: 12
```

Task may have only one active execution claim in v1.

---

## 6. Lease / heartbeat

A worker periodically renews its claim:

```yaml
command:
  type: renew_claim
  claim_ref: CLAIM-0042-01
  lease_seconds: 900
```

If a worker crashes and the lease expires, recovery policy may return the Task to `ready` after verifying that no live Workflow Run owns it.

Recovery must be auditable.

---

## 7. Workflow Run creation

After claim:

```text
claim task
   ↓
create Workflow Run
   ↓
link Workflow Run to Task
   ↓
start development at execution_preflight
```

Example:

```yaml
workflow_run:
  id: RUN-0042-EXEC-01
  task_ref: TASK-0042
  workflow: development
  phase: execution
  entrypoint: execution_preflight
  state: running
```

Task Manager stores only the run reference.

Graph Runtime owns exact execution state.

---

## 7A. Durable execution inputs

After claim, the executor resolves the Execution Package and loads:

```text
Task
Development Specification
Approved Implementation Plan
Project Profile
```

The executor does not load preparation conversation history or raw Context/Analysis by default.

The Execution Package is a manifest that verifies the exact Specification/Plan hashes approved for this Task.

---

## 8. Immediate execution uses the same claim semantics

`handoff_mode: immediate` must not bypass claim/state rules.

Instead:

```text
Preparation completes
      ↓
Task = ready
      ↓
current worker claims task
      ↓
Task = active
      ↓
Execution Preflight
```

Thus synchronous and asynchronous execution share one execution contract.

---

## 9. Execution result handling

Possible high-level outcomes:

```text
completed
awaiting_input
blocked
awaiting_acceptance
execution_failed
```

The Workflow/Final Check produces the evidence; TaskManagerService persists the lifecycle transition.

The executor loop itself does not invent the resulting status.

---

## 10. Failure before workflow start

If claim succeeds but Workflow Run cannot start:

```text
record execution-start failure
      ↓
release claim / recover task according to policy
```

For safe startup failures, the Task may return to `ready`.

For ambiguous partial startup, mark recovery-required rather than launching a second worker blindly.

---

## 11. Configuration

Candidate:

```yaml
task_executor:
  enabled: true

  polling:
    interval_seconds: 30

  claim:
    lease_seconds: 900
    heartbeat_seconds: 300

  concurrency:
    max_active_tasks: 1
```

v1 should default to one active task per executor unless explicitly configured otherwise.

---

## 12. Health Check integration

Health Check should detect:

```text
ready task with invalid/missing Specification, Plan, or Execution Package
active task without active claim
expired claim with running Workflow Run
multiple active claims for one Task
active claim owned by unknown worker
ready task whose Plan Review binding does not match current Specification/Plan
orphan Workflow Run
```

---

## 13. Accepted decisions

1. Task Executor Loop is infrastructure, not a reasoning subgraph.
2. It only picks Tasks in `ready` state.
3. Claim is atomic and transitions `ready → active`.
4. Claims use leases to support crash recovery.
5. Immediate and deferred execution use the same claim contract.
6. Workflow execution begins at `execution_preflight`.
7. Task Manager owns lifecycle state; Graph Runtime owns Workflow Run state.

---

## Workspace policy

The Task Executor Loop does not automatically create a worktree in v1.

After a task is claimed:

```text
claim READY task
→ Execution Preflight
→ resolve Project Profile workspace policy
→ current_workspace by default
→ Implementation
```

An isolated `task_branch` or `task_worktree` is used only when explicitly requested/configured.

This policy can later be changed for autonomous execution without changing the Task/Workflow contracts.
