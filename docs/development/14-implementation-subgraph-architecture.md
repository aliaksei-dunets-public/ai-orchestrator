# Implementation Subgraph Architecture

**Status:** Accepted design v0.2  
**Scope:** Development Workflow — execution of an approved Implementation Plan

## 1. v1 decision

For the first implementation of the AI Orchestrator, the `Implementation` stage uses **one implementation agent only**.

```text
APPROVED PLAN
      ↓
IMPLEMENTATION AGENT
      ↓
LOCAL VALIDATION
      ↓
IMPLEMENTATION RESULT
```

The agent executes the approved plan from start to finish.

Multi-agent segmentation, sequential delegation, parallel execution, integration workspaces, and implementation coordinators are explicitly deferred.

This keeps the first runtime simple and makes it possible to evaluate whether multi-agent execution is actually beneficial before adding orchestration complexity.

---

## 2. Why single-agent first

The default single-agent model provides:

- one coherent project understanding;
- minimal handoff overhead;
- no cross-agent merge problem;
- no implementation partitioning problem;
- simpler debugging;
- simpler checkpoint/resume semantics;
- simpler observability;
- lower runtime complexity.

The first version should optimize for reliability and architectural clarity rather than maximum concurrency.

---

## 3. Implementation remains a subgraph

Although v1 uses one agent, `Implementation` remains modeled as a subgraph.

Reason:

- it has its own inputs/outputs;
- it may request additional context;
- it performs local validation;
- it may detect a material plan deviation;
- it may need bounded retries;
- future execution strategies can be added internally without changing the parent Development Workflow contract.

This preserves extensibility without implementing multi-agent behavior prematurely.

---

## 4. High-level flow

```text
IMPLEMENTATION REQUEST
      │
      ▼
1. VALIDATE INPUTS
      │
      ▼
2. PREPARE IMPLEMENTATION CONTEXT
      │
      ▼
3. EXECUTE APPROVED PLAN
      │
      ▼
4. LOCAL VALIDATION
      │
      ▼
5. CLASSIFY DEVIATIONS / ISSUES
      │
      ├── needs_context ───────► CONTEXT EXPANSION
      ├── plan_change_required ► PLANNING
      ├── needs_input ─────────► ASK USER
      ├── blocked ─────────────► TASK BLOCKED
      └── success
              │
              ▼
6. BUILD IMPLEMENTATION RESULT
```

---

## 5. Inputs

The implementation agent receives:

```text
Task Artifact
Approved Implementation Plan
Implementation Analysis
Context Package
Project Profile
optional previous implementation feedback
```

It should not receive unrelated orchestration history or hidden reasoning from previous agents.

---

## 6. Execution responsibility

The implementation agent is responsible for:

- executing all approved plan steps;
- respecting plan dependencies;
- making the required repository/project changes;
- preserving constraints and invariants;
- performing fast local validation;
- recording deviations from the plan;
- reporting unresolved issues;
- requesting more context when required.

The agent is not responsible for independently changing the approved architecture or task scope.

---

## 7. Plan authority

The approved plan is the implementation contract.

Minor execution adjustments are allowed when they do not materially change:

- architecture;
- task scope;
- public contracts;
- major dependencies;
- data migration behavior;
- risk profile.

Example of acceptable local adjustment:

```text
Use an existing helper discovered during implementation
instead of adding a duplicate helper.
```

Example of material change:

```text
Plan assumes no API change,
but implementation requires a breaking API change.
```

Material changes must route back to Planning and Plan Review.

---

## 8. Context expansion

Implementation may discover missing project information.

Example:

```yaml
result: needs_context

context_request:
  mode: expand
  need:
    - transaction behavior around PaymentService.cancel
```

Flow:

```text
Implementation
      ↓
Context Expand
      ↓
Implementation resumes
```

The implementation agent should not guess project behavior when evidence can be retrieved.

---

## 9. Local validation

Implementation performs fast feedback checks where available:

```text
syntax / compile
build
lint/static checks
targeted unit tests
affected-component tests
basic runtime validation
```

This is not the final Testing Subgraph.

Local validation answers:

> Is the implementation internally coherent enough to hand off to Code Review?

The later Testing Subgraph remains authoritative for the full verification strategy.

---

## 10. Failure and issue outcomes

Recommended outcomes:

```yaml
result:
  enum:
    - success
    - needs_context
    - needs_input
    - plan_change_required
    - blocked
    - retryable_failure
    - failure
```

### `needs_context`

Missing project evidence can resolve the issue.

### `needs_input`

A requirement/business decision is needed.

### `plan_change_required`

The approved plan is no longer valid.

### `blocked`

An external or hard technical blocker prevents implementation.

### `retryable_failure`

A bounded transient/tool execution problem occurred.

### `failure`

Implementation failed and cannot safely continue under current policy.

---

## 11. Retry policy

Retries should be bounded.

Candidate default:

```yaml
implementation:
  max_retries: 1
```

A retry should be used for:

- transient tool failure;
- correctable mechanical execution failure.

A retry should not be used to hide:

- plan defects;
- missing requirements;
- missing context;
- architecture contradictions.

Those must route to the correct upstream stage.

---

## 12. Implementation Result

The final output should summarize the actual project changes.

It must include:

```text
changed files / objects
changed symbols/components
completed plan steps
plan deviations
local validation
unresolved issues
workspace/revision reference
```

Code Review then receives this artifact plus the actual diff/workspace.

---

## 13. Code Review handoff

```text
IMPLEMENTATION RESULT
        +
PROJECT DIFF / WORKSPACE
        +
APPROVED PLAN
        +
TASK
        ↓
CODE REVIEW
```

Code Review should review the real implementation, not the implementation agent's internal reasoning.

---

## 14. Future extension point

The Implementation subgraph deliberately keeps an internal execution-policy boundary.

Future versions may introduce:

```text
segmented sequential execution
multiple specialized agents
parallel execution
isolated workspaces
integration stage
```

without changing the external contract:

```text
Approved Plan
      ↓
Implementation
      ↓
Implementation Result
```

These capabilities are not part of v1.

---

## 15. Accepted decisions

1. v1 uses exactly one implementation agent.
2. The agent executes the approved plan end-to-end.
3. Implementation remains a subgraph for lifecycle/routing extensibility.
4. No segmentation or parallel execution is implemented in v1.
5. Local validation is part of Implementation.
6. Material plan deviations route back to Planning + Plan Review.
7. Missing project evidence routes to Context expansion.
8. Code Review remains a separate independent gate.
9. Multi-agent execution is a future optimization only if practical evidence justifies it.


---

## 16. TDD execution mode

The single Implementation agent may execute individual plan steps in TDD mode.

```text
RED
 ↓
GREEN
 ↓
REFACTOR
```

This does not introduce additional implementation agents.

The TDD loop is internal to the same Implementation Subgraph and agent.

Implementation Result records test-first evidence where applicable.

TDD is selected by approved Plan + Project Profile policy, not improvised silently by the Implementation agent.
