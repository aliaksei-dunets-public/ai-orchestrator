# Task Manager Service — Architecture

> **Актуализация 2026-09-15:** положения о каноническом файловом состоянии задач, `task.yaml`, `events.jsonl` и файловом репозитории заменены [контрактом состояния и хранения](../architecture/state-and-storage.md). Источник истины — SQLite Task Manager; каталог задачи содержит Specification и Plan. Остальной текст — импортированный проектный материал, не подтверждение реализации.

**Status:** Accepted design v0.1  
**Scope:** Persistent task state for the AI Orchestrator  
**Исторический вариант хранения (заменён):** Git-friendly filesystem repository

## 1. Core decision

`Task Manager` is not an AI agent and not a workflow subgraph. It is a deterministic application service with a stable API.

```text
Task Creator
     ↓
TaskManagerService
     ↓
TaskRepository
     ↓
FilesystemTaskRepository
```

The service owns task state and state invariants. It does **not** decide which Development Workflow node runs next.

## 2. Responsibility split

```text
Task Creator
→ understands the request and produces WHAT must be achieved

TaskManagerService
→ persists and protects Task state

Graph Runtime
→ controls workflow execution and routing

Workflow nodes/subgraphs
→ produce artifacts/results

Readiness / Completion logic
→ determines whether transition prerequisites are satisfied

TaskManagerService
→ persists the resulting lifecycle transition
```

Canonical rule:

> Task Creator reasons. Task Manager stores and guards state. Graph Runtime orchestrates execution.

## 3. Task state is not workflow state

Task lifecycle remains coarse-grained, but now includes the durable preparation/execution boundary:

```text
created
preparing
ready
active
awaiting_input
blocked
awaiting_acceptance
completed
cancelled
```

Meaning:

```text
created             → persisted, preparation not started
preparing           → Context/Analysis/Specification/Planning/Plan Review are running
ready               → current Specification + approved Plan are bound in an Execution Package; task may be claimed
active              → execution phase is claimed/running
awaiting_input      → user input is required
blocked             → hard blocker prevents progress
awaiting_acceptance → technical work finished; user acceptance pending
completed           → completion policy satisfied
cancelled           → explicitly cancelled
```

Exact workflow execution state is stored separately:

```yaml
task:
  id: TASK-0042
  status: ready

workflow_run:
  id: RUN-0042-PREP-01
  task_ref: TASK-0042
  workflow: development
  phase: preparation
  state: completed
```

A later execution run may be:

```yaml
workflow_run:
  id: RUN-0042-EXEC-01
  task_ref: TASK-0042
  workflow: development
  phase: execution
  current_node: implementation
  state: running
```

This prevents Task Manager from becoming a duplicate state machine for Development Workflow.

## 4. Canonical ownership

For v1, the orchestrator owns canonical Task state.

```text
CANONICAL
TaskManagerService
      ↓
Filesystem Task Store
      ↓
Git history

OPTIONAL PROJECTION
Committed Task event
      ↓
TaskTrackerSync
      ↓
TaskTrackerAdapter
      ↓
GitHub Issues / Plane / future tracker
```

External tracker state must not silently override canonical orchestrator state.

## 5. Filesystem layout

Recommended v1 canonical Task layout:

```text
.orchestrator/
├── tasks/
│   ├── TASK-0001/
│   │   ├── task.yaml
│   │   ├── specification.md
│   │   ├── plan.md
│   │   └── events.jsonl
│   └── TASK-0002/
│       ├── task.yaml
│       ├── specification.md
│       ├── plan.md
│       └── events.jsonl
│
└── runs/
    ├── RUN-0001.yaml
    └── RUN-0002.yaml
```

Ownership:

```text
.orchestrator/tasks/** → TaskManagerService / TaskRepository
.orchestrator/runs/**  → Graph Runtime / Workflow Run Store
```

Context/Analysis working artifacts belong to Workflow Run storage/retention policy. They are not required durable Task documents.

Task Manager may reference Workflow Runs, but must not mutate current graph node/retry/routing state.

## 6. Task snapshot

`task.yaml` is the current normalized Task snapshot.

```yaml
id: TASK-0042
version: 11

title: Fix payment calculation
type: implementation
status: ready

source:
  type: user_request
  original_request_ref: REQUEST-0042

definition_version: 3

problem_statement: >
  Payment calculation is incorrect for scenario X.

objective: >
  Correct payment calculation while preserving existing valid behavior.

acceptance_criteria:
  - id: AC-01
    text: Scenario X returns the expected payment result.

constraints: []

execution:
  target_workflow: development
  handoff_mode: deferred
  prepared_source_revision: abc123
  active_claim_ref: null

workflow:
  active_run_ref: null
  history:
    - RUN-0042-PREP-01

artifacts:
  specification: SPEC-0042-v1
  plan: PLAN-0042-v2
  plan_review: PLAN-REVIEW-0042-v2
  execution_package: EXEC-PKG-0042-v2
  implementation: null
  code_review: null
  testing: null
  documentation: null
  readiness: null
  acceptance_package: null
  user_acceptance: null
  completion_decision: null

blockers: []
user_decisions: []
external_links: []

created_at: timestamp
updated_at: timestamp
```

