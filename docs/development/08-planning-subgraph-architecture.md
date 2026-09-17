# Planning Subgraph Architecture

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted design v0.2  
**Scope:** Development Workflow — stage after Analysis and before Plan Review

## 1. Recommendation

Planning should be implemented as a **reusable subgraph**, not as one monolithic agent node. Planning consumes the durable Development Specification rather than depending on raw preparation context.

Reason:

- it has a stable artifact contract;
- it benefits from a simple/standard/complex execution path;
- it may need context or analysis expansion;
- it must support revision after Plan Review feedback;
- it is reusable for implementation, bugfix, refactoring, and migration;
- deterministic normalization and dependency ordering can be separated from AI reasoning.

Plan Review remains a separate independent gate.

Planning must not approve its own plan.

---

## 2. Boundary with neighboring stages

### Context + Analysis

Produce working evidence and technical understanding.

### Development Specification

Answers:

> What is the analyzed problem/design/behavior contract that implementation must satisfy?

Output:

```text
Development Specification
```

### Planning

Answers:

> What concrete implementation work should be performed to realize the Specification?

Output:

```text
Implementation Plan
```

### Plan Review

Answers:

> Does the Plan fully and safely realize the current Specification and Task?

The durable boundary is:

```text
CONTEXT / ANALYSIS
working reasoning
      ↓
SPECIFICATION
what must be true/change
      ↓
PLANNING
how to implement it
      ↓
PLAN REVIEW
independent verification
```

---

## 3. High-level Planning flow

```text
PLANNING REQUEST
      │
      ▼
1. CHECK SPECIFICATION SUFFICIENCY
      │
      ├── specification gap ───► SPECIFICATION PREPARATION
      └── sufficient
              │
              ▼
2. SCOPE CHECK
      │
      ▼
3. SELECT PLANNING DEPTH
      │
      ▼
4. DEFINE IMPLEMENTATION STRATEGY
      │
      ▼
5. MAP FILE / OBJECT STRUCTURE
      │
      ▼
6. DEFINE GLOBAL CONSTRAINTS
      │
      ▼
7. DECOMPOSE INTO WORK UNITS
      │
      ▼
8. DEFINE UNIT INTERFACES / DEPENDENCIES
      │
      ▼
9. DEFINE VALIDATION PER UNIT
      │
      ▼
10. ADD RISK / ROLLBACK NOTES
      │
      ▼
11. NORMALIZE + COMPLETENESS CHECK
      │
      ▼
IMPLEMENTATION PLAN
```

This incorporates selected strengths from Superpowers `writing-plans`: scope check, file/object structure, explicit global constraints, interfaces, and zero-context executability.

---

## 4. Stage 1 — Check Specification Sufficiency

**Type:** gate

Inputs:

- Task Artifact;
- Development Specification;
- Project Profile;
- optional Plan Review feedback;
- optional previous Plan.

Possible outcomes:

```yaml
result:
  enum:
    - sufficient
    - specification_revision_required
    - needs_input
    - blocked
```

Planning must not compensate for an incomplete Specification by inventing project facts.

A material gap routes back to Context/Analysis/Specification Synthesis through the preparation workflow.

---

## 5. Stage 2 — Scope Check

Before detailed planning, verify that the Specification can produce one coherent executable Plan.

Check for:

```text
multiple independent subsystems
unrelated objectives bundled together
work that cannot share one acceptance boundary
scope too broad for reliable implementation/review
```

For v1, do not automatically split Tasks. Return a scope finding or request explicit decomposition when necessary.

---

## 6. Stage 3 — Select Planning Depth

**Type:** deterministic-first router

Candidate depth:

```text
simple
standard
complex
```

### Simple

For small bounded changes.

Example:

```text
one component
low risk
no schema/API migration
few dependencies
```

### Standard

Default.

### Complex

For:

```text
cross-module changes
data migrations
public API changes
architecture changes
high-risk integrations
multi-stage rollout
```

This is execution policy, not a different artifact format.

---

## 7. Stage 4 — Define Implementation Strategy

**Type:** agent node

Purpose:

> Choose the high-level technical approach that satisfies the Analysis constraints.

The strategy should remain concise.

Example:

