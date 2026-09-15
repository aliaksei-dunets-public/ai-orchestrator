# Preparation Artifact Lifecycle and Retention Policy

> **Актуализация 2026-09-15:** положения о каноническом файловом состоянии задач, `task.yaml`, `events.jsonl` и файловом репозитории заменены [контрактом состояния и хранения](../architecture/state-and-storage.md). Источник истины — SQLite Task Manager; каталог задачи содержит Specification и Plan. Остальной текст — импортированный проектный материал, не подтверждение реализации.

**Status:** Accepted policy v0.1

## 1. Principle

Preparation produces two classes of artifacts:

```text
WORKING / TRANSIENT
Context Package
Implementation Analysis
Impact Analysis
search/tool evidence cache
agent scratch state

DURABLE
Task
Development Specification
Approved Implementation Plan
approval/readiness metadata
Task event history
```

The durable boundary intentionally compresses preparation knowledge.

---

## 2. Why not persist every intermediate artifact forever

Context and Analysis are valuable while reasoning is in progress, but making every intermediate document part of the permanent task contract creates:

```text
artifact sprawl
stale duplicated truth
larger executor context
more synchronization rules
more difficult archival/cleanup
```

The Development Specification exists specifically to preserve the useful conclusions from those stages.

---

## 3. Working artifact storage

During preparation, working artifacts may be stored under the Workflow Run:

```text
.orchestrator/runs/RUN-0042-PREP-01/
├── run.yaml
└── working/
    ├── context.json
    ├── analysis.json
    └── impact.json
```

These files are runtime state, not the public Task contract.

They may be regenerated if needed.

---

## 4. Ready-task durable storage

At `Task = ready`, normal execution requires only:

```text
.orchestrator/tasks/TASK-0042/
├── task.yaml
├── specification.md
├── plan.md
└── events.jsonl
```

Machine-readable readiness/approval metadata lives in `task.yaml` / event history / execution manifest.

The Execution Package is a small index/manifest, not a third knowledge document.

---

## 5. Default retention

Recommended v1:

```yaml
artifact_retention:
  preparation_working:
    keep_until: task_completed

  durable_task_documents:
    keep: true
```

Reason: keeping preparation working state until completion helps diagnose unexpected implementation/review issues without making it part of the executor's normal context.

After completion, working artifacts may be pruned.

---

## 6. Completion compaction

After Task completion:

```text
KEEP
Task snapshot/history
Specification
Approved Plan
Final acceptance/completion metadata

PRUNE OR ARCHIVE BY POLICY
raw Context Package
intermediate Analysis
impact scratch artifacts
tool/cache output
temporary run state
```

Do not delete durable documents merely because the Task completed.

---

## 7. Stable paths

Do not physically move completed tasks by default.

Use lifecycle state/indexing for logical archival:

```text
status: completed
```

Stable task paths prevent broken artifact references.

A future archive/export command may package completed tasks without changing canonical IDs.

---

## 8. Git policy

Projects may choose whether `.orchestrator/runs/**` is committed.

Recommended:

```text
.orchestrator/tasks/** durable docs/state → Git-trackable
.orchestrator/runs/** transient working state → normally ignored or selectively retained
```

Project Profile may override this for audit-heavy environments.

---

## 9. Re-preparation

If Execution Preflight invalidates a prepared task:

```text
ready/active
→ preparing
→ new Context/Analysis working state
→ specification revision if material
→ plan revision
→ Plan Review
→ ready
```

Old durable spec/plan versions remain represented in history even if stable task files point to the latest accepted versions.

---

## 10. Accepted decisions

1. Context/Analysis/Impact are working artifacts by default.
2. Specification and Plan are the durable preparation documents.
3. Working artifacts are not loaded into execution unless needed for diagnosis/re-preparation.
4. Default retention keeps working state until Task completion, then allows pruning.
5. Completed Task paths remain stable; logical archival uses status/indexes.
