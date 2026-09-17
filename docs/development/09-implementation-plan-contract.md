# Implementation Plan Contract

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Candidate artifact contract v0.2

## 1. Planning Request

```yaml
planning_request:
  task_ref: TASK-0042
  specification_ref: SPEC-0042-v1
  project_profile_ref: PROJECT-PROFILE

  intent: implementation

  previous_plan_ref: null
  review_feedback_ref: null

  policy:
    depth: auto
```

Raw Context/Analysis are not normal Planning inputs after Specification synthesis.

---

## 2. Implementation Plan

```yaml
implementation_plan:
  id: PLAN-0042-v1
  task_ref: TASK-0042
  specification_ref: SPEC-0042-v1
  specification_hash: sha256:...

  parent_plan_ref: null
  revision_reason: initial

  intent: implementation
  depth: standard

  goal: >
    Correct payment cancellation behavior for settled payments.

  architecture:
    summary: >
      Preserve the existing payment lifecycle and add cancellation
      validation at the domain service boundary.

  global_constraints:
    - public API remains backward compatible
    - rejected cancellation must not mutate payment state
    - reuse existing transaction handling

  file_object_structure:
    - ref: src/payment/service.py
      action: modify
      responsibility: payment cancellation domain orchestration
      symbols:
        - PaymentService.cancel

    - ref: tests/payment/test_service.py
      action: modify
      responsibility: payment cancellation behavior tests

  scope:
    in:
      - cancellation validation
      - regression tests
      - affected domain documentation

    out:
      - unrelated payment refactoring

  work_units:
    - id: STEP-01
      title: Protect cancellation behavior with regression coverage

      goal: >
        Capture the required settled/unsettled cancellation behavior.

      files_objects:
        - tests/payment/test_service.py

      interfaces:
        consumes:
          - existing PaymentService public cancellation contract
        produces:
          - regression tests defining expected cancellation behavior

      depends_on: []

      testing_strategy:
        mode: tdd
        level:
          - unit

      expected_result:
        - failing regression case exists for settled-payment cancellation

      validation:
        - run targeted payment service tests and confirm expected RED state

      risk:
        level: low

    - id: STEP-02
      title: Implement settled-payment cancellation validation

      goal: >
        Reject cancellation after settlement while preserving state.

      files_objects:
        - src/payment/service.py:PaymentService.cancel

      interfaces:
        consumes:
          - regression behavior from STEP-01
        produces:
          - validated cancellation behavior preserving existing API

      depends_on:
        - STEP-01

      expected_result:
        - settled cancellation rejected
        - rejected operation does not mutate payment state

      validation:
        - targeted tests pass
        - existing payment cancellation tests remain green

      risk:
        level: medium
        reason: transaction/state invariant must be preserved

    - id: STEP-03
      title: Synchronize domain documentation

      goal: >
        Document the settled-payment cancellation rule.

      files_objects:
        - docs/domain/payment-lifecycle.md

      interfaces:
        consumes:
          - verified behavior from STEP-02
        produces:
          - updated domain/business documentation

      depends_on:
        - STEP-02

      expected_result:
        - documented business rule matches verified implementation behavior

      validation:
        - documentation consistency check

  global_validation:
    - targeted payment tests pass
    - required broader tests selected by Testing Subgraph pass
    - public cancellation contract remains compatible

  risks: []
  unresolved: []
```

---

## 3. File / Object Structure Contract

```yaml
file_object:
  ref: exact path or platform object identifier
  action: create | modify | delete | generated
  responsibility: string
  symbols: []
```

Use exact project references where known.

For ABAP/SAP, `ref` may be:

```text
class/interface name
CDS entity
behavior definition
service definition
UI artifact
configuration object
```

---

## 4. Work Unit Contract

```yaml
work_unit:
  id: string
  title: string
  goal: string

  files_objects: []

  interfaces:
    consumes: []
    produces: []

  depends_on: []

  testing_strategy:
    mode: tdd | characterization | test_after | existing_tests | not_applicable
    level: []

  expected_result: []
  validation: []

  risk:
    level: low | medium | high | critical
    reason: string | null

  rollback:
    required: boolean
    strategy: string | null
```

---

## 5. Planning Result Envelope

```yaml
planning_result:
  result:
    success | specification_revision_required | needs_input | blocked | failure

  artifact_ref: PLAN-0042-v1 | null

  specification_issue: null
  questions: []
  blocker: null
  error: null
```

---

## 6. Plan Revision Metadata

```yaml
plan_revision:
  plan_ref: PLAN-0042-v2
  parent_plan_ref: PLAN-0042-v1

  specification_ref: SPEC-0042-v1

  reason: plan_review_feedback
  review_feedback_ref: PLAN-REVIEW-0042-v1

  changed_work_units:
    - STEP-02

  unchanged_work_units:
    - STEP-01
    - STEP-03
```

A changed Specification requires a new Plan revision and invalidates prior approval.

---

## 7. Contract rules

The Plan must:

- be derived from the current Development Specification;
- preserve Specification requirements/invariants;
- include a scope check result;
- map concrete files/objects and responsibilities before work units;
- carry critical global constraints from the Specification;
- use meaningful work units rather than line-by-line microsteps;
- identify exact paths/objects/symbols where available;
- make dependencies and consumes/produces interfaces explicit where useful;
- define expected results and validation for meaningful work;
- include TDD/characterization strategy when applicable;
- expose unresolved items explicitly;
- be executable by a fresh agent with Task + Specification + Project Profile;
- not depend on preparation conversation history or raw Analysis artifacts.

---

## 8. Self-contained does not mean duplicated

The Plan may refer to the Specification for rationale and detailed domain background.

However, critical execution constraints must be copied into `global_constraints`, and each work unit must contain enough concrete information to execute safely without opening raw Context/Analysis artifacts.
