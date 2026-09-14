# Task Management Integration Patch

**Status:** Accepted patch v0.2  
**Scope:** Request routing + preparation/execution handoff + external tracker projection

## 1. Updated top-level architecture

```text
USER
  ↓
REQUEST ROUTER
  │
  ├── Direct Response
  ├── Interaction
  └── Managed Work
         ↓
     TASK CREATOR
         ↓
  TASK MANAGER SERVICE
         ↓
     Task = created
         ↓
  DEVELOPMENT PREPARATION
         ↓
 Context → Analysis → Planning → Plan Review
         ↓ approved
  Execution Package
         ↓
     Task = ready
         │
      ┌──┴───────────────┐
      │                  │
  immediate           deferred
      │                  │
    claim               STOP
      │
      ▼
 DEVELOPMENT EXECUTION
```

Later deferred execution:

```text
TASK EXECUTOR LOOP
      ↓
TaskManagerService.list_executable_tasks()
      ↓
claim ready Task
      ↓
Execution Preflight
      ↓
Development Execution Phase
```

Optional external projection remains:

```text
TASK MANAGER SERVICE
      ↓ committed event
TASK TRACKER SYNC
      ↓
TASK TRACKER ADAPTER
      ↓
GitHub Issues / future provider
```

## 2. Canonical boundary

```text
TaskManagerService + TaskRepository
= source of truth for Task lifecycle and prepared artifact refs

Graph Runtime / Workflow Run Store
= source of truth for preparation/execution run state

Task Tracker
= optional external projection
```

## 3. Task creation and preparation

```text
Task Creator
      ↓
initial Task Artifact
      ↓
TaskManagerService.create_task()
      ↓
Task = created
      ↓
start preparation run
      ↓
Task = preparing
      ↓
Context
      ↓
Analysis / Impact Analysis
      ↓
Planning
      ↓
Plan Review
```

The Task exists before deep analysis so every preparation artifact has a persistent `task_ref`.

The initial Task captures the problem/outcome; preparation artifacts capture the technical understanding.

## 4. Readiness boundary

Plan Review `approved` triggers:

```text
build Execution Package
      ↓
attach Context/Analysis/Plan/Plan Review refs
      ↓
record prepared source revision
      ↓
TaskManagerService transition preparing → ready
```

`ready` means:

> The Task has enough approved technical preparation to be safely handed to an execution agent without repeating Planning by default.

## 5. Immediate execution

Immediate execution does not bypass the durable boundary:

```text
ready
 ↓ current worker claims Task
active
 ↓
Execution Preflight
 ↓
Implementation
```

## 6. Deferred execution

```text
ready
 ↓
STOP
```

Later:

```text
Task Executor Loop
 ↓
list ready Tasks
 ↓
claim_task()
 ↓
active
 ↓
Execution Preflight
```

The later executor receives Task + Execution Package and does not require previous conversation history.

## 7. Preparation interaction states

### Missing user input

```text
preparing
  ↓ needs_input
awaiting_input
  ↓ user answer recorded
preparing
```

### Blocker

```text
preparing
  ↓ blocked
blocked
  ↓ blocker resolved
preparing
```

## 8. Execution Preflight refresh

If source/project state changed since preparation:

```text
active
  ↓ Preflight says package stale
release claim
  ↓
preparing
  ↓
Context refresh / Analysis / Planning / Plan Review as needed
  ↓
new Execution Package
  ↓
ready
```

If package is fresh:

```text
active → Implementation
```

## 9. Execution lifecycle

During normal execution:

```text
active
  ↓
Implementation
  ↓
Code Review
  ↓
Testing
  ↓
Documentation
  ↓
Readiness Gate
  ↓
awaiting_acceptance
  ↓
User Acceptance
  ↓
completed
```

Rejected acceptance or additional validation returns Task to `active` and resumes the appropriate execution path.

## 10. Task Tracker integration

Recommended v1:

```yaml
task_tracker:
  enabled: optional
  provider: github
  mode: outbound_mirror
  required: false
```

Useful projected milestones now include:

```text
preparation started
plan approved
ready for execution
execution claimed
testing passed
awaiting acceptance
completed
```

Tracker state never authorizes canonical transitions.

## 11. File ownership

```text
.orchestrator/tasks/** → TaskManagerService / TaskRepository
.orchestrator/runs/**  → Graph Runtime / Workflow Run Store
source/project files   → workflow agents/tools
external tracker       → TaskTrackerAdapter projection
```

## 12. Health Check additions

Health Check should validate:

```text
Task schema
Task transition integrity
Task/event version consistency
ready Task has approved Plan Review
ready Task has Execution Package
active Task has a valid claim
Task ↔ Workflow Run references
prepared revision metadata
Final Check completion guards
tracker projection drift
tracker sync failures
```

## 13. v1 implementation order

```text
1. Task model/schema including preparing/ready
2. TaskRepository port
3. FilesystemTaskRepository
4. TaskManagerService
5. preparation/readiness transition guards
6. Execution Package contract
7. claim/lease API
8. Graph Runtime preparation/execution entrypoints
9. Execution Preflight
10. Health Check rules
11. Task Executor Loop
12. TaskTrackerAdapter port
13. GitHub Issue adapter
```

Task Tracker Adapter remains optional. Task Executor Loop is only required for deferred autonomous execution.

## 14. Accepted decisions

1. Task is persisted before deep technical preparation.
2. Preparation consists of Context, Analysis, Planning, and Plan Review.
3. Plan Review approval plus Execution Package transitions Task to `ready`.
4. `ready` is the asynchronous handoff boundary.
5. Immediate and deferred execution share identical claim/preflight semantics.
6. External executor loops claim only `ready` tasks.
7. Task Manager is infrastructure/service, not a workflow reasoning agent.
8. External tracker remains optional and outbound-only in v1.


---

## 12. Durable preparation handoff

The durable execution handoff is:

```text
Task + Development Specification + approved Implementation Plan
```

Context/Analysis are preparation working state and do not need to be loaded by the later executor.

`Execution Package` is a machine-readable manifest that binds the current Specification + Plan + approval + prepared source revision.
