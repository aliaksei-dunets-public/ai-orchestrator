# TDD Integration Architecture

**Status:** Accepted design draft v0.1  
**Scope:** Development Workflow — optional test-first execution mode

## 1. Recommendation

TDD should be supported by the orchestrator, but it should **not** be a mandatory global workflow.

The correct design is:

```text
Planning decides testing intent
        ↓
Implementation executes in normal or TDD mode
        ↓
Code Review
        ↓
Testing Subgraph performs independent verification
```

TDD is therefore primarily an **Implementation execution policy**, informed by Planning and validated by Testing.

---

## 2. Why not put TDD only into Testing

If tests are written only after implementation, that is not TDD.

TDD requires the implementation loop itself to be test-first:

```text
define expected behavior
      ↓
write/select failing test
      ↓
confirm failure
      ↓
implement minimum change
      ↓
confirm pass
      ↓
refactor safely
```

Therefore the RED/GREEN/REFACTOR loop belongs inside Implementation.

The downstream Testing Subgraph still remains necessary because it validates the completed implementation independently.

---

## 3. Workflow position

```text
TASK
 ↓
CONTEXT
 ↓
ANALYSIS
 ↓
PLANNING
 │
 │ determines testing strategy
 ↓
PLAN REVIEW
 ↓
IMPLEMENTATION
 │
 ├── normal mode
 │
 └── TDD mode
       ↓
   RED → GREEN → REFACTOR
 ↓
CODE REVIEW
 ↓
TESTING
 ↓
DOCUMENTATION
 ↓
FINAL VALIDATION
```

---

## 4. TDD modes

Recommended configuration:

```yaml
development:
  tdd:
    mode: auto
```

Supported modes:

```text
off
auto
required
```

### `off`

Implementation does not require test-first execution.

Tests may still be added and the Testing Subgraph still runs.

### `auto`

The orchestrator decides whether TDD is appropriate for the task or individual plan steps.

Recommended default.

### `required`

Applicable implementation steps must follow test-first execution unless a justified exception is recorded.

---

## 5. TDD is step-aware

TDD should not necessarily apply to the whole Task.

Example:

```text
STEP-01 Domain behavior
→ TDD

STEP-02 Configuration update
→ normal

STEP-03 Documentation
→ not applicable
```

Plan steps may define:

```yaml
testing_strategy:
  mode: tdd | test_after | existing_tests | not_applicable
```

This is more useful than one Task-wide boolean.

---

## 6. Strong TDD candidates

TDD is especially valuable for:

```text
business/domain logic
bug fixes
pure functions
service behavior
validation rules
state transitions
data transformation
algorithms
regression-prone logic
```

For bug fixes, the preferred pattern is:

```text
reproduce defect with failing regression test
      ↓
implement fix
      ↓
test passes
```

---

## 7. Refactoring

For refactoring, classical RED-first TDD may not be the right model.

Preferred:

```text
CHARACTERIZE
      ↓
REFACTOR
      ↓
VERIFY
```

Before changing behavior-neutral code:

- identify existing tests;
- add characterization tests if behavior is insufficiently protected;
- confirm baseline passes;
- refactor;
- re-run tests.

This is a separate test-first pattern but uses the same orchestration capability.

---

## 8. Weak TDD candidates

Do not force TDD where the loop creates little value.

Examples:

```text
documentation-only changes
formatting
static configuration
generated artifacts
mechanical renames
simple dependency metadata updates
UI layout-only changes
one-off migration scripts where integration verification is more meaningful
```

The system may still require validation.

---

## 9. Planning responsibility

Planning does not write tests.

It defines:

```text
what behavior must be verified
which plan steps should use TDD
what level of test is appropriate
what acceptance/regression cases matter
```

Example:

```yaml
testing_strategy:
  mode: tdd

  level:
    - unit

  behaviors:
    - cancellation rejects already-settled payments
    - failed validation does not mutate payment state
```

This gives the Implementation agent a clear test-first contract.

---

## 10. Plan Review responsibility

Plan Review verifies whether the testing strategy is appropriate.

Examples of findings:

```text
bugfix has no regression test
critical domain rule has no planned test
TDD required by project policy but plan uses test_after
plan proposes unit TDD for behavior that can only be verified by integration test
```

