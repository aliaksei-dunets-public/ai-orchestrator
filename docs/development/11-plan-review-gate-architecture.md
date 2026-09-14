# Plan Review Gate — Detailed Architecture

**Status:** Accepted design v0.2  
**Scope:** Development Workflow — independent review of Implementation Plan

## 1. Why Plan Review is a critical gate

Plan Review is a high-leverage stage because errors here multiply downstream.

A weak plan may lead to:

- unnecessary code changes;
- architecture drift;
- missing edge cases;
- incomplete tests;
- wrong implementation order;
- missed compatibility constraints;
- excessive implementation/review loops;
- wasted model/tool cost.

The purpose of Plan Review is therefore not to "make the plan nicer".

It is to answer:

> Is this plan sufficiently correct, safe, complete, scoped, and executable to authorize implementation?

---

## 2. Plan Review remains independent from Planning

Planning creates the plan.

Plan Review evaluates it independently.

```text
PLANNING
   ↓
PLAN ARTIFACT
   ↓
PLAN REVIEW
   ├── approved
   ├── changes_required
   ├── reanalysis_required
   ├── more_context_required
   ├── user_input_required
   └── blocked
```

The reviewer must not receive the Planning agent's hidden reasoning or scratchpad.

It receives evidence artifacts:

```text
Task Artifact
Development Specification
Implementation Plan
Project Profile
optional previous review history
```

This prevents self-confirmation bias.

---

## 3. Review is a Gate, not a second Planner

The reviewer should not silently rewrite the plan.

Its job is to:

1. detect problems;
2. classify them;
3. provide actionable evidence-backed feedback;
4. route the workflow correctly.

The Planning subgraph owns plan revision.

Bad behavior:

```text
reviewer finds issue
→ reviewer rewrites whole plan
→ implementation receives unreviewed replacement
```

Correct behavior:

```text
reviewer finds issue
→ changes_required
→ Planning creates PLAN-v2
→ Plan Review evaluates PLAN-v2
```

---

## 4. High-level review flow

```text
PLAN REVIEW REQUEST
      │
      ▼
1. VALIDATE REVIEW INPUTS
      │
      ▼
2. DETERMINE REVIEW DEPTH
      │
      ▼
3. CHECK TASK ALIGNMENT
      │
      ▼
4. CHECK ANALYSIS ALIGNMENT
      │
      ▼
5. CHECK SCOPE / MINIMALITY
      │
      ▼
6. CHECK TECHNICAL COHERENCE
      │
      ▼
7. CHECK DEPENDENCY / ORDERING
      │
      ▼
8. CHECK RISK / COMPATIBILITY
      │
      ▼
9. CHECK VALIDATION / TESTABILITY
      │
      ▼
10. CHECK IMPLEMENTABILITY
      │
      ▼
11. CLASSIFY FINDINGS
      │
      ▼
12. DECIDE OUTCOME / ROUTE
      │
      ▼
PLAN REVIEW RESULT
```

Not every stage requires a separate LLM call. These are logical checks inside the gate.

---

## 5. Review depth

The review depth should be risk-adaptive.

```yaml
review_depth:
  enum:
    - light
    - standard
    - deep
```

### Light

Suitable for:

- small local changes;
- low risk;
- no public contract changes;
- no data model changes;
- no migration;
- no cross-module impact.

### Standard

Default.

### Deep

Required when one or more apply:

- public API changes;
- schema/data migration;
- security-sensitive change;
- architecture change;
- critical business flow;
- cross-module/high fan-out impact;
- irreversible operation;
- high-risk integration;
- explicit project policy.

The runtime may derive review depth from:

```text
Task risk
Analysis risks
Planning depth
Project policy
Affected contracts
```

---

## 6. Review dimension 1 — Task alignment

Questions:

- Does the plan actually solve the Task objective?
- Are acceptance criteria represented?
- Is any required outcome missing?
- Has the plan drifted into unrelated improvements?
- Is the plan solving a different problem than requested?

Typical findings:

```text
missing_acceptance_criterion
scope_drift
unnecessary_work
objective_mismatch
```

---

## 7. Review dimension 2 — Specification alignment and coverage

Questions:

- Does every material Specification requirement have Plan coverage?
- Are business rules/validations/invariants preserved?
- Does the Plan respect scope/non-goals?
- Are affected contracts/dependencies from the Specification addressed?
- Are critical global constraints copied into the Plan?
- Does the Plan contradict any evidence-backed Specification statement?

The reviewer should maintain a lightweight coverage view:

```text
Specification requirement → Plan work unit / validation
```

If the Plan is wrong but the Specification is sound:

```text
changes_required → Planning
```

If the Specification itself is incomplete/incorrect:

```text
specification_revision_required → Preparation
```

Do not patch missing requirements directly inside Plan Review.

---

## 8. Review dimension 3 — Scope and minimality

The reviewer should actively protect against unnecessary changes.

Questions:

- Is every step necessary?
- Can the task be solved with a smaller change surface?
- Does the plan introduce premature abstractions?
- Does it refactor unrelated code?
- Does it create new infrastructure without need?

The goal is:

> smallest coherent change that satisfies the task and project constraints.

This is particularly important for AI coding agents, which often over-expand scope.

---

## 9. Review dimension 4 — Technical coherence

Questions:

- Do the proposed steps fit the project's architecture?
- Are abstractions placed in correct layers/components?
- Does the plan reuse existing capabilities instead of duplicating them?
- Are project conventions followed?
- Are state/data flows coherent?
- Are error handling and lifecycle concerns accounted for?
- Does the plan create circular dependencies or architectural leakage?

The reviewer should use Project Profile + Context evidence, not generic best practices alone.

---

## 10. Review dimension 5 — Dependency and ordering correctness

Checks:

- step dependencies exist;
- no cycles;
- prerequisites come first;
- migrations precede dependent usage;
- public contract changes are coordinated with consumers;
- tests/docs/compatibility steps are ordered sensibly;
- parallel steps are truly independent.

This can be partially deterministic.

---

## 10A. Review dimension — File/Object structure and interfaces

Questions:

- Are concrete files/objects identified where they are knowable during Planning?
- Do object responsibilities match existing project architecture?
- Are new files/objects justified rather than speculative restructuring?
- Do work-unit `consumes` / `produces` interfaces agree?
- Are tests located with the project's established conventions?

This check adopts the useful planning discipline from Superpowers without requiring its multi-agent execution model.

---

## 11. Review dimension 6 — Risk and compatibility

Check identified risk surfaces:

```text
backward compatibility
security
data integrity
transactionality
performance
concurrency
migration
deployment
external integrations
rollback/reversibility
```

Not every plan needs every category.

The reviewer should check only relevant dimensions.

---

## 12. Review dimension 7 — Validation and testability

Questions:

- Can each important step be verified?
- Does the plan define adequate validation?
- Are regressions likely to be caught?
- Are tests aligned with acceptance criteria?
- Are integration/E2E tests needed?
- Is a migration verification step missing?
- Are negative/error-path tests needed?

Plan Review does not execute tests.

It verifies that the plan is testable.

---

## 13. Review dimension 8 — Implementability

Questions:

- Is every work unit sufficiently concrete?
- Does the plan depend on unknown or unavailable information?
- Does it require capabilities/tools not available?
- Are steps too broad to execute reliably?
- Are steps too microscopic to be useful?
- Are outputs/checkpoints understandable?

A plan can be architecturally correct but still not executable by an agent.

---

## 14. Findings taxonomy

Every finding should be classified.

Recommended categories:

```text
task_alignment
scope
analysis_alignment
architecture
dependency
compatibility
security
data_integrity
performance
testing
documentation
implementability
missing_context
missing_requirement
risk
other
```

Recommended severity:

```text
info
minor
major
critical
```

Interpretation:

### Info

Optional improvement. Does not block approval.

### Minor

Small issue that may be safely fixed during plan revision without changing the main approach.

### Major