Task stores artifact references, not full artifact payloads.

For `ready` Tasks, `specification`, approved `plan`, and `execution_package` references are required. The package binds exact Specification/Plan versions or hashes.

## 7. Event history

`events.jsonl` is append-only audit history.

```json
{"sequence":1,"event":"task_created","task_version":1,"at":"..."}
{"sequence":2,"event":"status_changed","from":"created","to":"preparing","task_version":2,"at":"..."}
{"sequence":8,"event":"artifact_attached","role":"plan_review","ref":"PLAN-REVIEW-0042-v2","task_version":8,"at":"..."}
{"sequence":10,"event":"execution_package_attached","ref":"EXEC-PKG-0042-v1","task_version":10,"at":"..."}
{"sequence":11,"event":"status_changed","from":"preparing","to":"ready","task_version":11,"at":"..."}
{"sequence":12,"event":"task_claimed","claim_ref":"CLAIM-0042-01","task_version":12,"at":"..."}
```

Uses:

```text
audit
debugging
health check
external tracker synchronization
future analytics
claim/recovery diagnostics
```

The log is not a conversation transcript.

## 8. Concurrency and versioning

Every mutation uses optimistic versioning.

```text
caller read version 7
        ↓
command expected_version = 7
        ↓
repository version == 7?
   ├── yes → commit version 8
   └── no  → version conflict
```

Example error:

```yaml
error:
  type: task_version_conflict
  expected: 7
  actual: 8
```

This prevents agents from silently overwriting concurrent changes.

## 9. Repository transaction boundary

Logical mutation:

```text
validate command
      ↓
validate invariant / transition
      ↓
persist snapshot
      ↓
append domain event
      ↓
publish committed event
```

Candidate repository operation:

```text
commit(new_snapshot, event, expected_version)
```

Filesystem implementation should use:

```text
per-task lock
temporary file
atomic rename/replace
monotonic task version
monotonic event sequence
```

Health Check detects snapshot/event inconsistencies. A future SQLite repository may provide stronger native transactions without changing TaskManagerService.

## 10. Task status transitions

Candidate v1 lifecycle:

```text
created
   ↓ start preparation
preparing
   ├──────────────► awaiting_input ───► preparing
   ├──────────────► blocked ──────────► preparing
   └── Plan Review approved
          ↓
        ready
          ↓ claim
        active
          ├──────────────► awaiting_input ───► active
          ├──────────────► blocked ──────────► active
          ├──────────────► awaiting_acceptance
          │                    ├── rejected / more validation → active
          │                    ├── deferred → awaiting_acceptance
          │                    └── approved → completed
          └──────────────► completed
                           only when policy permits
```

If Execution Preflight invalidates the prepared package:

```text
active
  ↓ release execution claim / route back
preparing
  ↓ refresh Context/Analysis → Specification → Plan → Plan Review
ready
```

Cancellation:

```text
created / preparing / ready / active /
awaiting_input / blocked / awaiting_acceptance
→ cancelled
```

`completed` and `cancelled` are terminal in v1.

## 11. Transition guards

Task Manager does not inspect source code or rerun tests. It checks trusted evidence references.

### `created → preparing`

Require a valid persisted Task and a preparation Workflow Run (or preparation-start command).

### `preparing → ready`

Require:

```text
Development Specification exists and is sufficient
Implementation Plan exists
Plan Review = approved for current Specification + Plan binding
Execution Package exists and binds current Specification/Plan hashes
no blocking blocker
```

This is the durable execution-readiness guard.

### `ready → active`

Must occur through an atomic execution claim, not a generic status edit.

Require:

```text
current Execution Package exists
no active claim
no blocking blocker
```

### `active → preparing`

Allowed when Execution Preflight determines that the Specification and/or Plan must be refreshed. The active claim must be safely released/closed.

### `active → awaiting_acceptance`

Require:

```text
ReadinessResult = ready
AcceptancePackage exists
```

### `awaiting_acceptance → completed`

When user acceptance is required:

```text
UserAcceptance = approved
accepted candidate revision = current candidate revision
no blocking blockers
```

### `blocked → preparing|active|ready`

