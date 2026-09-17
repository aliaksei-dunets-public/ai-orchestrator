# Implementation Analysis Contract

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Candidate working-artifact contract v0.2

## 1. Analysis Request

```yaml
analysis_request:
  task_ref: TASK-0042
  intent: implementation

  context_ref: CONTEXT-0042-v2
  project_profile_ref: PROJECT-PROFILE

  previous_analysis_ref: null

  policy:
    max_context_expansions: 2
```

---

## 2. Implementation Analysis Artifact

```yaml
implementation_analysis:
  id: ANALYSIS-0042-v1
  task_ref: TASK-0042
  context_ref: CONTEXT-0042-v2

  objective_interpretation: >
    Add health-check functionality that inspects
    orchestrator installation in a target project.

  change_surface:
    primary:
      - ref: orchestrator/health
        reason: new capability location

    secondary:
      - ref: project-profile
        reason: health check requires project configuration

  affected_components:
    - ref: task-manager
      impact: low
      reason: may persist maintenance findings

  contracts:
    affected: []
    must_preserve: []

  data_model:
    affected: false
    notes: []

  configuration:
    affected: true
    refs:
      - project-profile

  dependencies:
    affected:
      - capability registry

  tests:
    likely_required:
      - health-check unit tests
      - project fixture integration tests

  documentation:
    likely_affected:
      - orchestrator architecture
      - project onboarding

  constraints:
    - remain platform agnostic
    - do not require Knowledge Map
    - reuse existing capability abstractions where possible

  invariants:
    - target-project audit must not modify project state by default

  risks:
    - id: RISK-1
      severity: medium
      summary: >
        Platform-specific checks may leak into universal health-check logic.

  assumptions:
    - adapters can expose installation diagnostics

  unknowns: []

  planning_guidance:
    - isolate universal health rules from project adapters
    - keep findings in a structured artifact

  evidence_refs:
    - docs/master-spec.md
    - docs/project-profile.md

  confidence: high
```

---

## 3. Analysis Result Envelope

```yaml
analysis_result:
  result:
    success | needs_context | needs_input | blocked | failure

  artifact_ref: ANALYSIS-0042-v1 | null

  context_request: null
  questions: []
  blocker: null
  error: null
```

---

## 4. Needs Context

```yaml
analysis_result:
  result: needs_context

  context_request:
    mode: expand

    need:
      - all consumers of PaymentRepository
      - transaction behavior around cancellation

    reason: >
      Current context is insufficient to determine regression impact.
```

---

## 5. Needs Input

```yaml
analysis_result:
  result: needs_input

  questions:
    - >
      Must the existing public API remain backward compatible,
      or may the contract change?
```

---

## 6. Blocked

```yaml
analysis_result:
  result: blocked

  blocker:
    type: missing_capability

    summary: >
      Required target-system metadata cannot be accessed
      with the currently available project capabilities.

    remediation:
      - enable the required project adapter
```

---

## 7. Artifact rules

The Implementation Analysis artifact should:

- describe findings, not implementation steps;
- reference evidence rather than reproduce excessive raw context;
- explicitly list unknowns and assumptions;
- distinguish likely impact from confirmed impact;
- capture constraints that Planning must obey;
- remain stable enough to survive a Planning retry.

It should not contain hidden chain-of-thought or agent scratchpad.


---

## 8. Durability policy

`Implementation Analysis` is a preparation working artifact by default.

It is not a required durable input for execution after `Task = ready`.

Its stable conclusions are synthesized into `Development Specification`.

Recommended retention:

```text
keep during preparation/execution diagnosis
prune after Task completion according to retention policy
```

If a later stage discovers material evidence missing from the Specification, the workflow returns to preparation and produces a new Specification version rather than relying on hidden Analysis state.