Material problem. Plan should not proceed unchanged.

### Critical

Plan is unsafe or fundamentally incorrect.

---

## 15. Blocking semantics

Do not equate every finding with `changes_required`.

Recommended rules:

```text
info only
→ approved

minor findings only
→ approved_with_notes OR changes_required by policy

major finding
→ changes_required / reanalysis / more_context

critical finding
→ blocked / reanalysis / user input depending on cause
```

For first version, simplest supported outcomes can remain:

```text
approved
changes_required
reanalysis_required
more_context_required
user_input_required
blocked
failure
```

`approved_with_notes` can be deferred unless needed.

---

## 16. Correct routing is more important than rejection

A major source of loops is sending every issue back to Planning.

The reviewer must classify **where the defect originated**.

### Planning defect

Examples:

- wrong step ordering;
- missing test step;
- unnecessary abstraction;
- ignored constraint.

Route:

```text
changes_required → Planning
```

### Analysis defect

Examples:

- wrong change surface;
- missed dependency;
- incomplete impact assessment.

Route:

```text
reanalysis_required → Analysis
```

### Context defect

Examples:

- reviewer cannot verify architecture assumption;
- relevant API consumer information missing.

Route:

```text
more_context_required → Context Expand
```

### Requirement defect

Examples:

- acceptance criteria ambiguous;
- backward compatibility decision not specified.

Route:

```text
user_input_required → Ask User
```

### True blocker

Route:

```text
blocked → Task Blocked
```

This routing is one of the most important mechanisms for avoiding endless Plan ↔ Review loops.

---

## 17. Review feedback must be actionable

Bad feedback:

```text
Plan is incomplete.
Architecture could be better.
Consider more tests.
```

Required finding format:

```yaml
finding:
  id: PRF-01
  category: architecture
  severity: major

  summary: >
    The plan places platform-specific health checks in the universal core.

  evidence:
    - analysis constraint: platform agnostic
    - PLAN STEP-02

  impact: >
    This couples the orchestrator core to target platforms
    and reduces reuse.

  required_change: >
    Keep orchestration universal and move target-specific checks
    behind the adapter/capability boundary.

  route: planning
```

The reviewer should explain **what is wrong, why it matters, and what property must change**.

It should not prescribe unnecessary line-level implementation.

---

## 18. Evidence discipline

Each blocking finding should reference at least one of:

```text
Task acceptance criterion
Analysis constraint/risk
Context evidence
Project Profile rule
Plan step
Architecture/project documentation
```

Avoid generic "best practice" objections unless the project has no relevant local guidance and the issue is objectively material.

---

## 19. Review independence

Recommended execution isolation:

```text
Planning Agent
    ≠
Plan Review Agent
```

At minimum:

- fresh sub-agent context;
- no planner scratchpad;
- independent system/skill instruction;
- evidence artifacts only.

For high-risk plans, a stronger model profile may be used.

---

## 20. Review loops

The loop must be bounded.

Candidate default:

```yaml
plan_review:
  max_review_cycles: 2
```

Example:

```text
PLAN v1
  ↓
Review 1 → changes_required
  ↓
PLAN v2
  ↓
Review 2
```

If Review 2 still finds major problems:

```text
do NOT blindly start cycle 3
```

Route based on root cause:

```text
analysis issue → Analysis
requirement issue → Ask User
context issue → Context Expand
persistent planning failure → Escalation / human gate / blocked
```

This matches the earlier orchestrator principle of avoiding unlimited review loops.

---

## 21. Delta review for revised plans

Reviewing PLAN-v2 should not always repeat the entire review from scratch.

Use:

```text
previous approved/criticized plan
+
review findings
+
plan revision diff
```

Review modes:

### Full review

Required when:

- main strategy changed;
- scope changed materially;
- Analysis changed;
- major new dependencies introduced;
- high-risk plan.

### Delta review

Suitable when:

- revision only addresses known findings;
- overall strategy remains unchanged.

Delta review checks:

1. were prior findings resolved?
2. did the revision introduce regressions?
3. did affected dependencies change?

