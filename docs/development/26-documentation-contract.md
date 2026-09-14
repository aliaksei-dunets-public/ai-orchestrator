# Documentation Contract

**Status:** Candidate artifact contract v0.1

## 1. Documentation Request

```yaml
documentation_request:
  task_ref: TASK-0042

  analysis_ref: ANALYSIS-0042-v1
  plan_ref: PLAN-0042-v2
  implementation_ref: IMPLEMENTATION-0042-v2
  code_review_ref: CODE-REVIEW-0042-v2
  testing_ref: TESTING-0042-v1

  context_ref: CONTEXT-0042-v2
  project_profile_ref: PROJECT-PROFILE

  workspace_ref: WORKSPACE-TESTED
```

---

## 2. Documentation Impact Result

```yaml
documentation_impact:
  result:
    no_change | update_required | implementation_change_required | needs_context

  reasons:
    - new public capability

  targets:
    - ref: docs/health-check.md
      class: external_doc

  evidence_refs:
    - IMPLEMENTATION-0042-v2
    - TESTING-0042-v1
```

---

## 3. Documentation Target

```yaml
documentation_target:
  ref: docs/health-check.md

  class:
    external_doc | source_adjacent_doc | runtime_affecting_contract

  domain:
    domain_business | technical | architecture | api_contract | developer | operational

  authoritative: true

  reason: new_capability

  source_of_truth:
    - IMPLEMENTATION-0042-v2
    - TESTING-0042-v1

  required_changes:
    - document invocation
    - document result contract

  validation:
    - markdown_lint
    - broken_link_check
```

---

## 4. Documentation Update Record

```yaml
documentation_update:
  target_ref: docs/health-check.md

  result:
    updated | unchanged | failed

  changed_sections:
    - Usage
    - Result contract

  evidence_refs:
    - IMPLEMENTATION-0042-v2

  warnings: []
```

---

## 5. Documentation Validation

```yaml
documentation_validation:
  target_ref: docs/health-check.md

  status:
    passed | passed_with_warnings | failed

  checks:
    - type: markdown_lint
      status: passed

    - type: implementation_consistency
      status: passed

  warnings: []
  errors: []
```

---

## 6. Documentation Result

```yaml
documentation_result:
  id: DOC-0042-v1

  task_ref: TASK-0042

  result:
    success | no_change | needs_context | implementation_change_required | needs_input | blocked | failure

  impacted: true

  targets:
    - docs/health-check.md

  updates:
    - DOC-UPDATE-01

  validation_status: passed

  source_adjacent_changed: false

  post_documentation_route:
    target: final_validation

  maintenance_candidates: []

  warnings: []
```

---

## 7. No-change Result

```yaml
documentation_result:
  result: no_change
  impacted: false

  reason: >
    The implementation changed internal mechanics only and did not alter
    behavior, contracts, configuration, architecture, or developer usage.

  post_documentation_route:
    target: final_validation
```

---

## 8. Source-adjacent documentation result

```yaml
documentation_result:
  result: success

  source_adjacent_changed: true

  targets:
    - src/payment/service.py:PaymentService

  post_documentation_route:
    target: code_review_delta

  required_followup:
    - delta_code_review
    - targeted_validation
```

---

## 9. Runtime-affecting discovery

```yaml
documentation_result:
  result: implementation_change_required

  issue:
    summary: >
      The required API description is generated from runtime annotations,
      so updating it changes the executable contract.

    affected:
      - Payment API annotation

    materiality:
      minor | material

  post_documentation_route:
    target: implementation | planning
```

---

## 10. Maintenance Candidate

```yaml
documentation_maintenance_candidate:
  id: DOC-MAINT-01

  type: stale_documentation

  target: docs/legacy-payment.md

  summary: >
    A pre-existing unrelated section appears stale.

  related_to_current_task: false

  recommended_action:
    create_maintenance_task
```

---

## 11. Contract rules

- impact is evaluated before editing;
- no-change is explicit;
- every documentation target has a safety class;
- runtime-affecting targets are not silently edited in Documentation;
- source-adjacent edits expose required downstream validation;
- documentation truth references actual implementation/testing evidence;
- unrelated drift does not silently expand task scope.


---

## 12. Domain / Business Documentation Update

```yaml
documentation_target:
  ref: docs/domain/payment-lifecycle.md

  class: external_doc
  domain: domain_business

  reason: business_rule_changed

  source_of_truth:
    - ANALYSIS-0042-v1
    - IMPLEMENTATION-0042-v2
    - TESTING-0042-v1

  required_changes:
    - document cancellation eligibility
    - document settlement restriction
    - document state-preservation invariant on rejection

  business_changes:
    rules:
      - payment cancellation is allowed only before settlement completion

    validations:
      - settled payment cancellation is rejected

    state_transitions:
      - rejected cancellation does not change payment state

    edge_cases:
      - cancellation after partial processing follows settlement policy
```

Domain documentation describes behavior and rules, not implementation mechanics.

---

## 13. Documentation Domain

Candidate normalized values:

```yaml
documentation_domain:
  enum:
    - domain_business
    - technical
    - architecture
    - api_contract
    - developer
    - operational
```

A single task may produce multiple targets in different documentation domains.