```yaml
strategy:
  summary: >
    Introduce a reusable health-check capability and keep
    project-specific checks behind adapters.

  key_decisions:
    - reuse existing capability registry
    - keep checks read-only by default
    - return structured findings
```

Planning may make implementation decisions, but every important decision should be traceable to:

```text
Task
Analysis
Project constraints
Evidence
```

---

## 8. Stage 5 — Map File / Object Structure

Before defining work units, map the concrete project objects that will be created or modified and their responsibilities.

For file-based projects:

```text
exact paths
important symbols
responsibility
create / modify / test
```

For object-centric platforms such as SAP/ABAP:

```text
classes/interfaces
CDS entities
behavior definitions
service definitions
UI artifacts
configuration objects
```

Follow existing project structure; do not introduce unrelated restructuring merely to satisfy a preferred file size/style.

---

## 9. Stage 6 — Define Global Constraints

Copy critical cross-unit constraints from the current Specification into the Plan.

Examples:

```text
compatibility requirements
version/dependency limits
naming constraints
Clean Core/platform rules
security/data invariants
exact business behavior that every work unit must preserve
```

This deliberate duplication ensures executor/reviewer visibility without copying the entire Specification.

---

## 10. Stage 7 — Decompose Into Work Units

**Type:** agent node

The plan is decomposed into practical implementation units.

A work unit should:

- have one clear goal;
- identify affected project targets;
- define an expected result;
- be independently understandable;
- be large enough to avoid micro-planning;
- be small enough to implement/checkpoint reliably.

Bad:

```text
1. Open file.
2. Find method.
3. Add if statement.
```

Bad:

```text
1. Implement entire feature.
```

Preferred:

```text
1. Introduce the health-check result model.
2. Add universal health-check orchestration.
3. Add project adapter integration.
4. Add tests for healthy/degraded installations.
5. Update orchestrator documentation.
```

---

## 11. Stage 8 — Unit Interfaces and Dependency Ordering


Each meaningful unit may declare:

```yaml
interfaces:
  consumes: []
  produces: []
```

This makes dependencies concrete and future-proofs the Plan for possible segmented execution, while v1 still uses one implementation agent.

**Type:** deterministic + agent-assisted

Each step may define:

```yaml
depends_on:
  - STEP-01
```

The plan must form an executable dependency order.

Checks:

- no missing dependency refs;
- no cycles;
- required foundations precede consumers;
- migration/setup precedes dependent implementation;
- validation steps occur after relevant changes.

Where independent steps exist, the plan may indicate:

```yaml
parallelizable: true
```

The parent workflow may later exploit this.

Planning does not itself execute in parallel.

---

## 12. Stage 9 — Define Validation Per Unit

Each meaningful implementation step should state how its completion can be checked.

Example:

```yaml
validation:
  - unit test for result classification
  - existing capability registry tests remain green
```

This is **not** the final Testing Subgraph.

The purpose is to make the implementation plan testable and observable.

The later Testing Subgraph remains authoritative for actual test execution.

---

## 13. Stage 10 — Risk / Rollback Notes

For risky steps, Planning should describe:

- important regression risk;
- compatibility concern;
- migration concern;
- rollback/reversibility when relevant.

Example:

```yaml
risk:
  level: high
  reason: public contract change

rollback:
  strategy: preserve old endpoint until migration completes
```

Do not require rollback metadata for every trivial code edit.

---

## 14. Stage 11 — Normalize Plan

**Type:** deterministic artifact builder

Normalize:

- IDs;
- ordering;
- dependencies;
- target refs;
- validation fields;
- scope;
- plan version;
- source artifact refs.

The plan format should not depend on the LLM's prose style.

---

## 15. Stage 12 — Plan Completeness Check

**Type:** deterministic-first gate

This is **not Plan Review**.

It checks schema/process completeness only:

- all required fields exist;
- every step has a goal;
- dependencies are valid;
- no cycles;
- important Specification constraints are represented;
- no step is obviously outside task scope;
- unresolved blockers are explicit.

Possible outcomes:

```text
ready_for_review
needs_revision
needs_context
needs_analysis
blocked
failure
```

Plan quality/architecture judgment belongs to independent Plan Review.

