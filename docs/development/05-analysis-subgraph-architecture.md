# Development Analysis Subgraph

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted design draft v0.1  
**Scope:** Development Workflow — stage after Context and before Planning

## 1. Purpose

The Analysis stage converts:

```text
Task Artifact
+
Context Package
+
Project Profile
```

into a project-specific understanding of **what must change and what may be affected**.

It must answer:

- where the requested change belongs;
- what project elements are likely to be modified;
- what contracts and dependencies may be affected;
- what constraints must be preserved;
- what risks and unknowns exist;
- whether enough evidence exists to continue to Planning.

It must **not** produce the detailed implementation sequence.

That belongs to Planning.

---

## 2. Boundary with neighboring stages

### Context

Answers:

> What project information is relevant?

Output:

```text
Context Package
```

### Analysis

Answers:

> Given the task and context, what does the project actually need to change?

Output:

```text
Implementation Analysis
```

### Planning

Answers:

> How exactly should we implement those changes?

Output:

```text
Implementation Plan
```

The separation is intentional:

```text
CONTEXT
find relevant evidence
      ↓
ANALYSIS
understand change surface and constraints
      ↓
PLANNING
design implementation steps
```

---

## 3. Analysis should be a reusable subgraph

The original Development graph modeled Analysis as a single agent node.

The refined design treats it as a reusable subgraph:

```yaml
analysis:
  type: subgraph
  ref: analysis

  config:
    intent: implementation

  inputs:
    - task
    - context_package
    - project_profile

  outputs:
    - implementation_analysis
```

Why a subgraph:

- complex tasks may require several analysis passes;
- context expansion may be needed;
- impact analysis is reusable elsewhere;
- deterministic and AI-driven operations can be separated;
- the same analysis capability can be reused by bugfix/refactoring/migration workflows.

For trivial tasks, the runtime may execute a compact path inside the subgraph rather than materializing every internal stage.

---

## 4. High-level flow

```text
ANALYSIS REQUEST
      │
      ▼
1. CHECK INPUT SUFFICIENCY
      │
      ├── missing context ─────► CONTEXT EXPANSION
      │                             │
      │                             └────► retry
      ▼
2. IDENTIFY CHANGE SURFACE
      │
      ▼
3. IMPACT ANALYSIS
      │
      ▼
4. CONSTRAINT / INVARIANT ANALYSIS
      │
      ▼
5. RISK / UNCERTAINTY ANALYSIS
      │
      ▼
6. ANALYSIS SUFFICIENCY GATE
      │
      ├── needs context ───────► CONTEXT EXPANSION
      ├── needs user input ────► ASK USER
      ├── blocked ─────────────► BLOCKED
      └── sufficient
              │
              ▼
7. BUILD IMPLEMENTATION ANALYSIS
```

---

## 5. Stage 1 — Check Input Sufficiency

**Type:** gate / cheap agent

Inputs:

- Task Artifact;
- Context Package;
- Project Profile.

Checks:

- task objective is understandable;
- acceptance criteria are sufficient for technical analysis;
- relevant project area has been identified;
- Context Package contains enough evidence to begin;
- no critical unresolved contradiction prevents analysis.

Possible results:

```yaml
result:
  enum:
    - sufficient
    - needs_context
    - needs_input
    - blocked
```

This is a cheap early exit before expensive reasoning.

---

## 6. Stage 2 — Identify Change Surface

**Type:** agent node

Purpose:

> Identify the smallest plausible project surface that may require change.

Candidate categories:

```text
source components
APIs / public contracts
data model
configuration
tests
documentation
integration boundaries
dependencies
```

Example:

```yaml
change_surface:
  primary:
    - PaymentService

  secondary:
    - PaymentRepository
    - PaymentServiceTest

  contracts:
    - Payment API

  data:
    - Payment entity
```

This is not yet the implementation plan.

---

## 7. Stage 3 — Impact Analysis

**Type:** reusable subgraph  
**Ref:** `impact-analysis`

Purpose:

> Determine what may be affected if the identified change surface changes.

Inputs:

```text
task
context package
change surface
project profile
```

Outputs:

```text
Impact Analysis Artifact
```

Candidate impact dimensions:

```text
callers / consumers
dependencies
public APIs
data access
tests
configuration
documentation
security boundary
performance-sensitive path
integration boundary
backward compatibility
```

This subgraph is designed for reuse by:

- Development Analysis;
- Refactoring;
- Migration;
- Code Review;
- Documentation Impact;
- Testing selection;
- Knowledge Refresh, if enabled in the future.

---

## 8. Stage 4 — Constraint / Invariant Analysis

**Type:** agent node

Identify conditions the implementation must preserve.

Examples:

```text
public API compatibility
transaction boundaries
data invariants
authorization rules
clean-core constraints
framework conventions
naming rules
performance limits
deployment constraints
```

Output:

```yaml
constraints:
  must_preserve: []
  must_follow: []
  prohibited: []
```

This stage does not decide exact implementation mechanics.

---

## 9. Stage 5 — Risk / Uncertainty Analysis

**Type:** agent node

Identify:

- high-risk project areas;
- missing evidence;
- ambiguous behavior;
- assumptions;
- potential regression zones;
- unresolved dependencies.

Example:

```yaml
risks:
  - id: RISK-1
    severity: medium
    description: >
      Cancellation behavior is shared with the settlement workflow.

unknowns:
  - exact behavior for partially settled payments
```

