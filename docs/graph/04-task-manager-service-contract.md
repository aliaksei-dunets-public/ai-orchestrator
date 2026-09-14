# Task Manager Service — API and Data Contract

**Status:** Candidate v1 contract

## 1. Task Model

```yaml
task:
  id: TASK-0042
  version: 7

  title: string
  type:
    implementation | analysis | investigation | incident | exploration

  status:
    created | preparing | ready | active | awaiting_input | blocked | awaiting_acceptance | completed | cancelled

  source:
    type: user_request
    ref: null
    original_request_ref: string | null

  definition_version: integer

  problem_statement: string | null
  objective: string
  expected_outcome: []
  constraints: []

  acceptance_criteria:
    - id: AC-01
      text: string

  open_questions: []

  execution:
    target_workflow: development
    handoff_mode: immediate | deferred
    prepared_source_revision: string | null
    active_claim_ref: string | null

  workflow:
    active_run_ref: RUN-0042-03
    history: []

  artifacts:
    specification: null
    plan: null
    plan_review: null
    execution_package: null

  durable_documents:
    specification_path: .orchestrator/tasks/TASK-0042/specification.md
    plan_path: .orchestrator/tasks/TASK-0042/plan.md
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

## 2. Commands and queries

### Create Task

```yaml
command:
  type: create_task
  task_artifact:
    title: Add payment cancellation validation
    type: implementation
    objective: Prevent cancellation of settled payments.
    acceptance_criteria:
      - id: AC-01
        text: Settled payment cannot be cancelled.
```

Result:

```yaml
result:
  status: success
  task_ref: TASK-0042
  version: 1
```

### Get Task

```yaml
query:
  type: get_task
  task_ref: TASK-0042
```

### List Tasks

```yaml
query:
  type: list_tasks
  filters:
    status: [preparing, ready, active, awaiting_acceptance]
    type: [implementation]
  limit: 50
```

### Update Metadata

Only non-lifecycle fields may use generic metadata updates.

```yaml
command:
  type: update_metadata
  task_ref: TASK-0042
  expected_version: 7
  patch:
    title: Updated title
```

Protected fields such as status, artifacts, blockers, user decisions, and workflow links require dedicated commands.

### Refine Task Definition

Allowed only while the Task is `created`, `preparing`, or `awaiting_input` related to preparation.

```yaml
command:
  type: refine_task_definition
  task_ref: TASK-0042
  expected_version: 6

  patch:
    objective: >
      Correct payment scenario X while preserving existing valid behavior.

    acceptance_criteria:
      - id: AC-01
        text: Scenario X returns the expected payment result.

  evidence_refs:
    - SPEC-0042-v1
```

Rules:

```text
original user request is immutable
refinement is evented/versioned
material refinement after ready invalidates readiness
```

### Transition Status

```yaml
command:
  type: transition_status
  task_ref: TASK-0042
  expected_version: 7
  to: awaiting_acceptance
  reason: readiness_completed
  evidence_refs:
    - READINESS-0042-v1
    - ACCEPTANCE-PACKAGE-0042-v1
```

Possible results:

```text
success
invalid_transition
guard_failed
version_conflict
not_found
failure
```

### Attach Artifact

```yaml
command:
  type: attach_artifact
  task_ref: TASK-0042
  expected_version: 7
  role: testing
  artifact_ref: TESTING-0042-v1
```

### Add Blocker

```yaml
command:
  type: add_blocker
  task_ref: TASK-0042
  expected_version: 7
  blocker:
    type: missing_environment
    summary: Integration environment unavailable.
    blocking: true
    evidence_refs:
      - TESTING-0042-v1
```

### Resolve Blocker

```yaml
command:
  type: resolve_blocker
  task_ref: TASK-0042
  expected_version: 8
  blocker_ref: BLOCK-01
  resolution:
    summary: Environment access restored.
```

### Record User Decision

```yaml
command:
  type: record_user_decision
  task_ref: TASK-0042
  expected_version: 9
  decision:
    type: acceptance
    value: approved
    artifact_ref: USER-ACCEPTANCE-0042-v2
```

### Link Workflow Run

```yaml
command:
  type: link_workflow_run
  task_ref: TASK-0042
  expected_version: 4
  workflow_run_ref: RUN-0042-03
  relation: active
```

Task Manager does not set `current_node`.

### Start Preparation

```yaml
command:
  type: start_preparation
  task_ref: TASK-0042
  expected_version: 1
  workflow_run_ref: RUN-0042-PREP-01
