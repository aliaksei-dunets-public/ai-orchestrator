# Code Review Contract

**Status:** Candidate artifact contract v0.1

## 1. Review Request

```yaml
code_review_request:
  task_ref: TASK-0042
  plan_ref: PLAN-0042-v2
  analysis_ref: ANALYSIS-0042-v1
  implementation_ref: IMPLEMENTATION-0042-v1

  context_ref: CONTEXT-0042-v2
  project_profile_ref: PROJECT-PROFILE

  workspace_ref: WORKSPACE-IMPLEMENTED
  diff_ref: DIFF-0042-v1

  previous_review_ref: null

  policy:
    review_depth: auto
    max_review_cycles: 2
```

---

## 2. Review Result

```yaml
code_review_result:
  id: CODE-REVIEW-0042-v1

  task_ref: TASK-0042
  implementation_ref: IMPLEMENTATION-0042-v1
  diff_ref: DIFF-0042-v1

  cycle: 1
  review_depth: standard

  result:
    approved | changes_required | replanning_required | reanalysis_required | more_context_required | user_input_required | blocked | failure

  summary: >
    Implementation follows the approved plan, but cancellation state
    is mutated before validation completes.

  findings:
    - CRF-01

  previous_findings:
    resolved: []
    still_open: []

  route:
    target: implementation
    reason: implementation_defect

  evidence_refs:
    - ANALYSIS-0042-v1
    - PLAN-0042-v2
    - DIFF-0042-v1
```

---

## 3. Finding Contract

```yaml
code_review_finding:
  id: CRF-01

  category:
    task_conformance | plan_conformance | scope | correctness | architecture | dependency | api_compatibility | data_integrity | transactionality | security | performance | error_handling | testing | maintainability | documentation | missing_context | missing_requirement | other

  severity:
    info | minor | major | critical

  status:
    open | resolved | accepted_risk | obsolete

  location:
    file: string | null
    symbol: string | null
    object_ref: string | null

  summary: string

  evidence:
    - ref: string
      detail: string

  impact: string

  required_change: string

  suggested_route:
    implementation | planning | analysis | context | user | blocked

  confidence:
    high | medium | low
```

---

## 4. Changes Required

```yaml
code_review_result:
  result: changes_required

  findings:
    - id: CRF-01
      category: correctness
      severity: major

      location:
        file: src/payment/service.py
        symbol: PaymentService.cancel

      summary: >
        Payment state is changed before validation succeeds.

      impact: >
        Validation failure can leave an invalid intermediate state.

      required_change: >
        Preserve validation-before-mutation behavior.

      suggested_route: implementation

  route:
    target: implementation
    reason: implementation_defect
```

---

## 5. Replanning Required

```yaml
code_review_result:
  result: replanning_required

  findings:
    - id: CRF-02
      category: architecture
      severity: major

      summary: >
        The approved plan cannot preserve the required transaction
        invariant without changing the service boundary.

      required_change: >
        Revisit implementation strategy and service boundary.

      suggested_route: planning

  route:
    target: planning
    reason: approved_plan_invalidated
```

---

## 6. Reanalysis Required

```yaml
code_review_result:
  result: reanalysis_required

  findings:
    - id: CRF-03
      category: dependency
      severity: major

      summary: >
        Implementation revealed another active consumer that was
        absent from the original impact analysis.

      suggested_route: analysis

  route:
    target: analysis
```

---

## 7. More Context Required

```yaml
code_review_result:
  result: more_context_required

  context_request:
    mode: expand

    need:
      - all consumers of PaymentService.cancel

    reason: >
      Compatibility impact cannot be verified with the current context.

  route:
    target: context
```

---

## 8. User Input Required

```yaml
code_review_result:
  result: user_input_required

  questions:
    - >
      Is breaking the legacy internal API acceptable for this task?

  route:
    target: user
```

---

## 9. Feedback to Implementation

```yaml
code_review_feedback:
  review_ref: CODE-REVIEW-0042-v1
  implementation_ref: IMPLEMENTATION-0042-v1

  required_changes:
    - finding_ref: CRF-01
      required_change: >
        Preserve validation-before-mutation behavior.

  constraints_to_preserve:
    - public API unchanged

  unchanged_plan_expected: true
```

Implementation receives this structured feedback, not the reviewer's private reasoning.

---

## 10. Delta Review Request

```yaml
delta_code_review_request:
  current_implementation_ref: IMPLEMENTATION-0042-v2
  previous_implementation_ref: IMPLEMENTATION-0042-v1

  current_diff_ref: DIFF-0042-v2
  previous_review_ref: CODE-REVIEW-0042-v1

  previous_open_findings:
    - CRF-01

  changed_scope:
    files:
      - src/payment/service.py
```

Delta review verifies:

```text
previous findings resolved
fix itself is correct
no new regression introduced
scope did not unexpectedly expand
```

---

## 11. Finding Resolution

```yaml
finding_resolution:
  review_ref: CODE-REVIEW-0042-v2
  finding_ref: CRF-01

  status: resolved

  evidence:
    - src/payment/service.py:PaymentService.cancel
```

---

## 12. Review Cycle Exhaustion

```yaml
code_review_exhausted:
  implementation_ref: IMPLEMENTATION-0042-v2

  cycles_used: 2

  unresolved_findings:
    - CRF-05

  recommended_route:
    implementation_escalation | planning | analysis | context | user | blocked
```

No automatic third Implementation↔Code Review cycle.

---

## 13. Contract rules

- reviewer does not modify source code;
- major/critical findings require concrete evidence;
- findings route to the stage that owns the defect;
- finding identity persists across review cycles;
- Code Review uses actual diff/workspace evidence;
- approval does not replace Testing;
- artifacts contain no private chain-of-thought.
