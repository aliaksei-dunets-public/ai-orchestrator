# Development Specification — Architecture and Contract

> **Актуализация 2026-09-17:** прежнее требование Specification заменено карточкой Task Manager; specification.md не обязательна. Task lifecycle — SQLite, immutable рабочие артефакты — Artifact Repository, шаг/WaitState — память Graph Runtime. Действующий минимальный [контракт подготовки](../architecture/preparation-workflow.md) останавливается на Package → Ready, не запускает исполнение. Остальной текст — импортированный проектный исходник.

**Status:** Accepted design v0.1  
**Scope:** Durable synthesis produced by Development Preparation before Planning

## 1. Purpose

The Development Specification is the first durable knowledge document produced by task preparation.

It is the normalized result of:

```text
Task
 +
Context discovery
 +
Analysis / Investigation
 +
Impact Analysis
        ↓
Development Specification
```

It answers:

> What is the problem, what is true about the current system, what behavior/design is required, what constraints and impacts matter, and what must be preserved?

It does **not** describe the step-by-step implementation sequence. That belongs to the Implementation Plan.

---

## 2. Durable artifact model

At the `ready` boundary, the executor should not require the previous conversation or raw preparation scratch state.

The durable human-readable preparation documents are:

```text
1. specification.md
2. plan.md
```

The executor receives:

```text
Task
+
Development Specification
+
Approved Implementation Plan
+
Project Profile
```

`Context Package`, `Implementation Analysis`, and `Impact Analysis` are preparation working artifacts. They may be retained for diagnostics according to retention policy, but they are not required inputs for normal execution after `ready`.

---

## 3. Location

Recommended v1 task layout:

```text
.orchestrator/tasks/TASK-0042/
├── task.yaml
├── specification.md
├── plan.md
└── events.jsonl
```

The paths are stable for the lifetime of the Task.

---

## 4. Specification content

A Development Specification should contain only evidence-backed information needed to understand the change.

Recommended sections:

```text
Problem / Objective
Current Behavior
Target Behavior
Scope / Non-goals
Domain / Business Rules
Validations / Invariants
Affected Components
Interfaces / Contracts
Data / State Impact
Integration Impact
Compatibility Requirements
Architecture / Design Constraints
Testing Expectations
Documentation Impact
Risks
Assumptions
Resolved Decisions
Open Questions
Evidence / Source References
Acceptance Criteria Mapping
```

Not every section must be populated for every task.

---

## 5. Domain and business behavior

The specification must capture business/domain semantics when they matter.

Example:

```text
Rule:
A settled payment cannot be cancelled.

Validation:
Cancellation after settlement is rejected.

Invariant:
A rejected cancellation must not mutate payment state.
```

Prefer behavioral language over implementation mechanics.

Bad:

```text
PaymentService.cancel checks field X before calling Y.
```

Preferred:

```text
Cancellation is allowed only before settlement completes.
```

---

## 6. Current and target behavior

The specification should make the delta explicit.

```yaml
behavior:
  current:
    - settled payment may remain in an invalid state after cancellation attempt

  target:
    - settled payment cancellation is rejected
    - rejection preserves current payment state
```

This makes Planning and later acceptance traceable.

---

## 7. Change surface

The specification contains the analyzed change surface, but not the execution sequence.

Example:

```yaml
change_surface:
  primary:
    - Payment domain cancellation behavior

  components:
    - PaymentService
    - PaymentRepository

  contracts:
    - Payment API cancellation semantics

  tests:
    - payment cancellation unit/integration coverage

  documentation:
    - payment lifecycle domain documentation
```

This is sufficient for Planning to decide exact file-level work.

---

## 8. Requirements and acceptance criteria

The specification refines the initial Task request without rewriting history.

The original user request remains immutable in Task metadata.

The specification may clarify:

```text
ambiguous success criteria
business rules
technical constraints
compatibility requirements
edge cases
non-goals
```

Any material interpretation that requires user authority must route to `needs_input` before the specification is considered sufficient.

---

## 9. Evidence discipline

Important claims should be traceable to evidence such as:

```text
source files / symbols
project documentation
schemas/contracts
configuration
existing tests
runtime evidence
user decisions
```

The specification must not contain hidden chain-of-thought or raw agent scratchpad.

It should record conclusions and references.

---

## 10. Specification synthesis

`Specification Synthesis` is a preparation node/action after Context + Analysis.

```text
Context
   ↓
Analysis / Impact
   ↓
Specification Synthesis
   ↓
Specification Sufficiency Check
   ↓
Planning
```

It is not a new large subgraph in v1.

Inputs:

```text
Task
Context Package
Implementation Analysis
Impact Analysis
Project Profile
relevant user decisions
```

Output:

```text
Development Specification
```

---

## 11. Specification sufficiency check

Before Planning, validate that the specification is:

```text
internally consistent
free of unresolved blocking ambiguity
clear about target behavior
clear about constraints/invariants
clear about affected scope at design level
traceable to evidence
sufficient for a zero-conversation planner
```

Possible outcomes:

```text
sufficient
needs_context
needs_analysis
needs_input
blocked
```

The check may repair minor formatting/normalization issues inline, but material semantic changes return to the owning stage.

---

## 12. User confirmation policy

Superpowers uses explicit human review of the written spec before Planning. The Orchestrator adopts the principle but makes it policy-driven rather than universally mandatory.

Candidate configuration:

```yaml
development:
  specification:
    user_confirmation: auto
```

Supported:

```text
off
auto
required
```

`auto` should request confirmation for material ambiguity, important business behavior decisions, high-risk architecture changes, or project policy requirements.

A normal evidence-backed technical specification does not require an extra human gate solely because a file was written.

---

## 13. Versioning

Specifications are immutable/versioned logically.

Example:

```text
SPEC-0042-v1
SPEC-0042-v2
```

The stable task path may remain:

```text
.orchestrator/tasks/TASK-0042/specification.md
```

while Task metadata/event history records the current specification version/hash.

Material specification revision invalidates any Plan derived from the previous specification.

---

## 14. Candidate structured contract

```yaml
development_specification:
  id: SPEC-0042-v1
  task_ref: TASK-0042

  problem:
    summary: string

  objective: string

  behavior:
    current: []
    target: []

  scope:
    in: []
    out: []

  domain:
    rules: []
    validations: []
    invariants: []
    state_transitions: []
    edge_cases: []

  change_surface:
    components: []
    contracts: []
    data: []
    integrations: []
    tests: []
    documentation: []

  constraints: []
  compatibility: []
  risks: []
  assumptions: []
  resolved_decisions: []
  open_questions: []

  acceptance_criteria: []
  evidence_refs: []

  prepared_source_revision: abc123
```

The Markdown document is the human/agent-readable source. Structured metadata may be extracted or stored alongside Task state for deterministic checks.

---

## 15. Accepted decisions

1. Specification is a durable preparation artifact.
2. It is produced after Context + Analysis and before Planning.
3. Context/Analysis are working artifacts, not normal executor inputs.
4. Specification describes the problem/design/behavior, not implementation steps.
5. Business rules, validations, invariants, and edge cases are first-class content.
6. Material specification changes invalidate the derived Plan.
7. User confirmation is policy-driven, not universally mandatory.
8. Executor must not need preparation conversation history.
