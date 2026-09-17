# Task Readiness and Execution Package

> **Актуализация 2026-09-17:** прежнее требование Specification заменено карточкой Task Manager; specification.md не обязательна. Task lifecycle — SQLite, immutable рабочие артефакты — Artifact Repository, шаг/WaitState — память Graph Runtime. Действующий минимальный [контракт подготовки](../architecture/preparation-workflow.md) останавливается на Package → Ready, не запускает исполнение. Остальной текст — импортированный проектный исходник.

**Status:** Accepted design v0.2  
**Scope:** Durable boundary between task preparation and execution

## 1. Core decision

A persisted Task is not automatically executable.

A Task becomes `ready` only after preparation produces two durable documents and approves the Plan against the Specification.

```text
USER REQUEST
      ↓
Task Creator
      ↓
TaskManagerService
      ↓
TASK = created / preparing
      ↓
Context
      ↓
Analysis + Impact
      ↓
Development Specification
      ↓
Planning
      ↓
Implementation Plan
      ↓
Plan Review
      ↓ approved
Execution Package manifest
      ↓
TASK = ready
```

`ready` is a durable handoff boundary.

---

## 2. Durable knowledge documents

The task folder contains:

```text
.orchestrator/tasks/TASK-0042/
├── task.yaml
├── specification.md
├── plan.md
└── events.jsonl
```

The executor contract is:

```text
Task
+
Specification
+
Approved Plan
```

Context/Analysis/Impact are preparation working state, not normal executor inputs.

---

## 3. Meaning of lifecycle states

```text
created
→ persisted, preparation not started

preparing
→ Context/Analysis/Specification/Planning/Plan Review are running

ready
→ current Specification + approved Plan are bound into an executable package

active
→ an executor claimed the Task

awaiting_input
→ user input is required

blocked
→ hard blocker prevents progress

awaiting_acceptance
→ engineering work finished; user acceptance pending

completed
→ completion policy satisfied

cancelled
→ explicitly cancelled
```

---

## 4. Ready guard

Required:

```text
Development Specification exists and is sufficient
Implementation Plan exists
Plan Review = approved
Plan Review approval matches current Specification + Plan hashes
Execution Package exists
prepared source revision recorded
no blocking blocker
```

Raw Context/Analysis existence is not a readiness requirement after successful Specification synthesis.

---

## 5. Execution Package

`Execution Package` is a compact machine-readable manifest. It does not duplicate the two durable documents.

```yaml
execution_package:
  id: EXEC-PKG-0042-v2
  task_ref: TASK-0042

  specification_ref: SPEC-0042-v1
  specification_path: .orchestrator/tasks/TASK-0042/specification.md
  specification_hash: sha256:...

  plan_ref: PLAN-0042-v2
  plan_path: .orchestrator/tasks/TASK-0042/plan.md
  plan_hash: sha256:...

  plan_review_ref: PLAN-REVIEW-0042-v2
  prepared_source_revision: abc123

  target_workflow: development
  entrypoint: execution_preflight

  readiness:
    status: ready
```

---

## 6. Ready Task snapshot

```yaml
task:
  id: TASK-0042
  status: ready

  problem_statement: >
    Payment calculation is incorrect for scenario X.

  objective: >
    Correct payment calculation while preserving existing valid behavior.

  artifacts:
    specification: SPEC-0042-v1
    plan: PLAN-0042-v2
    plan_review: PLAN-REVIEW-0042-v2
    execution_package: EXEC-PKG-0042-v2

  execution:
    target_workflow: development
    handoff_mode: deferred
    prepared_source_revision: abc123
```

---

## 7. Handoff modes

```text
immediate
→ current runtime may claim after `ready`

deferred
→ stop at `ready`; async executor may claim later
```

Both modes produce exactly the same durable handoff.

---

## 8. Zero-conversation executor

A later executor must not require preparation conversation history.

Normal startup context:

```text
Task
Specification
Plan
Project Profile
current project/repository state
```

If critical information exists only in raw Context/Analysis, preparation is incomplete.

---

## 9. Freshness

The package binds preparation to:

```yaml
prepared_source_revision: abc123
```

Execution Preflight checks whether the Specification/Plan remain valid against the current source revision.

If not:

```text
return to preparing
→ refresh Context/Analysis as needed
→ new Specification version if material
→ new Plan version
→ Plan Review
→ new Execution Package
→ ready
```

---

## 10. Accepted decisions

1. `ready` requires Specification + approved Plan.
2. Context/Analysis are not normal durable execution dependencies.
3. Execution Package is a manifest, not a third knowledge document.
4. Approval binds exact Specification and Plan versions/hashes.
5. Deferred execution starts from Task + Specification + Plan.
6. Material Specification change invalidates the Plan and readiness package.
