# Testing Contract

**Status:** Candidate artifact contract v0.1

## 1. Testing Request

```yaml
testing_request:
  task_ref: TASK-0042
  plan_ref: PLAN-0042-v2
  analysis_ref: ANALYSIS-0042-v1
  implementation_ref: IMPLEMENTATION-0042-v2
  code_review_ref: CODE-REVIEW-0042-v2

  workspace_ref: WORKSPACE-IMPLEMENTED
  project_profile_ref: PROJECT-PROFILE

  previous_testing_ref: null
```

---

## 2. Test Execution Plan

```yaml
test_execution_plan:
  id: TEST-PLAN-0042-v1

  stages:
    - id: TEST-STAGE-01
      type: build
      required: true

    - id: TEST-STAGE-02
      type: targeted_unit
      required: true

    - id: TEST-STAGE-03
      type: integration
      required: true

  fail_fast: true
```

---

## 3. Test Execution Record

```yaml
test_execution:
  id: TEST-RUN-0042-01

  stage_ref: TEST-STAGE-02

  capability: project-test-runner
  command_ref: unit:payment

  status:
    passed | failed | blocked | skipped

  counts:
    passed: 18
    failed: 0
    skipped: 1

  duration_ms: 8420

  output_ref: TEST-OUTPUT-0042-01
```

---

## 4. Failure Finding

```yaml
test_failure:
  id: TEST-F-01

  test_ref: PaymentServiceTest.test_reject_settled_payment

  classification:
    implementation_defect | test_defect | plan_defect | analysis_defect | missing_context | environment | flaky | unknown

  evidence:
    - TEST-OUTPUT-0042-01
    - DIFF-0042-v2

  summary: string

  recommended_route:
    implementation | planning | analysis | context | retry | blocked

  confidence:
    high | medium | low
```

---

## 5. Testing Result

```yaml
testing_result:
  id: TESTING-0042-v1

  task_ref: TASK-0042

  result:
    passed | passed_with_warnings | failed | blocked | inconclusive

  execution_plan_ref: TEST-PLAN-0042-v1

  totals:
    checks: 4
    passed: 4
    failed: 0
    skipped: 0

  coverage:
    available: true
    metrics: {}

  failures: []

  flaky_tests: []

  missing_coverage: []

  warnings: []

  route:
    target: documentation
```

---

## 6. Failed result

```yaml
testing_result:
  result: failed

  failures:
    - TEST-F-01

  route:
    target: implementation
    reason: implementation_defect
```

---

## 7. Inconclusive result

```yaml
testing_result:
  result: inconclusive

  warnings:
    - >
      Required integration environment was unavailable.

  route:
    target: blocked
```

---

## 8. Contract rules

- actual execution evidence must exist for pass/fail claims;
- Testing does not modify source in v1;
- failures are classified before routing;
- coverage is project-policy driven;
- TDD evidence is supplementary, not authoritative;
- testing artifacts contain no private chain-of-thought.


---

## 9. Additional Validation Request

```yaml
testing_request:
  mode: additional_validation

  source:
    user_acceptance_ref: USER-ACCEPTANCE-0042-v1

  requested_validation:
    types:
      - integration
      - e2e

    scenarios:
      - cancellation through complete UI-to-backend flow
```

The resulting `testing_result` becomes evidence for a new Readiness/Acceptance candidate.