Risk discovery influences Planning and later Review/Testing.

---

## 10. Stage 6 — Analysis Sufficiency Gate

**Type:** gate

The analysis must not fabricate missing project facts.

Outcomes:

```yaml
result:
  enum:
    - success
    - needs_context
    - needs_input
    - blocked
    - failure
```

### `needs_context`

More project evidence can resolve the uncertainty.

Route:

```text
Analysis
   ↓
Context(mode=expand)
   ↓
Analysis retry
```

### `needs_input`

Only the user or external stakeholder can clarify the requirement.

Route:

```text
Analysis
   ↓
Ask User
   ↓
Analysis retry
```

### `blocked`

The task cannot safely proceed due to a genuine blocker.

Examples:

- required dependency unavailable;
- environment/tool access missing;
- contradictory mandatory constraints;
- unsupported platform capability.

`blocked` is different from `failure`.

---

## 11. Stage 7 — Build Implementation Analysis

**Type:** artifact builder

Produces the canonical `Implementation Analysis` artifact.

The artifact summarizes conclusions while retaining references to supporting Context evidence.

It should be concise enough for Planning, but detailed enough that Planning does not need to repeat the entire analysis.

---

## 12. What Analysis must NOT do

Analysis must not:

- edit code;
- create the detailed implementation sequence;
- select exact line-by-line changes unless necessary as evidence;
- approve its own conclusions as final project validation;
- run the Code Review;
- decide test pass/fail;
- silently invent missing requirements.

---

## 13. Context expansion loop

Analysis is allowed to request additional context multiple times, but loops must be bounded.

Candidate policy:

```yaml
context_expansion:
  max_iterations: 2

  on_exhausted:
    route: needs_input_or_blocked
```

The exact number remains configurable.

---

## 14. Reusable Impact Analysis Subgraph

Candidate internal contract:

```yaml
impact_request:
  intent: implementation

  roots:
    - PaymentService

  dimensions:
    - dependencies
    - consumers
    - api
    - data
    - tests
    - documentation
```

Output:

```yaml
impact_result:
  affected_components: []
  affected_contracts: []
  affected_data: []
  affected_tests: []
  affected_docs: []
  integration_impacts: []
  risk_flags: []
  evidence_refs: []
```

The caller decides what to do with this result.

`impact-analysis` does not route directly to Planning, Code Review, or Testing.

This is important for reuse.

---

## 15. Model policy

Recommended:

| Internal stage | Execution |
|---|---|
| Input sufficiency | cheap |
| Change surface | standard |
| Impact Analysis | deterministic-first + standard |
| Constraints | standard |
| Risk/uncertainty | standard |
| Ambiguous/high-risk analysis | expert escalation |
| Artifact construction | cheap/standard |

For simple tasks the runtime may use a cheaper compact path.

---

## 16. Development Workflow patch

The top-level Development Workflow becomes:

```text
Context Subgraph
      ↓
Analysis Subgraph
      ↓
Planning
      ↓
Plan Review
      ↓
...
```

Candidate node:

```yaml
analysis:
  type: subgraph
  ref: analysis

  config:
    intent: implementation

  execution:
    model_profile: standard
    escalation_profile: expert

  inputs:
    required:
      - task
      - context_package
      - project_profile

  outputs:
    artifact: implementation_analysis
    result:
      enum:
        - success
        - needs_context
        - needs_input
        - blocked
        - failure

  transitions:
    success: planning
    needs_context: context_expand
    needs_input: ask_user
    blocked: task_blocked
    failure: development_failed
```

---

## 17. Reuse strategy

The reusable generic analysis capability can support multiple workflows by changing `intent` and policy.

Candidate intents:

```text
implementation
bugfix
refactoring
migration
```

The common subgraph remains:

```text
sufficiency
change surface
impact
constraints
risk
artifact
```

But each intent may supply:

- different prompt/skill profile;
- different impact dimensions;
- different required fields;
- different risk rules.

Investigation and Incident should **not automatically** reuse the whole Development Analysis subgraph because their primary goal is evidence/root-cause discovery, not change design.

They may still reuse smaller subgraphs such as:

```text
Context
Impact Analysis
Evidence Validation
Risk Assessment
```

---

## 18. Accepted decisions

1. Development Analysis becomes a subgraph.
2. Analysis is distinct from Context and Planning.
3. `Impact Analysis` is extracted as a reusable subgraph.
4. Context expansion is a first-class Analysis outcome.
5. Analysis can return `blocked`.
6. The subgraph is reusable for implementation/bugfix/refactoring/migration through `intent`.
7. Investigation/Incident reuse lower-level subgraphs rather than the full Development Analysis flow by default.
8. The caller owns routing; reusable subgraphs return outcomes/artifacts.


---

## 16. Durability and Specification synthesis

Within Development Preparation, `Context Package`, `Implementation Analysis`, and `Impact Analysis` are working artifacts.

They are inputs to a later `Specification Synthesis` action:

```text
Task + Context + Analysis + Impact
              ↓
Development Specification
```

The Specification is the durable technical/domain understanding consumed by Planning and later execution.

The normal executor does not require raw Analysis artifacts after the Task reaches `ready`.

This preserves Analysis as a reusable subgraph while preventing preparation-internal artifacts from becoming permanent cross-session dependencies.
