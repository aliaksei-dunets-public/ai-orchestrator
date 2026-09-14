# Superpowers Principles Adopted by AI Orchestrator

**Status:** Accepted reference v0.1  
**Reference project:** `obra/superpowers` (reviewed against current 2026 workflow/skills)

## 1. Purpose

Superpowers is used as a design reference, not as a runtime dependency.

The Orchestrator adopts selected process principles while preserving its own goals:

```text
platform agnostic
single implementation agent in v1
project-profile driven
optional TDD
artifact-based handoff
Task Manager / async execution support
```

---

## 2. Superpowers pattern: design/spec before plan

Current Superpowers brainstorming flow explores project context, clarifies intent, evaluates approaches, writes a design/spec document, reviews it, and only then invokes `writing-plans`.

Adopted Orchestrator equivalent:

```text
Context
→ Analysis / Impact
→ Development Specification
→ Specification Sufficiency
→ Planning
```

The durable Specification is separate from the implementation Plan.

---

## 3. Superpowers pattern: zero-context plan consumer

Superpowers `writing-plans` explicitly assumes the implementer has little/no codebase or problem-domain context.

Adopted principle:

> An executor must be able to begin from Task + Specification + Approved Plan without preparation conversation history.

The Orchestrator does not pass raw chat history or planner scratchpad across the durable `ready` boundary.

---

## 4. Superpowers pattern: scope check

Current Superpowers checks whether a specification spans multiple independent subsystems before writing one oversized plan.

Adopted principle:

```text
Before detailed planning:
  detect task/spec scope that cannot form one coherent executable plan.
```

For v1, this is a Planning/Plan Review warning and does not automatically split the Task.

If independent work truly requires separate managed Tasks, explicit task decomposition may be introduced later.

---

## 5. Superpowers pattern: file structure before tasks

Current Superpowers plans map file responsibilities before detailed implementation tasks.

Adopted principle:

The Implementation Plan contains a `File / Object Structure` section before work units.

It identifies:

```text
files/objects to create
files/objects to modify
responsibilities
important symbols/interfaces
expected test locations
```

For non-file platforms (for example SAP/ABAP), the same concept maps to project objects:

```text
classes
interfaces
CDS entities
behavior definitions
service definitions
UI artifacts
configuration objects
```

---

## 6. Superpowers pattern: global constraints reach the executor

Current Superpowers copies project-wide constraints from the spec into the plan so downstream implementers cannot accidentally lose them.

Adopted principle:

The Plan carries an explicit `Global Constraints` section derived from the Specification.

This is deliberate duplication of critical execution constraints, not uncontrolled duplication of the whole Specification.

---

## 7. Superpowers pattern: explicit interfaces between work units

Current Superpowers plans document what tasks consume and produce so independently executed units share stable contracts.

Adopted principle for v1 single-agent execution:

Each meaningful work unit may define:

```text
Consumes
Produces
Depends On
```

This improves sequencing and future-proofs the Plan for later segmented execution without requiring multi-agent implementation now.

---

## 8. Superpowers pattern: concrete implementation targets

Adopted strongly.

A Plan should prefer:

```text
exact file/object path
symbol/object name where known
what changes
expected result
verification command/check
```

over vague instructions such as:

```text
Update payment logic.
```

The plan should be precise enough to execute but should not become line-by-line code generation before Implementation.

---

## 9. Superpowers pattern: verification is part of the plan

Adopted.

Every meaningful implementation work unit defines expected validation.

Examples:

```text
unit test
component/integration test
contract check
build/static check
manual acceptance behavior
```

Actual authoritative execution remains owned by Implementation local validation and the Testing Subgraph.

---

## 10. Superpowers pattern: spec/review gates

Adopted with adaptation.

Superpowers explicitly reviews/approves the written spec and later reviews implementation work.

Orchestrator uses:

```text
Specification Sufficiency Check
+ optional/risk-driven user confirmation
+ independent Plan Review
+ independent Code Review
+ Testing
+ User Acceptance
```

We avoid adding a universal extra human gate for every specification.

---

## 11. Deliberate differences

The Orchestrator does **not** copy these Superpowers choices literally in v1:

```text
mandatory fresh subagent per implementation task
mandatory TDD for every code change
mandatory micro-task commit cadence
mandatory worktree usage in core graph
human approval of every specification regardless of risk
```

Reasons:

```text
single-agent v1 implementation policy
support for ABAP/config/migration/docs/non-code work
platform independence
project-specific tooling differences
avoid unnecessary process overhead
```

TDD remains `auto`/policy-driven in the Orchestrator.

---

## 12. Orchestrator preparation pipeline after adoption

```text
Task = preparing
      ↓
Context
      ↓
Analysis / Impact
      ↓
Development Specification
      ↓
Specification Sufficiency Check
      ↓
Planning
  ├── Scope Check
  ├── File/Object Structure
  ├── Global Constraints
  ├── Work Units + Interfaces
  └── Validation per Unit
      ↓
Plan Review
  ├── Specification coverage
  ├── scope/minimality
  ├── architecture
  ├── dependency/order
  ├── validation/testability
  └── zero-context executability
      ↓ approved
Task = ready
```

---

## 13. References reviewed

- https://github.com/obra/superpowers
- https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
- https://github.com/obra/superpowers/blob/main/skills/writing-plans/SKILL.md
- https://github.com/obra/superpowers/blob/main/skills/executing-plans/SKILL.md
- https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md

---

## 14. Accepted decisions

1. Adopt Spec → Plan → Execute as a durable boundary.
2. Executor is zero-conversation-context by design.
3. Specification and Plan are separate durable documents.
4. Add Planning Scope Check and File/Object Structure.
5. Copy critical global constraints from Spec into Plan.
6. Add explicit consumes/produces interfaces to meaningful plan work units.
7. Strengthen Plan Review with specification coverage and executability checks.
8. Do not copy Superpowers multi-agent/TDD/worktree policies literally.
