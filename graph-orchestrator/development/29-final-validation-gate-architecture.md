# Final Check — Completion + User Acceptance Architecture

**Status:** Accepted design draft v0.2  
**Supersedes:** previous `Final Validation` design  
**Scope:** Development Workflow — final readiness and user acceptance before task completion

## 1. Recommendation

The final stage should **not** be another AI review.

It should consist of two clearly separated parts:

```text
A. COMPLETION / READINESS GATE
   deterministic-first

B. USER ACCEPTANCE GATE
   human validation of the delivered behavior
```

Together they form the `Final Check`.

The purpose is:

1. confirm that all required automated gates and artifacts are complete;
2. prepare a clear acceptance package for the user;
3. let the user exercise the delivered change;
4. allow the user to approve, reject, or request additional validation;
5. complete the task only after acceptance policy is satisfied.

---

## 2. High-level workflow

```text
DOCUMENTATION
      ↓
COMPLETION / READINESS GATE
      │
      ├── not ready
      │      ↓
      │  return to owning stage
      │
      └── ready
              ↓
       PREPARE ACCEPTANCE PACKAGE
              ↓
       USER ACCEPTANCE GATE
          │       │        │
          │       │        └── request additional validation
          │       │                    ↓
          │       │                 TESTING
          │       │                    ↓
          │       │               READINESS GATE
          │       │                    ↓
          │       └── rejected ──► REMEDIATION
          │                            ↓
          │                     required quality gates
          │                            ↓
          │                     READINESS GATE
          │                            ↓
          └── approved ─────────────► COMPLETE
```

There is no automatic self-review loop inside Final Check.

---

## 3. Why user acceptance is distinct from Testing

Automated Testing answers:

> Does the implementation satisfy the executable checks we know how to run?

User Acceptance answers:

> Does the delivered behavior actually solve my problem in the way I expect?

These are not identical.

Automated tests may all pass while the user still discovers:

- wrong UX;
- misunderstood requirement;
- inconvenient workflow;
- missing business scenario;
- unexpected integration behavior;
- a technically correct but practically wrong result.

Therefore user acceptance is a valid independent gate.

---

## 4. Why Integration / E2E tests remain in Testing

Integration and E2E are still test types owned by the `Testing Subgraph`.

The Final Check does not implement a second test runner.

Instead it may decide:

```text
acceptance confidence insufficient
or
user explicitly requests more validation
        ↓
additional_validation_request
        ↓
Testing Subgraph
```

Testing then executes the required:

```text
integration
contract
E2E/UI
smoke
regression
environment-specific validation
```

and returns new evidence.

This preserves clear responsibility boundaries.

---

# PART A — COMPLETION / READINESS GATE

## 5. Purpose

The Readiness Gate is a deterministic-first closure check.

It does not ask whether the code is "good".

It verifies that the workflow is in a valid state for user acceptance.

---

## 6. Readiness checks

Candidate checks:

```text
Task is active and not blocked
Plan Review approved
Approved Plan version is final/current
Implementation completed
Code Review approved
Testing passed / accepted warnings
Documentation impact evaluated
Required documentation completed
No blocking findings remain
No unresolved material plan deviations
Final workspace/revision is consistent
Acceptance criteria have traceable evidence
```

If all pass:

```text
READY_FOR_USER_ACCEPTANCE
```

Otherwise:

```text
NOT_READY
```

---

## 7. Acceptance criteria traceability

The gate should verify a structured trace rather than re-reason about every criterion.

Example:

```text
AC-01
  → implemented by PaymentService.cancel
  → reviewed in CODE-REVIEW-42
  → verified by TEST-17
  → documented in domain/payment.md
```

This is primarily a data consistency check.

AI may be used only when mapping an ambiguous natural-language acceptance criterion to existing evidence cannot be done deterministically.

---

## 8. Revision integrity

A critical readiness requirement:

