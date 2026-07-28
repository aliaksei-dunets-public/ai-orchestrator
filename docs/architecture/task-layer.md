---
language: en
---

# Task Layer contract

## Task Creator, Task Context, Task Manager, and Task Execution

**Version:** 0.3
**Status:** normative Task Layer specification
**Language:** English

## 1. Purpose

The Task Layer turns a user request into a prepared task, registers it in a
small queue, and executes its approved workflow. It consists of Task Creator,
Task Context, Task Manager, and Task Execution Workflow.

> Task Manager knows the state of a task; it does not know how to implement it.

### 1.1. Normative boundaries

This document is the source of truth for Task Layer contracts. Architecture and
roadmap boundaries are defined by [core architecture](orchestrator-core.md) and
[project roadmap](../roadmap.md). Task Creator
coordinates atomic classification, analysis, specification, planning, review,
and validation skills; their logic does not move into Task Manager. Current
status exists only in Task Registry; evidence exists only in Task Context.

## 2. Task Creation Workflow

```text
user request
→ task classification
→ project analysis
→ brainstorming
→ scope definition
→ task specification
→ plan writing
→ plan review
→ context validation
→ Task Manager registration
```

Project analysis reads Project Context, active profiles, source and tests,
architecture documents, ADRs, security constraints, and related knowledge.
Brainstorming separates symptom from cause, evaluates alternatives, identifies
unknowns and risks, defines scope, and records decisions requiring the user.
The plan names real files, interfaces, commands, acceptance criteria, and
focused tests.

## 3. Task creation modes

### 3.1. Quick

For obvious local changes: short analysis, goal, scope, acceptance criteria,
short plan, and registration. Unresolved product or security decisions require
approval.

### 3.2. Standard

The normal mode for bugs and features: project analysis, brainstorming,
specification, detailed plan, Plan Review, and Context Validation. Approval is
required for scope, external behavior, security, or irreversible decisions.

### 3.3. Deep

For architectural, risky, or ambiguous changes: deep investigation, multiple
alternatives, ADR impact, explicit approval of the selected approach, detailed
plan, and independent review. A deep context MUST contain
`approach_approved: true` before registration.

## 4. Task Context

Drafts live in `.orchestrator/tasks/drafts/<slug>.md`. After validation and ID
allocation, the context is moved to `.orchestrator/tasks/contexts/TASK-<id>.md`.
The registered definition from the request through Open Questions is the
baseline. A semantic change increments `revision`, returns the task to
`backlog`, and requires Context Validation again. Execution Record is appended
after the baseline and does not change the task definition.

### 4.1. Task Context contract

Frontmatter uses one-level scalar YAML fields only: no anchors, tags, multiline
values, or nested collections. A standard/deep context contains the following
sections (quick may omit explicitly inapplicable sections):

```markdown
---
schema_version: 1
id: TASK-0007
revision: 1
title: Example task
type: feature
mode: standard
risk: medium
created_by: task-creation-workflow
---

# TASK-0007 — Example task
## User Request
## Goal
## Problem or Need
## Current Behavior
## Expected Behavior
## Analysis
## Selected Approach
## Alternatives Considered
## Scope
## Affected Components
## Acceptance Criteria
## Constraints
## Risks
## Implementation Plan
## Plan Review
## Open Questions

# Execution Record
```

Critical open questions are forbidden at registration. Empty sections must be
marked inapplicable with a reason. The execution record may contain factual
changes, tests, task/code/security review, user decision, documentation,
memory/knowledge, and finalization evidence.

### 4.2. Single source of status

Task Context never stores the current operational status. Task Registry is the
only status authority.

## 5. Task Registry

The first-version registry is `.orchestrator/tasks/tasks.json`:

```json
{
  "schema_version": 1,
  "next_id": 3,
  "tasks": [{
    "id": "TASK-0002",
    "title": "Implement Task Manager",
    "status": "in_progress",
    "context": "contexts/TASK-0002.md",
    "status_note": "CLI implementation in progress",
    "created_at": "2026-07-26T12:35:00+02:00",
    "updated_at": "2026-07-26T13:10:00+02:00"
  }]
}
```

`next_id` is monotonic and never reused. `context` is an exact POSIX path below
`.orchestrator/tasks/`; traversal is forbidden. `status_note` is a string or
null and timestamps are RFC 3339 with a timezone. Array order is queue order.
Only `backlog` tasks are candidates for `next` and `claim-next`.

Registry state, temporary files, locks, and checkpoints are operational state
and are excluded from Git. The core repository excludes the complete
`.orchestrator/` tree; target onboarding creates fresh target-owned state while
leaving canonical memory and Knowledge Graph stores visible to Git. Contexts
are versioned only when they belong to an explicitly versioned target project.

## 6. Task Manager

Task Manager registers validated contexts, allocates IDs, lists and reads
tasks, selects the next task, claims a task, validates transitions, changes
status and notes, and validates registry integrity. It does not brainstorm,
plan, implement, test, review, update documentation, update memory, or commit.

## 7. Statuses and transitions

Statuses are `backlog`, `in_progress`, `waiting_user`, `blocked`, `done`, and
`cancelled`. Planning, testing, review, and security review are workflow steps,
not statuses.

```text
backlog       → in_progress | cancelled
in_progress   → waiting_user | blocked | done | cancelled
waiting_user  → in_progress | blocked | cancelled
blocked       → backlog | in_progress | cancelled
```

`done` and `cancelled` are terminal. `waiting_user → done` is forbidden: the
workflow must resume, finalize, commit, and then complete the task with a valid
receipt.

## 8. Active-task rule