Plan Review does not execute tests.

---

## 11. Implementation TDD loop

For a `tdd` plan step:

```text
SELECT BEHAVIOR
      ↓
CREATE / MODIFY TEST
      ↓
RUN TARGETED TEST
      ↓
EXPECTED FAILURE?
   ├── no → diagnose test/baseline
   └── yes
          ↓
IMPLEMENT MINIMAL CHANGE
          ↓
RUN TARGETED TEST
          ↓
PASS?
   ├── no → fix implementation
   └── yes
          ↓
REFACTOR
          ↓
RUN TARGETED TESTS
          ↓
STEP COMPLETE
```

The implementation artifact should record this sequence compactly.

---

## 12. Red-state validation

A test that passes immediately does not prove the intended behavior was absent.

For genuine TDD, the Implementation agent should confirm the test fails for the expected reason before implementation.

Possible result:

```yaml
red_phase:
  status: confirmed
  failure_reason: expected_behavior_missing
```

Exceptions:

- existing failing regression test already demonstrates the defect;
- behavior already partially exists;
- test-first mode is impossible in the environment.

Any exception should be recorded.

---

## 13. Green-state validation

After implementation:

```yaml
green_phase:
  status: passed
  tests:
    - PaymentServiceTest.test_reject_settled_payment
```

The agent should avoid implementing unrelated functionality merely to make tests pass.

---

## 14. Refactor phase

Refactor is optional when no cleanup is necessary.

If used:

```text
tests must remain green
```

The refactor phase should not expand approved task scope.

---

## 15. Code Review integration

Code Review receives TDD evidence, but does not trust it blindly.

It may verify:

- test actually covers the changed behavior;
- assertion is meaningful;
- test was not weakened to make code pass;
- implementation is not overfit to a trivial test;
- required regression case exists.

TDD evidence improves reviewability but does not replace review.

---

## 16. Testing Subgraph integration

Testing Subgraph remains independent.

It may run:

```text
new targeted tests
existing unit suite
integration tests
E2E tests
regression suites
static/build checks
```

Thus:

```text
Implementation TDD
= development method

Testing Subgraph
= independent verification
```

They must not be merged.

---

## 17. Failure routing

During TDD Implementation:

### Test cannot be made meaningfully red

Possible causes:

```text
wrong assumption
existing behavior already present
insufficient context
bad test design
```

Route appropriately.

### Implementation cannot make test green without material plan change

```text
plan_change_required → Planning
```

### Test reveals missing impact/dependency

```text
reanalysis_required / needs_context
```

Do not endlessly modify code until the test passes.

---

## 18. Project configuration

Candidate configuration:

```yaml
development:
  tdd:
    mode: auto

    preferred_for:
      - bugfix
      - domain_logic

    require_regression_test_for_bugfix: true
```

Project Profile may override the default.

---

## 19. Test level selection

Test-first does not mean "unit test only".

Possible levels:

```text
unit
component
integration
contract
E2E
```

Use the lowest reliable level that verifies the intended behavior.

Examples:

```text
pure business rule
→ unit

repository/service integration
→ component/integration

public API compatibility
→ contract/integration

UI workflow
→ component/E2E
```

---

## 20. TDD artifact evidence

Implementation Result may include:

```yaml
test_first:
  mode: tdd

  behaviors:
    - id: BEHAVIOR-01

      red:
        status: confirmed
        test_ref: PaymentServiceTest.test_reject_settled_payment

      green:
        status: passed

      refactor:
        performed: false
```

Do not store model chain-of-thought.

---

## 21. Accepted decisions

1. TDD is supported but not globally mandatory.
2. `auto` is the recommended default.
3. TDD selection is per plan step where useful.
4. Planning defines the testing intent.
5. RED/GREEN/REFACTOR lives inside Implementation.
6. Plan Review checks appropriateness of the testing strategy.
7. Bug fixes should normally begin with a regression test.
8. Refactoring uses characterization-first when appropriate.
9. Testing Subgraph remains an independent verification stage.
10. Test-first execution may use unit, component, integration, contract, or E2E tests depending on behavior.
