# Final Check Policy

**Status:** Accepted policy draft v0.2  
**Supersedes:** previous Final Validation policy

## 1. Default v1

Recommended for the single-developer orchestrator:

```yaml
final_check:
  enabled: true

  readiness_gate:
    enabled: true

  user_acceptance:
    mode: required

  acceptance_package:
    enabled: true
```

---

## 2. Readiness policy

Readiness Gate is deterministic-first.

Required:

```text
Plan Review approved
Implementation completed
Code Review approved
Testing passed under current policy
Documentation completed/no_change
No blocking findings
Acceptance evidence trace exists
Candidate revision is consistent
```

No additional AI review is performed by default.

---

## 3. User acceptance modes

```text
required
auto
off
```

Recommended v1:

```text
required
```

This ensures the delivered feature is explicitly accepted by the user before Task completion.

---

## 4. Auto mode policy

If enabled later, require acceptance for:

```text
observable behavior change
bugfix
new feature
business/domain rule change
UI/UX change
integration change
public API behavior change
user-visible migration
```

Potential bypass:

```text
behavior-preserving internal refactor
documentation-only task
test-only maintenance
mechanical cleanup
```

---

## 5. Additional automated validation

Final Check may recommend or the user may request:

```text
integration
E2E/UI
contract
smoke
full regression
environment-specific validation
```

All execution routes to the Testing Subgraph.

Final Check itself never executes tests.

---

## 6. Risk-driven pre-acceptance validation

Project Profile may require additional test classes before user acceptance.

Example:

```yaml
final_check:
  required_test_evidence:
    user_facing_change:
      - integration
      - e2e
```

Readiness Gate then blocks acceptance until Testing provides the evidence.

---

## 7. User rejection policy

A user rejection:

1. does not mark the task failed;
2. does not create an automatic infinite loop;
3. is classified;
4. routes to the owning stage;
5. creates a new acceptance candidate after remediation.

Track:

```text
acceptance_cycle
rejection reason
candidate version
resolved feedback
```

---

## 8. New scope policy

If user feedback is a new feature/request rather than a defect in the accepted Task:

```text
do not silently expand current task
```

Preferred:

```text
current task accepted/completed if original criteria are satisfied
+
create new managed Task
```

If the user explicitly says the missing behavior was part of the original requirement, treat it as requirement mismatch and remediate the current Task.

---

## 9. Awaiting Acceptance state

Recommended Task Manager state:

```text
Awaiting Acceptance
```

Use when:

- technical workflow is ready;
- acceptance package exists;
- user has not yet approved;
- acceptance is deferred.

This distinguishes engineering completion from product/user acceptance.

---

## 10. Approval invalidation

User approval is valid only for the exact accepted candidate.

Invalidate acceptance when:

```text
runtime code changes
business behavior changes
contract changes
material configuration changes
source-adjacent change affects behavior
```

Pure external documentation correction may not require renewed functional acceptance unless project policy says otherwise.

---

## 11. Clarification policy

`needs_clarification` should not restart the workflow.

The orchestrator explains:

```text
expected behavior
what changed
how to test
existing automated evidence
```

The user then continues acceptance decision.

---

## 12. Completion policy

Task becomes `Complete` only when:

```text
readiness == ready
AND
user acceptance policy satisfied
```

No additional generic Final Validation model pass is required.

---

## 13. Accepted decisions

1. Final Check is not an AI-heavy review.
2. It combines deterministic readiness with human/user acceptance.
3. User acceptance is required by default in v1.
4. Additional integration/E2E validation routes to Testing.
5. `Awaiting Acceptance` is a first-class state.
6. User rejection creates explicit remediation, not automatic looping.
7. Candidate revision and approval are version-bound.
8. New scope is separated from defects/misunderstood original scope.
