# Reusable Subgraph Design Rules

> **Актуализация 2026-09-15:** последовательная работа одного агента, общая оболочка результата и владение маршрутом согласованы в [упрощённом Workflow Run](../architecture/workflow-run.md). Runtime хранит процесс в памяти сессии; исходные правила не доказывают наличие реализации.

**Status:** Accepted architecture rules v0.1  
**Scope:** AI Orchestrator graph library

## 1. Goal

Reusable subgraphs should behave like stable orchestration components that can be called from multiple workflows without knowing the caller's internal graph.

Examples:

```text
Context
Impact Analysis
Testing
Documentation
Security Review
Evidence Validation
```

---

## 2. Core rule — caller owns routing

A reusable subgraph must not contain caller-specific transitions such as:

```text
goto: development.planning
```

Instead it returns:

```yaml
result: success
artifact: ...
```

The parent workflow decides:

```text
success → Planning
```

This is the most important reuse boundary.

---

## 3. Stable input/output contracts

A reusable subgraph should consume domain artifacts, not arbitrary parent-node state.

Good:

```yaml
inputs:
  task
  context_package
  project_profile
```

Bad:

```yaml
inputs:
  whatever_is_in_parent_memory
```

Outputs should be structured and versionable.

---

## 4. Explicit side effects

Prefer subgraphs that transform artifacts.

If a subgraph changes external state, the side effect must be explicit.

Example:

```yaml
effects:
  writes_repository: false
  writes_task_manager: false
```

A reusable analysis subgraph should not silently:

- change Task status;
- edit source code;
- persist workflow-specific state.

---

## 5. Parameterize policy, not business logic

Reuse should come from configuration such as:

```yaml
intent: implementation
risk_profile: standard
depth: normal
```

Do not create one universal subgraph full of caller-specific conditionals.

Bad:

```text
if development...
if incident...
if release...
if migration...
```

If workflows fundamentally differ, create separate subgraphs and reuse smaller components.

---

## 6. Reuse threshold

Create a dedicated reusable subgraph when at least one is true:

1. it is expected in two or more workflows;
2. it has independent retry/loop behavior;
3. it has a stable artifact contract;
4. it has its own execution/model policy;
5. it can be tested independently;
6. it has meaningful internal orchestration.

Do not create a subgraph only to avoid a 10-line node definition.

---

## 7. Recommended levels

```text
WORKFLOW
   ↓
REUSABLE SUBGRAPH
   ↓
NODE / SMALL SUBGRAPH
   ↓
AGENT / TOOL / ACTION
   ↓
SKILL
```

Example:

```text
Development Workflow
   ↓
Analysis Subgraph
   ↓
Impact Analysis Subgraph
   ↓
dependency-search capability
```

Nested subgraphs are valid when boundaries are meaningful.

---

## 8. Context independence

A reusable subgraph should receive only the context it requires.

It must not assume access to the full original conversation.

Artifacts should carry:

```text
references
evidence
scope
constraints
```

This keeps subgraphs isolated and reduces model-context cost.

---

## 9. Model independence

The subgraph should define logical execution profiles:

```text
cheap
standard
expert
deterministic
```

It should not hard-code a provider/model unless a capability truly requires it.

---

## 10. Project independence

Project-specific behavior comes from:

```text
Project Profile
Capabilities
Adapters
Tools
```

The reusable subgraph should not contain hard-coded:

```text
Python-only
ABAP-only
SAP-only
repository-specific
```

logic in its orchestration core.

---

## 11. Reusable failure contract

Recommended common outcome vocabulary where applicable:

```text
success
needs_context
needs_input
blocked
retryable_failure
failure
```

Not every subgraph needs every outcome.

The parent workflow maps outcomes to transitions.

---

## 12. Versioning

Reusable subgraphs and their artifact contracts should be versioned independently.

Example:

```yaml
subgraph:
  id: impact-analysis
  version: 1

contract:
  output: impact-result/v1
```

This allows workflow evolution without silently breaking callers.

---

## 13. Observability

Each reusable subgraph should expose:

```text
start/end
result
duration
iterations
model profile used
tools/capabilities used
artifact refs
warnings
```

This supports audit and optimizer capabilities.

---

## 14. Candidate reusable subgraph library

Current likely library:

```text
context
analysis
impact-analysis
testing
documentation
```

Strong future candidates:

```text
security-review
evidence-validation
risk-assessment
change-validation
release-validation
```

Potential but not yet proven reusable:

```text
planning
plan-review
code-review
final-validation
```

These should remain workflow nodes until their reuse requirements are demonstrated.

---

## 15. Avoid premature generalization

Do not turn every node into a generic subgraph.

Example:

```text
Implementation
```

may differ significantly between:

```text
feature development
migration
configuration update
documentation-only task
```

We should extract common reusable parts only after a stable shared contract is visible.

---

## 16. Current Development composition

Recommended structure:

```text
Development Workflow
│
├── Context Subgraph
│
├── Analysis Subgraph
│     └── Impact Analysis Subgraph
│
├── Planning Node
├── Plan Review Gate
├── Implementation Node
├── Code Review Gate
├── Testing Subgraph
├── Documentation Subgraph
├── Final Validation Gate
└── Complete Action
```

This gives reuse without turning the entire orchestrator into excessively fragmented micrographs.

---

## 17. Accepted decisions

1. Parent workflow owns routing.
2. Reusable subgraphs use stable artifact contracts.
3. Side effects are explicit.
4. Policy is configurable; workflow-specific behavior is not hidden inside generic subgraphs.
5. Nested subgraphs are allowed.
6. Reuse should be earned by stable boundaries, not created prematurely.
7. Context, Analysis, Impact Analysis, Testing, and Documentation are current primary reusable subgraphs.