---

## 16. Planning revision after Plan Review

Plan Review may return:

```yaml
result: changes_required

feedback:
  - add migration step before changing the schema
  - preserve compatibility with existing API consumers
```

Planning is then invoked with:

```text
previous plan
+
review feedback
+
original analysis/context
```

Flow:

```text
PLANNING v1
    ↓
PLAN REVIEW
    ↓ changes_required
PLANNING v2
```

The Planning Subgraph should modify only the necessary parts where possible instead of regenerating the entire plan blindly.

---

## 17. Versioning

Plans are immutable versions.

```text
PLAN-0042-v1
PLAN-0042-v2
PLAN-0042-v3
```

Each version records:

```text
parent plan
reason for revision
review feedback ref
analysis ref
context ref
```

This supports review loops and auditability.

---

## 18. Reuse

Recommended intents:

```text
implementation
bugfix
refactoring
migration
```

Possible future intents:

```text
configuration_change
dependency_upgrade
```

The common algorithm remains:

```text
strategy
decomposition
dependency ordering
validation definition
normalization
```

Intent-specific policy may control:

- required plan fields;
- risk rules;
- migration requirements;
- test requirements;
- rollback requirements.

Do not use this planning subgraph for pure investigation unless the investigation has become an execution task.

---

## 19. Side effects

Planning must have no repository side effects.

```yaml
effects:
  writes_repository: false
  writes_task_manager: false
  changes_project_state: false
```

It only creates/revises a Plan Artifact.

---

## 20. Model policy

Recommended:

| Stage | Execution |
|---|---|
| Input sufficiency | cheap |
| Planning depth | deterministic / cheap |
| Strategy | standard → expert for high risk |
| Work decomposition | standard |
| Dependency ordering | deterministic-first |
| Validation definition | standard |
| Risk/rollback | standard → expert if high risk |
| Normalization | deterministic |
| Completeness check | deterministic + cheap |

A simple task may use one standard model pass plus deterministic normalization.

---

## 21. Parent workflow contract

Candidate parent node:

```yaml
planning:
  type: subgraph
  ref: planning

  config:
    intent: implementation

  execution:
    model_profile: standard
    escalation_profile: expert

  inputs:
    required:
      - task
      - context_package
      - implementation_analysis
      - project_profile

    optional:
      - previous_plan
      - plan_review_feedback

  outputs:
    artifact: implementation_plan

    result:
      enum:
        - success
        - needs_context
        - needs_analysis
        - needs_input
        - blocked
        - failure

  transitions:
    success: plan_review
    needs_context: context_expand
    needs_analysis: analysis
    needs_input: ask_user
    blocked: task_blocked
    failure: development_failed
```

---

## 22. Accepted decisions

1. Planning becomes a reusable subgraph.
2. Plan Review remains a separate independent gate.
3. Planning supports simple/standard/complex internal paths.
4. Planning creates practical work units, not micro-steps.
5. Work units support dependency ordering and future parallelism.
6. Each important step defines validation expectations.
7. Plans are immutable/versioned artifacts.
8. Review feedback revises the prior plan instead of blindly regenerating it.
9. Planning has no repository side effects.
10. Implementation/bugfix/refactoring/migration reuse the same base planning contract.


---

## 23. TDD / testing-strategy integration

Planning determines the testing intent for implementation-relevant work units.

Candidate field:

```yaml
testing_strategy:
  mode:
    tdd | characterization | test_after | existing_tests | not_applicable

  level:
    unit | component | integration | contract | e2e

  behaviors: []
```

Planning does not create or execute tests.

For bug fixes, regression-first behavior should normally be planned.

For behavior-preserving refactoring, prefer characterization tests when existing coverage is insufficient.

The Project Profile may configure TDD mode:

```yaml
development:
  tdd:
    mode: off | auto | required
```

`auto` is the recommended default.


---

## 24. Zero-conversation executor requirement

A completed Plan must be executable in a fresh AI session when paired with:

```text
Task
Development Specification
Project Profile
```

The executor must not require:

```text
preparation conversation history
planner scratchpad
raw Context Package
raw Implementation Analysis
```

If a critical fact is needed for execution, it belongs in the Specification or Plan.