This reduces cost and review latency.

---

## 22. Review state / finding lifecycle

Findings should have lifecycle:

```text
open
resolved
accepted_risk
obsolete
```

When PLAN-v2 is reviewed:

```yaml
finding_resolution:
  finding_ref: PRF-01
  status: resolved
  evidence:
    - PLAN-v2 STEP-03
```

This prevents the reviewer from repeatedly raising the same issue with slightly different wording.

---

## 23. Accepted risk

Some findings may be intentionally accepted.

Candidate mechanism:

```yaml
accepted_risk:
  finding_ref: PRF-03
  decision_by: human | policy
  rationale: >
    Backward compatibility is intentionally not required for this internal API.
```

AI alone should not silently accept high/critical risk unless project policy explicitly permits it.

---

## 24. Optional specialized reviewers

Do not start with multiple reviewers for every plan.

Default:

```text
one independent Plan Reviewer
```

For high-risk plans, the gate may invoke specialized reusable checks:

```text
Security Review
Migration Review
Data Integrity Review
Architecture Compliance
```

Conceptually:

```text
PLAN REVIEW
      │
      ├── core review
      ├── security check?       conditional
      ├── migration check?      conditional
      └── architecture check?   conditional
```

These are future reusable subgraphs/gates.

The core Plan Review aggregates their findings.

This is preferable to always running 4 expensive agents.

---

## 25. Review depth selection policy

Example:

```yaml
review_policy:
  default: standard

  deep_if:
    - task.risk == high
    - plan.depth == complex
    - public_api_change == true
    - data_model_change == true
    - migration == true
    - security_sensitive == true
```

Light review should never be used merely to save tokens if task risk is high.

---

## 26. Plan Review output

The output must contain:

```text
result
review depth
summary
findings
resolved previous findings
unresolved findings
routing reason
reviewed plan version
evidence refs
```

It should be short enough to feed directly back into Planning.

---

## 27. What Plan Review must NOT do

The gate must not:

- implement code;
- rewrite the entire plan;
- silently expand task scope;
- repeat Context Discovery from scratch unless needed;
- invent requirements;
- approve because "the plan looks reasonable";
- reject on style preferences alone;
- create endless loops;
- inspect planner chain-of-thought.

---

## 28. Observability

Record:

```text
plan version
review cycle
review depth
outcome
finding count by severity/category
model profile
duration
specialized checks invoked
previous finding resolution rate
```

Useful metrics:

```text
plans approved first pass
average review cycles
reanalysis rate
context-expansion rate
false-positive/repeated finding rate
implementation failures after approved plan
```

These metrics reveal whether Plan Review is actually improving downstream execution.

---

## 29. Model policy

Recommended:

| Review type | Model profile |
|---|---|
| Light | standard |
| Standard | expert |
| Deep | expert |
| Deterministic dependency/schema checks | no LLM |
| Delta review | standard/expert based on risk |

Plan Review is one of the stages where using a stronger model is usually justified.

---

## 30. Accepted decisions

1. Plan Review is an independent gate.
2. It does not rewrite plans.
3. Review is risk-adaptive.
4. The reviewer checks eight explicit dimensions.
5. Findings are categorized, severity-rated, evidence-backed, and actionable.
6. Routing identifies whether the defect belongs to Planning, Analysis, Context, requirement/user input, or true blocker.
7. Review loops are bounded.
8. Revised plans support delta review.
9. Findings have lifecycle to prevent repeated feedback.
10. Specialized reviewers are conditional, not always-on.
11. Review quality is measured with downstream metrics.


---

## 31. Zero-conversation executability

Before approval, ask:

> Could a fresh executor implement this Task using only Task + current Specification + current Plan + Project Profile?

Blocking symptoms:

```text
"as discussed earlier"
missing file/object targets that are discoverable during planning
critical constraint available only in raw Analysis
implicit interface contracts
validation omitted for meaningful behavior
```

A Plan that relies on preparation conversation history is not `ready`.
