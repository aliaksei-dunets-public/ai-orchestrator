# Final Check Contract

**Status:** Candidate contract v0.2  
**Supersedes:** previous Final Validation contract

## 1. Final Check Request

```yaml
final_check_request:
  task_ref: TASK-0042

  plan_ref: PLAN-0042-v2
  plan_review_ref: PLAN-REVIEW-0042-v2
  implementation_ref: IMPLEMENTATION-0042-v2
  code_review_ref: CODE-REVIEW-0042-v2
  testing_ref: TESTING-0042-v1
  documentation_ref: DOC-0042-v1

  project_profile_ref: PROJECT-PROFILE

  candidate_workspace_ref: WORKSPACE-CANDIDATE
  candidate_revision_ref: REVISION-CANDIDATE
```

---

## 2. Readiness Result

```yaml
readiness_result:
  id: READINESS-0042-v1

  result:
    ready | not_ready | blocked

  checks:
    plan_review: pass
    implementation: pass
    code_review: pass
    testing: pass
    documentation: pass
    blocking_findings: pass
    acceptance_traceability: pass
    revision_integrity: pass

  missing_prerequisites: []

  route:
    target: acceptance_preparation
```

---

## 3. Acceptance Trace

```yaml
acceptance_trace:
  criterion_ref: AC-01

  status:
    satisfied | partially_satisfied | unsatisfied

  implementation_refs:
    - PaymentService.cancel

  review_refs:
    - CODE-REVIEW-0042-v2

  testing_refs:
    - TEST-RUN-0042-03

  documentation_refs:
    - docs/domain/payment-lifecycle.md

  evidence_refs: []
```

---

## 4. Acceptance Package

```yaml
acceptance_package:
  id: ACCEPTANCE-PACKAGE-0042-v1

  task_ref: TASK-0042
  candidate_revision_ref: REVISION-CANDIDATE

  summary: >
    Payment cancellation now rejects settled payments
    without changing payment state.

  changed_behavior:
    - settled payments cannot be cancelled
    - rejected cancellation preserves current state

  scenarios:
    - id: UAT-01
      title: Cancel an unsettled payment

      prerequisites:
        - payment status is open

      action:
        - attempt payment cancellation

      expected:
        - cancellation succeeds

    - id: UAT-02
      title: Attempt to cancel a settled payment

      prerequisites:
        - payment status is settled

      action:
        - attempt payment cancellation

      expected:
        - cancellation is rejected
        - payment state remains settled

  automated_evidence:
    - type: unit
      result: passed

    - type: integration
      result: passed

  known_warnings: []
  known_limitations: []
```

---

## 5. User Acceptance Result

```yaml
user_acceptance:
  id: USER-ACCEPTANCE-0042-v1

  package_ref: ACCEPTANCE-PACKAGE-0042-v1
  candidate_revision_ref: REVISION-CANDIDATE

  result:
    approved | rejected | request_additional_validation | needs_clarification | deferred

  feedback: null

  requested_validation: null

  approved_by: user
```

---

## 6. User Rejection

```yaml
user_acceptance:
  result: rejected

  feedback:
    summary: >
      Cancellation is rejected correctly, but the UI does not
      display the rejection reason.

    category:
      implementation_defect

    affected_scenarios:
      - UAT-02

  route:
    target: implementation
```

---

## 7. Additional Validation Request

```yaml
user_acceptance:
  result: request_additional_validation

  requested_validation:
    types:
      - integration
      - e2e

    scenarios:
      - cancellation through complete UI-to-backend flow

    reason: >
      I want verification of the complete user flow before approval.

  route:
    target: testing
```

---

## 8. Deferred Acceptance

```yaml
user_acceptance:
  result: deferred

  route:
    target: awaiting_acceptance
```

No technical work is automatically restarted.

---

## 9. Acceptance Candidate

```yaml
acceptance_candidate:
  id: ACCEPTANCE-CANDIDATE-0042-v2

  task_ref: TASK-0042

  revision_ref: REVISION-CANDIDATE-v2

  readiness_ref: READINESS-0042-v2
  acceptance_package_ref: ACCEPTANCE-PACKAGE-0042-v2

  supersedes:
    - ACCEPTANCE-CANDIDATE-0042-v1
```

Any code/runtime-affecting change creates a new candidate version.

---

## 10. Completion Decision

```yaml
completion_decision:
  task_ref: TASK-0042

  readiness:
    status: ready

  user_acceptance:
    required: true
    status: approved

  result:
    complete

  route:
    target: task_manager.complete
```

---

## 11. Not-ready Result

```yaml
readiness_result:
  result: not_ready

  missing_prerequisites:
    - category: testing
      summary: required integration validation has not been executed
      owner: testing

  route:
    target: testing
```

---

## 12. Contract Rules

- Readiness does not redo technical reviews.
- User approval is tied to a specific acceptance candidate revision.
- Any material implementation change invalidates prior approval.
- Integration/E2E requests route to Testing.
- Rejection feedback is classified before remediation routing.
- New scope requests are separated from defects.
- `deferred` leaves the task in `Awaiting Acceptance`.
- artifacts contain no private chain-of-thought.
