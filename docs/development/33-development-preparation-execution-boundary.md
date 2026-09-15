# Development Workflow — Preparation / Execution Boundary

> **Актуализация 2026-09-15:** положения о каноническом файловом состоянии задач, `task.yaml`, `events.jsonl` и файловом репозитории заменены [контрактом состояния и хранения](../architecture/state-and-storage.md). Источник истины — SQLite Task Manager; каталог задачи содержит Specification и Plan. Фоновый Executor Loop в этом материале — будущий вариант, не часть v1. Остальной текст — импортированный проектный материал, не подтверждение реализации.

**Status:** Accepted architecture patch v0.2

## 1. Core model

Development has two phases separated by a durable `ready` boundary.

```text
DEVELOPMENT
│
├── PREPARATION PHASE
│     ├── Context Subgraph
│     ├── Analysis Subgraph
│     │     └── Impact Analysis
│     ├── Specification Synthesis
│     ├── Specification Sufficiency Check
│     ├── Planning Subgraph
│     └── Plan Review Gate
│
│        ┌─────────────────────────────┐
│        │ specification.md persisted │
│        │ plan.md approved           │
│        │ Task status = ready         │
│        └─────────────────────────────┘
│
└── EXECUTION PHASE
      ├── Execution Preflight
      ├── Implementation Subgraph
      │     └── optional TDD
      ├── Code Review Gate
      ├── Testing Subgraph
      ├── Documentation Subgraph
      ├── Readiness Gate
      └── User Acceptance Gate
```

---

## 2. Preparation entry

A managed Development Task is persisted before deep work begins.

```text
Task Creator
   ↓
TaskManagerService.create_task()
   ↓
created
   ↓
start preparation run
   ↓
preparing
   ↓
Context
```

This gives all preparation work a stable `task_ref`.

---

## 3. Working artifacts versus durable documents

Preparation uses intermediate working artifacts:

```text
Context Package
Implementation Analysis
Impact Analysis
```

These support reasoning between stages but are not the normal executor contract.

Their conclusions are synthesized into:

```text
Development Specification
```

Planning then turns the Specification into:

```text
Approved Implementation Plan
```

At the durable boundary, the core handoff is therefore:

```text
Task
+
Specification
+
Plan
```

No previous conversation history is required.

---

## 4. Specification synthesis

```text
Task
+
Context
+
Analysis / Impact
        ↓
Specification Synthesis
        ↓
specification.md
```

Specification records:

```text
problem / objective
current and target behavior
business/domain rules
validations/invariants
change surface
contracts/dependencies
constraints
compatibility
risks/assumptions
acceptance criteria
source evidence
```

It does not contain the detailed implementation sequence.

---

## 5. Planning from Specification

Planning receives primarily:

```text
Task
Development Specification
Project Profile
previous Plan / Plan Review feedback when revising
```

It should not need raw Context or Analysis in the normal path.

If Planning discovers missing technical truth, route back to Specification preparation rather than silently inventing it.

---

## 6. Preparation exit

Preparation completes only when:

```text
Specification is sufficient
Implementation Plan exists
Plan Review approves Plan against current Specification
```

Then runtime:

```text
records Specification version/hash
records approved Plan version/hash
creates compact Execution Package manifest
records prepared source revision
transitions preparing → ready
```

`Execution Package` is an index/manifest, not a third knowledge document.

---

## 7. Immediate mode

```text
Plan Review approved
   ↓
Task = ready
   ↓
current executor claims Task
   ↓
Task = active
   ↓
Execution Preflight
   ↓
Implementation
```

Even immediate execution crosses the same durable boundary.

---

## 8. Deferred mode

```text
Plan Review approved
   ↓
Task = ready
   ↓
STOP
```

Later:

```text
Task Executor Loop
   ↓
claim ready Task
   ↓
Execution Preflight
   ↓
Implementation
```

The new AI session loads Task + Specification + Plan, not prior chat history.

---

## 9. Preparation routing

```text
Context needs input
→ awaiting_input

Analysis needs more context
→ Context expansion

Specification insufficient
→ Context / Analysis / User according to root cause

Planning finds spec gap
→ specification_revision_required

Plan Review changes_required
→ Planning

Plan Review specification_revision_required
→ Specification preparation

Plan Review approved
→ Execution Package + ready
```

---

## 10. Durable file layout

Recommended:

```text
.orchestrator/tasks/TASK-0042/
├── task.yaml
├── specification.md
├── plan.md
└── events.jsonl
```

Context/Analysis working state belongs to the preparation Workflow Run and follows retention policy.

---

## 11. Semantics

```text
Task
= original problem/outcome and lifecycle

Specification
= durable analyzed understanding of what must be true/change

Plan
= durable concrete implementation instructions

Execution Package
= machine-readable manifest binding Task + Spec + approved Plan + source revision
```

---

## 12. Accepted decisions

1. Development remains one lifecycle with Preparation and Execution phases.
2. Task is persisted before Context/Analysis.
3. Context/Analysis are working artifacts; Specification is their durable synthesis.
4. Specification and Plan are the two durable preparation documents.
5. Plan Review approval against the current Specification creates the readiness boundary.
6. `ready` means autonomous execution may begin without previous conversation context.
7. Immediate and deferred execution use the same durable artifacts and guards.
8. Executor receives Task + Specification + Plan by default.

---

## Execution workspace boundary

Execution phase now begins:

```text
READY
  ↓
claim/start
  ↓
Execution Preflight
  ↓
WORKSPACE RESOLUTION
  ↓
Implementation
```

v1 default:

```text
configured development branch
+
current workspace
```

A task-specific branch/worktree is used only by explicit override.
