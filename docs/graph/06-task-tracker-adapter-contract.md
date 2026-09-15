# Task Tracker Adapter — Contract

> **Статус материала:** импортированный кандидат контракта. Внешний трекер является только проекцией Task Manager; он не заменяет SQLite и не входит в обязательный v1.

**Status:** Candidate v1 contract

## 1. Normalized Projection

```yaml
task_tracker_projection:
  task_ref: TASK-0042
  task_version: 8

  title: Payment cancellation validation
  type: implementation
  status: awaiting_acceptance

  summary: >
    Prevent cancellation of settled payments.

  acceptance_criteria:
    - id: AC-01
      text: Settled payment cannot be cancelled.
    - id: AC-02
      text: Rejected cancellation preserves payment state.

  blockers: []

  workflow_summary:
    current_phase: awaiting_acceptance

  important_artifacts:
    plan_ref: PLAN-0042-v2
    testing_ref: TESTING-0042-v1
    acceptance_package_ref: ACCEPTANCE-PACKAGE-0042-v1

  latest_milestones:
    - type: testing_passed
    - type: awaiting_acceptance
```

## 2. Create Projection

```yaml
request:
  type: create_task_projection
  projection: {}
```

Result:

```yaml
result:
  status: success
  external:
    provider: github
    external_ref: owner/repo#123
```

The external link is then registered through TaskManagerService.

## 3. Update Projection

```yaml
request:
  type: update_task_projection
  external_ref: owner/repo#123
  projection: {}
```

```yaml
result:
  status: success
  synced_task_version: 8
```

## 4. Append Milestone Event

```yaml
request:
  type: append_task_event
  external_ref: owner/repo#123
  event:
    type: testing_passed
    summary: Automated testing passed.
    task_version: 8
```

Provider may render this as comment/activity/timeline event.

## 5. Close Projection

```yaml
request:
  type: close_task_projection
  external_ref: owner/repo#123
  summary:
    result: completed
    acceptance_ref: USER-ACCEPTANCE-0042-v2
```

## 6. Adapter Result Envelope

```yaml
task_tracker_result:
  status:
    success | retryable_failure | permanent_failure | disabled

  provider: github
  external_ref: owner/repo#123
  retry_after: null
  error: null
```

## 7. Sync Event

Input from committed Task domain event:

```yaml
task_tracker_sync_event:
  task_ref: TASK-0042
  task_version: 8
  event_sequence: 17
  event_type: status_changed
```

Sync service loads the current canonical Task and builds a fresh projection. It must not reconstruct full current state from the event payload alone.

## 8. Sync State

```yaml
task_tracker_sync_state:
  task_ref: TASK-0042
  provider: github
  external_ref: owner/repo#123

  last_synced_task_version: 8
  last_synced_event_sequence: 17

  status:
    synced | pending | failed | disabled

  attempts: 1
  last_error: null
  updated_at: timestamp
```

## 9. Idempotency

Create/update operations should be idempotent where practical.

Suggested key:

```text
provider + task_ref + target_task_version
```

Creation should check for an existing external link before creating a new item.

## 10. Provider Mapping Contract

Each adapter owns mappings such as:

```text
map_title()
map_body()
map_status()
map_labels()
map_event()
```

Core orchestration code must not contain provider-specific label names or issue-state semantics.

## 11. GitHub Candidate Mapping

```yaml
github_mapping:
  issue:
    title: projection.title
    body_sections:
      - Objective
      - Acceptance Criteria
      - Current Status
      - Blockers
      - Orchestrator References

  labels:
    static:
      - orchestrator

    status:
      created: status:created
      active: status:active
      awaiting_input: status:awaiting-input
      blocked: status:blocked
      awaiting_acceptance: status:awaiting-acceptance
      cancelled: status:cancelled

  issue_state:
    completed: closed
    cancelled: closed
    default: open
```

## 12. Retry policy

Candidate v1:

```yaml
task_tracker_sync:
  max_retries: 3
  backoff: exponential
```

A failed tracker sync does not automatically block the canonical Task. If tracker integration is configured as mandatory, policy may register a separate operational blocker.

## 13. Inbound contract

Not supported in v1:

```text
external status → canonical status
external labels → canonical metadata
external comments → automatic commands
```

Future inbound support requires a separate authorized command contract.

## 14. Contract rules

- projection derives from canonical Task state;
- updates are idempotent where practical;
- provider external reference is non-canonical;
- sync failure is isolated from Task mutation;
- provider mapping lives entirely inside adapter implementation;
- private chain-of-thought is never projected externally.