Serial mode is the default. It allows one active task and one modifying Task
Manager process. `in_progress` occupies the slot; `waiting_user` also occupies
it unless configuration explicitly permits backlog continuation. `blocked` does
not occupy it, but it cannot resume while another task owns the slot.

## 9. Task Manager CLI

The preferred interface is:

```bash
python .orchestrator/bin/task.py <command>
```

### 9.0. Workspace execution modes

`serial` preserves the default single-active-task behavior in the primary
workspace and retains the user-selected current branch. A serial agent does not
create or switch to a task branch or worktree, and it does not integrate or
clean up task-owned Git state. Explicit `isolated_parallel` requires `run_id`,
`max_workers` from 2 through 16, and `worktree_root`. Sequence 1 runs in main
only after clean and freshness checks. Its confirmed commit becomes the base for
sequence 2+; each later task receives a unique branch and worktree.

Assignments contain `mode`, `run_id`, `sequence`, `max_workers`,
`workspace_kind`, `workspace_path`, `branch`, `base_commit`, and
`commit_evidence`. Legacy assignments without these fields remain valid serial
records. Owner-aware locking serializes registry read-modify-write operations.
Live locks are never overwritten; stale locks fail closed until recovered.
Conflicts or missing commits stop the run and preserve the worktree. Cleanup
checks ownership and never removes main or a failed worktree automatically.

### 9.1. Commands

```bash
python .orchestrator/bin/task.py register --context drafts/task.md
python .orchestrator/bin/task.py list --json
python .orchestrator/bin/task.py show TASK-0003
python .orchestrator/bin/task.py next --json
python .orchestrator/bin/task.py claim-next --json
python .orchestrator/bin/task.py claim-next --json --mode isolated_parallel --run-id RUN --max-workers 2 --worktree-root .orchestrator/worktrees --repository-root .
python .orchestrator/bin/task.py assignment TASK-0003 --json
python .orchestrator/bin/task.py status TASK-0003 waiting_user --note "Need approval"
python .orchestrator/bin/task.py block TASK-0003 --note "Blocked by dependency"
python .orchestrator/bin/task.py resume TASK-0003
python .orchestrator/bin/task.py cancel TASK-0003
python .orchestrator/bin/task.py validate --json
```

`claim-next` atomically selects the first backlog task, checks the active slot,
marks it in progress, and returns its context. Specialized commands validate
the same transition table. Concurrent writers are outside the serial contract.

### 9.2. Machine output

Successful output has `{ "ok": true, "task": { ... } }`. Failure has
`{ "ok": false, "error": { "code": "...", "message": "..." } }`.

### 9.3. Exit codes

`0` success; `1` general error; `2` task not found; `3` invalid transition;
`4` corrupt registry; `5` active-task conflict; `6` no available task;
`7` invalid execution-mode configuration; `8` workspace/commit/ownership gate
failure; `9` live registry lock.

### 9.4. Write reliability

The CLI validates the registry and transition, writes a same-directory
temporary file, flushes and fsyncs it, publishes with `os.replace`, and cleans
up an unpublished temporary file. Registration validates context and registry
as one recoverable single-writer operation. Validation reports orphan contexts
and records without contexts but does not repair them automatically.

## 10. Task Execution Workflow

```text
claim → fresh context → implement plan → design/run tests
→ required reviews → security review → documentation
→ documentation/knowledge/memory finalization → receipt → commit → complete
```

Every route receives a fresh bounded context pack before analysis and
implementation. Empty stores are valid no-ops. Execution evidence is bounded,
attempts have a hard limit, checkpoints keep compact head/tail and digests, and
the receipt binds task ID, context revision, baseline hash, checkpoint, and
changed paths. Missing or stale receipts block completion.

Independent review is an optional workflow step admitted at most once for deep,
high/critical, security-, migration-, persistence-, public-API-, irreversible-,
or challenged-blocking work. Its immutable request is read-only and contains
only task scope, acceptance criteria, bounded context, changed paths, diff
summary, and test evidence. The active platform's `review_isolation` capability
routes the request to a native adapter or the same-agent clean-context fallback.

## 11. Backlog Loop

The loop is finite: it has task/time/step limits, stop conditions, one commit
per task, an independent result per task, and one session report after the loop
stops. A waiting-user, blocked, failed-finalization, or workflow error stops the
loop before the next claim.

## 12. Platform adaptation

The Task Layer uses platform-neutral contracts. Shell, Git, worktree,
interaction, approval, and telemetry behavior is supplied by platform profiles.

## 13. Task Layer Health Check

Health verifies context frontmatter and required sections, registry schema and
paths, legal statuses/transitions, one-active-task rules, orphan contexts,
checkpoint ownership, assignment/worktree invariants, and CLI JSON/error
contracts. Strict mode fails on `ERROR` and `CRITICAL` findings.

## 14. Test strategy

- Unit tests cover parsing, transitions, IDs, locks, checkpoints, and CLI helpers.
- Contract tests cover schemas, registry, context, exit codes, assignments, and
  receipt bindings.
- Scenario tests cover creation, execution, waiting-user, blocked recovery,
  serial mode, isolated worktrees, finalization, and empty stores.

## 15. Task Layer roadmap

| Milestone | Scope |
| --- | --- |
| T0 | Contracts |
| T1 | Read-only Task Manager |
| T2 | Registration |
| T3 | State management |
| T4 | Quick Task Creator |
| T5 | Standard Task Creator |
| T6 | Plan Review and Context Validation |
| T7 | Execution integration |
| T8 | Backlog Loop |
| T9 | Platform validation |

These milestones refine the product roadmap and do not create a parallel
backlog.

## 16. Out of scope for the first version

SQLite or an external database, a web UI or Kanban board, multiple writers in
serial mode, complex dependencies or subtasks, time estimates, and automatic
translation of external projects.
