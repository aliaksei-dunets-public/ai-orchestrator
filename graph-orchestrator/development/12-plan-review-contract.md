# Plan Review Contract

**Status:** Candidate artifact contract v0.2

## 1. Review Request

```yaml
plan_review_request:
  task_ref: TASK-0042
  specification_ref: SPEC-0042-v1
  plan_ref: PLAN-0042-v1
  project_profile_ref: PROJECT-PROFILE

  previous_review_ref: null

  policy:
    review_depth: auto
    max_review_cycles: 2
```

The reviewer does not need raw Context/Analysis in the normal path. It may request re-preparation if the Specification itself is insufficient.

---

## 2. Review Result

```yaml
plan_review_result:
  id: PLAN-REVIEW-0042-v1

  task_ref: TASK-0042
  specification_ref: SPEC-0042-v1
  plan_ref: PLAN-0042-v1

  cycle: 1
  review_depth: standard

  result:
    approved | changes_required | specification_revision_required | user_input_required | blocked | failure

  findings: []

  specification_coverage:
    complete: false
    uncovered_refs: []

  zero_context_executable: false

  route:
    target: planning
    reason: planning_defect
```

---

## 3. Finding Contract

```yaml
plan_review_finding:
  id: PRF-01

  category:
    task_alignment |
    specification_coverage |
    scope |
    architecture |
    file_object_structure |
    interface |
    dependency |
    compatibility |
    security |
    data_integrity |
    performance |
    testing |
    documentation |
    implementability |
    missing_requirement |
    risk |
    other

  severity:
    info | minor | major | critical

  status:
    open | resolved | accepted_risk | obsolete

  summary: string

  location:
    plan_work_units: []
    specification_refs: []

  evidence: []
  impact: string
  required_change: string

  suggested_route:
    planning | specification | user | blocked

  confidence:
    high | medium | low
```

---

## 4. Approved / readiness handoff

```yaml
plan_review_result:
  result: approved

  specification_coverage:
    complete: true
    uncovered_refs: []

  zero_context_executable: true

  approved_binding:
    specification_ref: SPEC-0042-v1
    specification_hash: sha256:...
    plan_ref: PLAN-0042-v2
    plan_hash: sha256:...

  route:
    target: build_execution_package
    reason: preparation_approved
```

A deterministic action builds the Execution Package from the approved binding.

```yaml
execution_package:
  task_ref: TASK-0042
  specification_ref: SPEC-0042-v1
  specification_hash: sha256:...
  plan_ref: PLAN-0042-v2
  plan_hash: sha256:...
  plan_review_ref: PLAN-REVIEW-0042-v2
  prepared_source_revision: abc123
```

TaskManagerService then evaluates `preparing → ready`.

---

## 5. Changes Required

Use when Specification is sound but Plan must change.

```yaml
plan_review_result:
  result: changes_required

  findings:
    - id: PRF-01
      category: specification_coverage
      severity: major
      summary: Plan omits the state-preservation invariant.
      required_change: Add implementation and validation coverage for the invariant.
      suggested_route: planning

  route:
    target: planning
```

---

## 6. Specification Revision Required

Use when the durable Specification itself is incomplete, inconsistent, or contradicted by evidence.

```yaml
plan_review_result:
  result: specification_revision_required

  findings:
    - id: PRF-02
      category: missing_requirement
      severity: major
      summary: Compatibility behavior for an active API consumer is not specified.
      required_change: Re-enter preparation and update the Specification from evidence.
      suggested_route: specification

  route:
    target: preparation
```

Preparation decides whether Context, Analysis, or user input is required before issuing a new Specification version.

---

## 7. User Input Required

```yaml
plan_review_result:
  result: user_input_required

  questions:
    - Must backward compatibility be preserved for the legacy API consumer?

  route:
    target: user
```

---

## 8. Feedback to Planning

```yaml
plan_review_feedback:
  review_ref: PLAN-REVIEW-0042-v1
  specification_ref: SPEC-0042-v1
  plan_ref: PLAN-0042-v1

  required_changes:
    - finding_ref: PRF-01
      required_change: Preserve validation-before-mutation behavior.

  constraints_to_preserve:
    - public API unchanged
```

Planning receives structured findings, not reviewer scratchpad.

---

## 9. Review cycle exhaustion

After two direct Planning↔Plan Review cycles, diagnose root cause rather than starting a blind third cycle.

```text
specification issue → preparation
requirement ambiguity → user
review uncertainty → model/policy escalation
persistent contradiction → blocked/human decision
```

---

## 10. Contract rules

- approval is bound to exact Specification + Plan versions/hashes;
- any material Specification revision invalidates Plan approval;
- major/critical findings require evidence;
- Plan Review checks Specification coverage, not raw planner reasoning;
- Plan must be executable from Task + Specification + Plan without prior conversation;
- artifacts contain no hidden chain-of-thought.
