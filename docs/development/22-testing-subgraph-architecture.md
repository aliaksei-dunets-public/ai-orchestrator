# Testing Subgraph Architecture

**Status:** Accepted design draft v0.1  
**Scope:** Development Workflow — independent verification after Code Review

## 1. Purpose

The Testing Subgraph verifies that the reviewed implementation behaves correctly in the target project.

Its primary rule is:

> Test execution is deterministic/tool-first. AI is used for test selection, gap analysis, and failure interpretation — not as a substitute for the test runner.

---

## 2. Position in workflow

```text
Implementation
      ↓
Code Review
      ↓ approved
Testing Subgraph
      ↓
Documentation
      ↓
Final Validation
```

TDD inside Implementation does not remove this stage.

---

## 3. High-level flow

```text
TESTING REQUEST
      │
      ▼
1. RESOLVE TEST SCOPE
      │
      ▼
2. DISCOVER AVAILABLE TEST CAPABILITIES
      │
      ▼
3. BUILD TEST EXECUTION PLAN
      │
      ▼
4. RUN FAST / TARGETED CHECKS
      │
      ▼
5. RUN REQUIRED BROADER TESTS
      │
      ▼
6. COLLECT RESULTS
      │
      ├── all pass
      │
      └── failures
              ↓
      7. CLASSIFY FAILURES
              │
              ├── implementation defect
              ├── test defect
              ├── plan/analysis defect
              ├── environment/infrastructure
              └── flaky/unknown
              ↓
8. GAP / COVERAGE CHECK
      │
      ▼
9. TESTING RESULT
```

---

## 4. Inputs

```text
Task
Approved Plan
Implementation Analysis
Implementation Result
Code Review Result
Project Profile
actual workspace/revision
```

Optional:

```text
TDD evidence
previous testing result
```

---

## 5. Test scope resolution

Testing should derive required verification from:

```text
Task acceptance criteria
Plan validation expectations
Analysis risks
Code Review findings
changed components
Project Profile test policy
```

It should not simply run "all tests" by default if that is prohibitively expensive.

---

## 6. Test layers

Candidate types:

```text
build/compile
static analysis
unit
component
integration
contract
E2E/UI
regression suite
smoke
project-specific validation
```

Project Profile/capabilities determine what is available.

---

## 7. Test execution plan

Example:

```yaml
test_execution_plan:
  stages:
    - build
    - targeted_unit
    - affected_component
    - integration

  optional:
    - full_regression
```

Ordering normally goes from cheap/fast to expensive/broad.

Fail-fast policy may be configurable.

---

## 8. Deterministic execution

Actual execution must use project tools/capabilities.

Examples:

```text
pytest
npm test
maven/gradle
ABAP Unit
ATC
Playwright
Cypress
project scripts
CI validation commands
```

The testing subgraph invokes capabilities rather than hard-coding specific tools.

---

## 9. Failure classification

A failed test does not automatically mean "send to Implementation".

Classify root cause.

### Implementation defect

```text
route → Implementation
```

### Test defect

Example:

```text
obsolete assertion
incorrect fixture
broken mock
```

Route may still go to Implementation if tests are part of current change, otherwise to test-maintenance handling.

### Plan defect

```text
route → Planning
```

### Analysis defect

```text
route → Analysis
```

### Missing context

```text
route → Context
```

### Environment / infrastructure

```text
retry / blocked / external issue
```

### Flaky

Use bounded retry and record flakiness.

---

## 10. AI failure analysis

Use AI only after deterministic evidence exists.

Inputs:

```text
test command
exit status
failure output
changed diff
relevant test code
relevant production code
Task/Plan/Analysis
```

Output:

```text
failure classification
likely owning stage
evidence
recommended route
confidence
```

AI should not fabricate successful execution.

---

## 11. Test generation

If required behaviors are not covered, Testing may produce:

```text
missing_test finding
```

For v1, the recommended route is:

```text
Testing
   ↓ missing required coverage
Implementation
   ↓ add/fix tests
Code Review (delta)
   ↓
Testing
```

Testing itself should preferably not edit code in v1.

This keeps execution and verification responsibilities separate.

---

## 12. TDD awareness

When TDD was used, Testing verifies:

- TDD tests still pass;
- they are included in the relevant suite;
- broader behavior is not broken;
- implementation did not merely satisfy one narrow test.

TDD evidence can reduce uncertainty, but never reduces mandatory broader tests defined by project policy.

---

## 13. Coverage

Coverage thresholds are project-specific.

Possible signals:

```text
line/branch coverage
changed-line coverage
behavior/acceptance coverage
test matrix coverage
```

Do not make `80%` a universal hard-coded rule.

Project Profile may define:

```yaml
testing:
  coverage:
    required: true
    minimum: 80
```

or no numeric threshold.

Behavioral coverage is often more important than a raw percentage.

---

## 14. Bounded retry

Retries are appropriate for:

```text
flaky test
transient environment issue
temporary external dependency
```

Candidate:

```yaml
testing:
  max_transient_retries: 1
```

Do not retry deterministic implementation failures without code changes.

---

## 15. Test result statuses

Recommended:

```text
passed
passed_with_warnings
failed
blocked
inconclusive
```

`inconclusive` is valid when required verification could not be completed.

---

## 16. Testing output

The result should contain:

```text
tests/checks executed
pass/fail/skip counts
failed checks
coverage signals
environment issues
flaky tests
missing coverage findings
routing recommendation
evidence refs
```

---

## 17. Reuse

Testing is strongly reusable across:

```text
feature
bugfix
refactoring
migration
release validation
```

Behavior is driven by Project Profile and test capabilities.

---

## 18. Model policy

| Stage | Policy |
|---|---|
| Scope derivation | standard |
| Capability discovery | deterministic |
| Test plan construction | cheap/standard |
| Test execution | deterministic |
| Result collection | deterministic |
| Failure interpretation | standard → expert |
| Coverage/gap analysis | deterministic + standard |

---

## 19. Accepted decisions

1. Testing is a reusable subgraph.
2. Test execution is deterministic/tool-first.
3. AI is used for scope/gap/failure reasoning.
4. TDD does not replace Testing.
5. Testing does not edit code in v1.
6. Failure routing follows root cause.
7. Coverage policy is project-specific, not globally hard-coded.
8. Fast checks generally precede broad expensive tests.


---

## 20. Final Check / User Acceptance integration

The Testing Subgraph may be invoked again after the normal testing pass when:

```text
Readiness policy requires additional evidence
or
User Acceptance requests additional validation
```

Supported additional validation may include:

```text
integration
E2E/UI
contract
smoke
full regression
environment-specific validation
```

This is not a separate Final Check test runner. It is a normal Testing invocation with a narrower/expanded validation request.

Example:

```text
User Acceptance
  ↓ request E2E
Testing(mode=additional_validation)
  ↓
Readiness Gate
  ↓
User Acceptance
```

The user acceptance decision remains external to Testing.