Return target depends on the phase that owned the blocker. Require all blocking blockers resolved.

### `awaiting_input → preparing|active`

Require explicit user-answer/decision evidence and resume the phase that requested input.

## 12. Blockers and user decisions

Blockers are first-class structured records:

```yaml
blocker:
  id: BLOCK-01
  type: missing_access
  summary: Integration environment is unavailable.
  blocking: true
  status: open
  evidence_refs:
    - TESTING-0042-v1
```

Important user decisions are also persisted:

```text
requirement clarification
accepted risk
acceptance approval/rejection
scope decision
cancellation
```

## 12A. Task definition refinement

During `preparing`, Context/Analysis may reveal that the initial problem contract needs evidence-based refinement.

Allowed refinements may include:

```text
problem statement normalization
objective clarification
acceptance criteria
constraints
non-blocking assumptions
```

The original user request remains immutable. Every refinement is versioned and recorded as a Task event.

After the Task becomes `ready`, material definition changes invalidate readiness and return the Task to `preparing`.

The Task Manager validates lifecycle rules; the reasoning for the refinement comes from preparation artifacts.

## 13. API boundary

Recommended commands:

```text
create_task()
start_preparation()
refine_task_definition()
update_metadata()
transition_status()
attach_artifact()
attach_execution_package()
add_blocker()
resolve_blocker()
record_user_decision()
link_workflow_run()
claim_task()
renew_claim()
release_claim()
complete_task()
cancel_task()
register_external_link()
```

Recommended queries:

```text
get_task()
list_tasks()
list_executable_tasks()
get_history()
get_claim()
```

`claim_task()` is the only normal path from `ready → active`.

Agents must use the service API/capability rather than editing Task files directly.

## 14. Domain events and side effects

After canonical commit, Task Manager emits a domain event:

```text
TaskCreated
TaskStatusChanged
ArtifactAttached
BlockerAdded
TaskCompleted
```

Consumers may include:

```text
Task Tracker synchronization
metrics
audit
health monitoring
future notification service
```

External side effects occur **after** canonical persistence. Tracker failure does not roll back a successfully committed Task mutation by default.

## 15. Storage portability

TaskManagerService depends on `TaskRepository`, not filesystem APIs.

Candidate implementations:

```text
FilesystemTaskRepository   # v1
SQLiteTaskRepository       # future
DatabaseTaskRepository     # future
RemoteTaskRepository       # future
```

## 16. Git policy

The filesystem store is Git-friendly and gains:

```text
history
backup
branch awareness
diffability
portability
developer visibility
```

But Git is not the mutation API. Direct file edits are not normal Task Manager operations.

## 17. Health Check integration

Health Check should verify:

```text
task schema
duplicate task IDs
version monotonicity
event sequence integrity
broken artifact refs
invalid status transitions
preparing task without preparation run
ready task without current Specification or approved Plan Review
ready task without Execution Package
ready task with invalid prepared revision metadata
active task without active execution claim
multiple active claims for one task
expired claim with live Workflow Run
completed task without completion evidence
awaiting_acceptance without acceptance package
blocked task without open blocker
stale Workflow Run references
tracker projection drift
```

Health Check may recommend rebuilding external projections or repairing infrastructure metadata, but must not fabricate missing review/test evidence.

## 18. What Task Manager must NOT do

It must not:

- analyze implementation architecture;
- select the next graph node;
- perform Planning or Review;
- execute tests;
- interpret code quality;
- modify production source code;
- treat external tracker state as canonical;
- accept arbitrary direct file edits as normal API usage.

## 19. Recommended v1 configuration

```yaml
task_manager:
  implementation: internal_service

  repository:
    type: filesystem
    root: .orchestrator/tasks

  optimistic_versioning: true
  event_history: true

  direct_file_mutation:
    allowed: false

  external_tracker:
    canonical: false
```

## 20. Accepted decisions

1. Task Manager is a deterministic service/API.
2. It is not a subgraph and not an AI agent.
3. Task state and Workflow Run state are separate.
4. Filesystem repository is canonical for v1.
5. Task files are Git-friendly.
6. Agents mutate Task only through TaskManagerService.
7. State transitions are protected by deterministic guards.
8. Artifacts are referenced, not embedded.
9. Task history is append-only.
10. External trackers are optional projections only.
11. Repository and tracker integrations are hidden behind ports/adapters.
12. Task preparation and execution are separated by the first-class `ready` state.
13. `preparing → ready` requires a sufficient Specification, an approved Plan bound to that Specification, plus an Execution Package.
14. `ready → active` requires an atomic execution claim.
15. Immediate and deferred execution use the same readiness/claim semantics.
