# Task Tracker Adapter — Architecture

> **Актуализация 2026-09-15:** положения о каноническом файловом состоянии задач, `task.yaml`, `events.jsonl` и файловом репозитории заменены [контрактом состояния и хранения](../architecture/state-and-storage.md). Источник истины — SQLite Task Manager; каталог задачи содержит Specification и Plan. Остальной текст — импортированный проектный материал, не подтверждение реализации.

**Status:** Accepted design v0.1  
**Scope:** Optional external task-tracker projection for Task Manager state

## 1. Core decision

External trackers are **not** the canonical Task store. They are optional human-facing projections.

```text
TaskManagerService
      ↓
canonical commit
      ↓
Task Domain Event
      ↓
TaskTrackerSync
      ↓
TaskTrackerAdapter
      ↓
GitHub Issues / Plane / future tracker
```

The orchestrator remains fully functional when no external tracker is configured.

## 2. Why an adapter exists

External trackers are useful for:

```text
human-friendly issue UI
boards
search/filtering
notifications
comments
links to repository/project
team visibility
mobile access
```

But their data models must not dictate orchestrator internals. The adapter isolates provider-specific concepts from Task Manager and workflow graphs.

## 3. v1 synchronization direction

Recommended v1:

```text
canonical orchestrator
      ↓
external tracker

OUTBOUND MIRROR
```

General bidirectional state synchronization is intentionally excluded from v1 because external tracker edits could bypass lifecycle guards, acceptance rules, and conflict handling.

## 4. Projection model

Adapters receive a normalized `TaskTrackerProjection`, not the raw internal Task object.

```yaml
task_tracker_projection:
  task_ref: TASK-0042
  task_version: 8
  title: Payment cancellation validation
  status: awaiting_acceptance
  type: implementation

  summary: >
    Prevent cancellation of settled payments.

  acceptance_criteria:
    - Settled payment cannot be cancelled.
    - Rejected cancellation does not change state.

  blockers: []

  workflow_summary:
    stage: awaiting_user_acceptance

  important_artifacts:
    plan_ref: PLAN-0042-v2
    testing_ref: TESTING-0042-v1
    acceptance_package_ref: ACCEPTANCE-PACKAGE-0042-v1
```

This keeps provider formatting outside the canonical model.

## 5. Adapter port

Candidate interface:

```text
TaskTrackerAdapter

create_task_projection(projection)
update_task_projection(external_ref, projection)
append_task_event(external_ref, tracker_event)
close_task_projection(external_ref, completion_summary)
get_external_link(external_ref)
```

Potential future inbound methods are explicitly deferred:

```text
read_feedback()
read_comments()
map_external_command()
```

## 6. TaskTrackerSync

`TaskTrackerSync` is a small integration service, not a workflow subgraph.

Responsibilities:

```text
consume committed Task event
load current canonical Task
build normalized projection
resolve configured adapter
create/update external item
record external link
persist sync diagnostics
```

It must not mutate canonical Task lifecycle state except through explicit TaskManagerService commands such as registering the external link.

## 7. Failure isolation

Canonical Task mutation must succeed independently of external tracker availability.

Default:

```yaml
task_tracker:
  required: false
```

Example:

```text
Task status committed successfully
      ↓
GitHub unavailable
      ↓
Task remains valid
      ↓
tracker sync marked pending/failed
```

If a project later marks the tracker as required, its failure may create an operational blocker, but it still does not roll back the committed Task mutation.

## 8. Provider adapters

Candidate implementations:

```text
GitHubIssueTaskTrackerAdapter   # recommended first adapter
PlaneTaskTrackerAdapter         # future
LinearTaskTrackerAdapter        # future
TodoistTaskTrackerAdapter       # optional/personal use
```

Provider code stays outside Task Manager core.

## 9. GitHub Issues projection

Recommended first provider because the orchestrator repository already lives in Git.

Possible mapping:

```text
Task title
→ Issue title

Task objective + acceptance criteria
→ Issue body

Task status
→ status label / issue state

Task type
→ type label

blocker
→ blocker label + short summary

major lifecycle event
→ issue comment

completed
→ close issue
```

Suggested labels:

```text
orchestrator
status:created
status:active
status:awaiting-input
status:blocked
status:awaiting-acceptance
status:cancelled
type:implementation
type:analysis
type:investigation
type:incident
type:exploration
```

Do not mirror every internal retry, artifact version, or tool call. The external tracker should remain useful to humans.

## 10. Status mapping

External trackers may expose fewer states. Mapping is adapter-owned.

Example GitHub mapping:

```text
created              → open + status:created
active               → open + status:active
awaiting_input       → open + status:awaiting-input
blocked              → open + status:blocked
awaiting_acceptance  → open + status:awaiting-acceptance
completed            → closed
cancelled            → closed + status:cancelled
```

Internal status is never inferred back from Issue state in v1.

## 11. Milestone events

Recommended external events:

```text
task created
plan approved
implementation completed
code review passed
testing passed
blocked/unblocked
ready for acceptance
user accepted/rejected
task completed/cancelled
```

Avoid external noise from every internal orchestration step.

## 12. External identifiers

Canonical Task may store external links:

```yaml
external_links:
  - tracker: github
    external_ref: owner/repo#123
    relation: projection
```

Provider IDs never replace canonical Task IDs.

## 13. Sync state

Sync state should be separate from core lifecycle fields.

```yaml
tracker_sync:
  tracker: github
  external_ref: owner/repo#123
  last_task_version: 8
  last_event_sequence: 17
  status: synced
  last_error: null
```

Possible statuses:

```text
synced
pending
failed
disabled
```

A dedicated sync-state store is preferable to bloating `task.yaml`.

## 14. Project Profile configuration

```yaml
task_tracker:
  enabled: true
  provider: github
  mode: outbound_mirror
  required: false

  events:
    comments:
      - plan_approved
      - testing_passed
      - awaiting_acceptance
      - completed
```

When disabled, TaskManagerService continues normally.

## 15. Security

Rules:

```text
credentials never stored in task.yaml
credentials never copied into Task artifacts
logs redact secrets/tokens
least-privilege provider permissions
no hidden reasoning projected externally
```

## 16. Future inbound integration

A later version may support controlled inbound actions such as:

```text
external comment → feedback candidate
external cancel command → authorized orchestrator command
external acceptance → authorized user action
```

This requires identity, authorization, idempotency, conflict policy, command validation, and audit. Therefore general bidirectional sync is deferred.

## 17. Health Check integration

Health Check may detect:

```text
missing projection
stale projection version
wrong status label
closed external issue for active Task
duplicate tracker item
broken external link
failed sync backlog
```

Repair direction in v1:

```text
canonical Task → rebuild external projection
```

Never repair canonical Task from tracker state.

## 18. What Task Tracker Adapter must NOT do

It must not:

- own canonical Task state;
- transition canonical status directly;
- interpret code/review/testing quality;
- route graph execution;
- bypass TaskManagerService;
- expose private reasoning;
- leak provider-specific fields into the core Task schema.

## 19. Recommended v1

```yaml
task_tracker:
  enabled: optional
  provider: github
  mode: outbound_mirror
  required: false
```

## 20. Accepted decisions

1. External tracker is an optional projection.
2. TaskManagerService/filesystem remains canonical in v1.
3. Tracker sync is outbound-only in v1.
4. Adapter consumes a normalized projection model.
5. Tracker failures do not roll back canonical Task mutations.
6. GitHub Issues is the preferred first adapter.
7. Provider-specific status/labels are adapter-owned.
8. General bidirectional sync is deferred.
9. Health Check may rebuild tracker projection from canonical Task state.