> The state presented to the user must be the state that passed the required technical gates.

Check:

```text
implemented revision
reviewed revision
tested revision
post-documentation revision
current candidate revision
```

Any source-adjacent documentation change must have completed its required delta review/validation.

If revisions do not align:

```text
NOT_READY
```

---

# PART B — ACCEPTANCE PREPARATION

## 9. Acceptance Package

Before asking the user to test, the orchestrator creates a compact `Acceptance Package`.

It should answer:

```text
What changed?
Why?
What should I test?
How do I test it?
What should happen?
What automated verification already passed?
Are there known limitations/warnings?
```

Example:

```yaml
acceptance_package:
  summary: >
    Payment cancellation now rejects settled payments
    without changing payment state.

  scenarios:
    - title: Cancel unsettled payment
      expected: cancellation succeeds

    - title: Cancel settled payment
      expected: cancellation is rejected and state remains unchanged

  automated_evidence:
    - targeted unit tests passed
    - integration tests passed

  known_warnings: []
```

The user should not need to reconstruct testing steps from the implementation plan.

---

## 10. Manual acceptance scenarios

Manual scenarios should be derived from:

```text
Task acceptance criteria
business/domain behavior
important edge cases
user-facing workflows
Analysis risks
automated test gaps
```

They should focus on observable outcomes, not implementation internals.

Bad:

```text
Open class X and inspect variable Y.
```

Preferred:

```text
Open a settled payment and attempt cancellation.
Expected: cancellation is rejected and payment state does not change.
```

---

## 11. Environment / prerequisites

Acceptance Package may include:

```text
environment
test data
required account/role
feature flags
setup steps
URLs/screens/screens
expected preconditions
```

If the orchestrator can prepare test data or launch the application safely, that can be an optional capability.

The Final Check itself should not hide environment assumptions.

---

# PART C — USER ACCEPTANCE GATE

## 12. User outcomes

Recommended outcomes:

```text
approved
rejected
request_additional_validation
needs_clarification
deferred
```

### approved

User accepts the delivered change.

Route:

```text
Complete
```

### rejected

User tested the behavior and found a problem.

The rejection includes structured feedback and routes to remediation.

### request_additional_validation

User wants more automated confidence before approval.

Examples:

```text
run integration tests
run E2E
test another environment
run full regression
verify one specific business scenario
```

Route:

```text
Testing
```

### needs_clarification

User wants clarification about expected behavior/testing before deciding.

### deferred

User acceptance will happen later. Task remains awaiting acceptance.

---

## 13. User rejection is not an automatic loop

A user rejection creates a new explicit remediation cycle.

Example:

```text
USER REJECTS:
"Cancellation works, but the screen does not show the rejection reason."
       ↓
classify feedback
       ↓
Implementation / Planning / Analysis
       ↓
Code Review
       ↓
Testing
       ↓
Documentation if impacted
       ↓
Readiness Gate
       ↓
new Acceptance Package
       ↓
User Acceptance
```

This is not considered an uncontrolled orchestrator loop because each cycle is initiated by explicit external acceptance feedback.

The system should track acceptance version/cycle for auditability.

---

## 14. Feedback classification

User feedback must be classified before routing.

Possible categories:

```text
implementation_defect
requirement_mismatch
missing_scenario
ux_issue
integration_issue
documentation_issue
additional_validation_request
new_scope_request
environment_issue
```

Examples:

### implementation defect

```text
expected behavior is correct, implementation is wrong
→ Implementation
```

### requirement mismatch

```text
system implemented the approved interpretation,
but user says requirement was misunderstood
→ Analysis / Planning
```

### new scope request

```text
user accepts current task but asks for an additional feature
→ current task may complete
→ create new Task
```

Do not silently expand the current task.

---

## 15. Additional validation requested by user

Example:

```yaml
additional_validation_request:
  requested_by: user

  types:
    - integration
    - e2e

  scenarios:
    - cancellation through actual UI and backend

  reason: >
    Unit tests passed, but I want verification of the complete user flow.
```

Route:

```text
Testing Subgraph
```

After successful testing:

```text
Readiness Gate
→ User Acceptance again
```

The user remains the acceptance authority.

---

## 16. Automated acceptance escalation

The system may also recommend additional integration/E2E testing before user acceptance when risk warrants it.

Example:

```text
Task changed UI + API + backend
but only unit tests were executed
        ↓
Readiness policy says acceptance evidence insufficient
        ↓
Testing Subgraph
        ↓
run E2E/integration
```

This should be driven by explicit Project/Test policy, not arbitrary final-stage intuition.

---

## 17. User acceptance configuration

Candidate Project Profile:

```yaml
final_check:
  user_acceptance:
    mode: required
```

Supported:

```text
required
auto
off
```

### required

Task cannot complete without explicit user approval.

### auto

Require user acceptance for user-facing/high-risk/behavior-changing work; allow automatic completion for clearly internal low-risk work.

### off

No user acceptance gate.

For a single-developer workflow, recommended default for v1:

```yaml
mode: required
```

Projects may later choose `auto`.

---

## 18. Suggested `auto` policy

If `mode: auto`, require user acceptance for:

```text
new feature
bugfix affecting observable behavior
UI/UX change
business rule change
public API behavior change
workflow change
integration behavior change
migration with user-visible effect
```

May skip explicit acceptance for:

```text
internal refactoring with behavior unchanged
documentation-only change
test-only maintenance
mechanical cleanup
```

---

## 19. Acceptance versioning

Each acceptance attempt refers to an immutable candidate.

Example:

```text
ACCEPTANCE-CANDIDATE-v1
→ rejected

implementation changes
→ review/testing
→ ACCEPTANCE-CANDIDATE-v2
→ approved
```

The system must never carry approval from v1 onto changed v2 automatically.

Any implementation change after rejection invalidates previous acceptance.

---

## 20. Completion

Task transitions to `Complete` only when:

```text
Readiness Gate = ready
AND
User Acceptance policy = satisfied
```

For `required`:

```text
explicit user approval
```

For `auto`:

```text
explicit approval when required by policy
or
documented policy-based bypass
```

For `off`:

```text
Readiness Gate only
```

---

## 21. Relationship with Task Manager

Recommended managed-work states:

```text
In Progress
Review
Testing
Documentation
Awaiting Acceptance
Complete
Blocked
```

`Awaiting Acceptance` is valuable because the technical workflow may be finished while the user has not yet tested it.

---

## 22. Model policy

| Stage | Execution |
|---|---|
| Readiness checks | deterministic |
| Acceptance traceability | deterministic-first |
| Acceptance scenario generation | standard |
| Feedback classification | standard |
| Additional-test recommendation | policy + standard |
| User approval | human |
| Task completion transition | deterministic |

---

## 23. What Final Check must NOT do

Final Check must not:

- redo Code Review;
- rerun tests directly;
- modify code;
- modify docs;
- silently reinterpret failed acceptance;
- auto-approve user-facing behavior when approval is required;
- turn new feature requests into hidden current-task scope;
- create automated infinite remediation cycles.

---

## 24. Accepted decisions

1. Previous AI-heavy Final Validation is replaced.
2. Final Check consists of Readiness Gate + User Acceptance Gate.
3. Readiness is deterministic-first.
4. Integration/E2E execution remains owned by Testing.
5. Final Check may request additional Testing.
6. User receives a structured Acceptance Package.
7. User may approve, reject, request more validation, defer, or ask for clarification.
8. User rejection creates an explicit remediation cycle, not an automatic loop.
9. Acceptance candidates are versioned.
10. `Awaiting Acceptance` becomes a first-class task state.
11. Recommended v1 policy for the single-developer workflow is explicit user acceptance.