```

Successful execution performs:

```text
created → preparing
```

### Attach Execution Package

```yaml
command:
  type: attach_execution_package
  task_ref: TASK-0042
  expected_version: 10
  execution_package_ref: EXEC-PKG-0042-v1
```

The package must reference the current approved Plan Review and prepared source revision.

### Mark Ready

```yaml
command:
  type: transition_status
  task_ref: TASK-0042
  expected_version: 11
  to: ready
  reason: preparation_approved
  evidence_refs:
    - PLAN-REVIEW-0042-v2
    - EXEC-PKG-0042-v1
```

TaskManagerService evaluates the execution-readiness guard.

### List Executable Tasks

```yaml
query:
  type: list_executable_tasks
  filters:
    status: ready
    target_workflow: development
  limit: 20
```

### Claim Task

```yaml
command:
  type: claim_task
  task_ref: TASK-0042
  expected_version: 12
  worker_ref: WORKER-03
  lease_seconds: 900
```

Success atomically performs `ready → active` and returns:

```yaml
result:
  status: success
  claim:
    claim_ref: CLAIM-0042-01
    task_ref: TASK-0042
    worker_ref: WORKER-03
    lease_until: timestamp
    execution_package_ref: EXEC-PKG-0042-v1
```

### Renew Claim

```yaml
command:
  type: renew_claim
  claim_ref: CLAIM-0042-01
  lease_seconds: 900
```

### Release Claim

```yaml
command:
  type: release_claim
  claim_ref: CLAIM-0042-01
  reason: preflight_requires_repreparation
  target_status: preparing
```

Release is guarded so that an active Workflow Run cannot be accidentally duplicated.

### Complete Task

Completion uses a dedicated command.

```yaml
command:
  type: complete_task
  task_ref: TASK-0042
  expected_version: 12
  completion_decision_ref: COMPLETION-0042-v1
```

Example guard failure:

```yaml
result:
  status: guard_failed
  failed_guards:
    - user_acceptance_missing
```

### Cancel Task

```yaml
command:
  type: cancel_task
  task_ref: TASK-0042
  expected_version: 5
  reason: superseded_by_new_task
  superseded_by: TASK-0047
```

### Register External Link

```yaml
command:
  type: register_external_link
  task_ref: TASK-0042
  expected_version: 7
  link:
    tracker: github
    external_ref: owner/repo#123
    relation: projection
```

### Get History

```yaml
query:
  type: get_history
  task_ref: TASK-0042
  after_sequence: 0
```

## 3. Domain Event Envelope

```yaml
task_event:
  event_id: EVT-000123
  sequence: 17
  task_ref: TASK-0042
  task_version: 8
  type: status_changed
  at: timestamp

  actor:
    type: orchestrator
    ref: task_manager_service

  payload:
    from: active
    to: awaiting_acceptance

  evidence_refs:
    - READINESS-0042-v1
```

## 4. Error Contract

```yaml
error:
  type:
    task_not_found |
    task_version_conflict |
    invalid_transition |
    guard_failed |
    validation_failed |
    repository_failure |
    task_not_ready |
    claim_conflict |
    claim_expired

  message: string
  details: {}
```

Graph Runtime must be able to route from structured errors without parsing prose.

## 5. Repository Port

Candidate interface:

```text
TaskRepository

get(task_ref)
list(filters)
commit(new_snapshot, event, expected_version)
history(task_ref, after_sequence)
exists(task_ref)
```

Task lifecycle rules belong in TaskManagerService, not Repository.

## 6. Lifecycle guards

Candidate v1:

```text
to preparing:
  valid task exists
  preparation run linked

preparing → ready:
  specification exists and is sufficient
  plan exists
  plan_review == approved for current specification + plan binding
  execution_package exists
  execution_package spec/plan hashes are current
  no blocking blockers

ready → active:
  atomic claim required
  execution_package current
  no active claim
  no blocking blockers

to awaiting_acceptance:
  readiness == ready
  acceptance_package exists

to completed when acceptance required:
  readiness == ready
  user_acceptance == approved
  accepted candidate revision == current candidate revision
  no blocking blockers
```

Project policy may add guards but should not remove data-integrity guards.

## 7. Contract rules

- every mutation is versioned;
- direct status mutation outside service commands is forbidden;
- protected fields use dedicated commands;
- errors are machine-readable;
- Task stores references rather than artifact bodies;
- `ready` requires a current Specification, approved Plan binding, and valid Execution Package;
- `ready → active` is claim-only;
- execution claims are leased and versioned;
- Workflow Run execution state stays outside Task;
- canonical mutation commits before external tracker synchronization.
