# Implementation Contract

**Status:** Accepted v1 contract  
**Scope:** Single-agent implementation

## 1. Implementation Request

```yaml
implementation_request:
  task_ref: TASK-0042
  execution_package_ref: EXEC-PKG-0042-v1
  execution_preflight_ref: PREFLIGHT-0042-v1
  plan_ref: PLAN-0042-v2
  specification_ref: SPEC-0042-v1
  project_profile_ref: PROJECT-PROFILE

  preflight_status: fresh

  previous_feedback:
    code_review_ref: null
    test_failure_ref: null
```

## 1A. Implementation start guard

Implementation may start only when:

```text
Task status = active
valid execution claim exists
Execution Package is current
Execution Preflight = fresh
```

If Preflight requests refresh/reanalysis/replanning, no Implementation Result is created until preparation is approved again and a new Execution Package is current.

## 2. Implementation Result

```yaml
implementation_result:
  id: IMPLEMENTATION-0042-v1

  task_ref: TASK-0042
  plan_ref: PLAN-0042-v2

  strategy: single_agent

  completed_plan_steps:
    - STEP-01
    - STEP-02
    - STEP-03

  changed:
    files: []
    symbols: []
    components: []

  deviations:
    accepted_minor: []
    plan_change_required: []

  local_validation:
    status: passed | partial | failed
    checks_run: []
    passed: []
    failed: []

  discoveries:
    context_candidates: []
    knowledge_candidates: []

  unresolved: []

  workspace_ref: string | null
  source_revision_ref: string | null
```

## 3. Result envelope

```yaml
implementation_execution_result:
  result:
    success | needs_context | needs_input | plan_change_required | blocked | retryable_failure | failure

  artifact_ref: IMPLEMENTATION-0042-v1 | null

  context_request: null
  questions: []
  blocker: null
  error: null
```

## 4. Needs Context

```yaml
implementation_execution_result:
  result: needs_context

  context_request:
    mode: expand
    need:
      - transaction behavior around PaymentService.cancel

    reason: >
      Implementation cannot safely proceed without confirming
      the transaction invariant.
```

## 5. Plan Change Required

```yaml
implementation_execution_result:
  result: plan_change_required

  plan_issue:
    summary: >
      The approved plan assumes the public API remains unchanged,
      but implementation requires a new mandatory field.

    affected_steps:
      - STEP-02
      - STEP-03

    recommended_route: planning
```

## 6. Local Validation

```yaml
local_validation:
  checks_run:
    - syntax
    - targeted_unit_tests

  passed:
    - syntax

  failed: []

  status: passed
```

Local validation is a fast implementation-stage check and does not replace the downstream Testing Subgraph.

## 7. Contract rules

- v1 always uses `strategy: single_agent`;
- Implementation requires a current Execution Package and successful Execution Preflight;
- one implementation agent executes the approved plan end-to-end;
- material plan changes route to Planning;
- missing evidence routes to Context expansion;
- the result records actual changes and deviations;
- Code Review receives the actual diff/workspace in addition to this artifact;
- multi-agent/work-unit contracts are deferred to a future version.


---

## 8. Durable execution input rule

Implementation starts from the durable:

```text
Task
Development Specification
Approved Implementation Plan
Project Profile
```

It must not depend on preparation conversation history or raw Context/Analysis artifacts.

If implementation discovers that a material project fact is missing or contradicts the Specification, return to re-preparation rather than silently reconstructing hidden preparation state.
