# Code Review Gate — Detailed Architecture

**Status:** Accepted design draft v0.1  
**Scope:** Development Workflow — independent review of the actual implementation

## 1. Purpose

`Code Review` evaluates the implementation that actually exists in the project after the Implementation stage.

Its main question is:

> Does the produced code correctly implement the approved Task and Plan, respect project constraints, and remain safe enough to proceed to full Testing?

Code Review is not a second Planning stage and is not a replacement for Testing.

It is an independent quality gate over the real diff / workspace.

---

## 2. Difference from Plan Review

### Plan Review

Reviews intended work:

```text
Task
Analysis
Plan
```

Question:

> Is this a good implementation plan?

### Code Review

Reviews actual work:

```text
Task
Approved Plan
Implementation Result
Actual Diff / Changed Objects
Relevant Project Context
```

Question:

> Did the implementation correctly realize the approved plan and task?

The two gates protect different failure classes.

---

## 3. Independence

The Code Reviewer should be independent from the Implementation agent.

Recommended isolation:

```text
Implementation Agent
        ≠
Code Review Agent
```

The reviewer receives:

- Task Artifact;
- Approved Plan;
- Implementation Analysis;
- Implementation Result;
- actual project diff / changed objects;
- relevant Context refs;
- Project Profile;
- optional previous Code Review findings.

The reviewer should **not** receive the implementer's hidden reasoning or scratchpad.

---

## 4. High-level flow

```text
CODE REVIEW REQUEST
      │
      ▼
1. VALIDATE REVIEW INPUTS
      │
      ▼
2. DETERMINE REVIEW DEPTH
      │
      ▼
3. CHECK TASK / PLAN CONFORMANCE
      │
      ▼
4. CHECK DIFF SCOPE
      │
      ▼
5. CHECK CORRECTNESS
      │
      ▼
6. CHECK ARCHITECTURE / PROJECT RULES
      │
      ▼
7. CHECK API / DATA / COMPATIBILITY
      │
      ▼
8. CHECK ERROR / EDGE CASE HANDLING
      │
      ▼
9. CHECK MAINTAINABILITY / DUPLICATION
      │
      ▼
10. CHECK TEST CHANGES / TESTABILITY
      │
      ▼
11. CHECK SECURITY / PERFORMANCE SIGNALS
      │
      ▼
12. CLASSIFY FINDINGS
      │
      ▼
13. DECIDE ROUTE
      │
      ▼
CODE REVIEW RESULT
```

These are logical review dimensions. They do not require separate LLM calls in v1.

---

## 5. Review depth

```yaml
review_depth:
  enum:
    - light
    - standard
    - deep
```

### Light

Suitable for:

- very small local implementation;
- low-risk change;
- narrow diff;
- no public contract/data/security impact.

### Standard

Default.

### Deep

Required when:

- public API changed;
- data model changed;
- security-sensitive area touched;
- transaction/concurrency behavior changed;
- architecture changed;
- critical business flow changed;
- diff is large or cross-module;
- Plan Review classified task as high risk;
- project policy requires deep review.

---

## 6. Dimension 1 — Task and Plan conformance

Questions:

- Does the implementation satisfy the original Task objective?
- Are acceptance criteria represented in the actual change?
- Were approved Plan steps completed?
- Did implementation silently omit a required step?
- Did it implement something not approved?
- Were material plan deviations recorded?

Typical findings:

```text
missing_required_change
unapproved_scope_expansion
incomplete_plan_step
acceptance_criterion_not_implemented
undocumented_plan_deviation
```

---

## 7. Dimension 2 — Diff scope

The reviewer should inspect the actual change surface.

Questions:

- Are changed files/objects expected?
- Are there unrelated modifications?
- Did generated/vendor/unrelated areas change unexpectedly?
- Is the diff larger than necessary?
- Did implementation modify sensitive files not declared in the plan?

This protects against AI agents over-editing the project.

---

## 8. Dimension 3 — Correctness

Check actual logic for:

- incorrect conditions;
- wrong state transitions;
- missing branches;
- off-by-one/boundary errors;
- null/empty handling;
- incorrect data transformation;
- lifecycle mistakes;
- exception/error propagation;
- resource handling;
- transactional correctness where relevant.

Review should rely on project context and evidence, not generic style critique.

---

## 9. Dimension 4 — Architecture and project rules

Questions:

- Does code respect project layering?
- Are existing abstractions reused?
- Was duplicate capability introduced?
- Are naming/conventions respected?
- Is platform-specific logic isolated correctly?
- Are Clean Core / framework rules respected when configured?
- Has implementation introduced undesirable coupling?

Findings must point to concrete changed code and project constraints.

---

## 10. Dimension 5 — API / data / compatibility

Conditional review dimensions:

```text
public API compatibility
schema/data compatibility
serialization
versioning
migration compatibility
backward compatibility
external integration contract
```

Only run deeply when relevant.

Examples:

```text
new mandatory API field
changed OData exposure
database field semantic change
event contract change
```

---

## 11. Dimension 6 — Error and edge-case handling

Questions:

- Are known failure paths handled?
- Are Analysis risks reflected?
- Are invalid inputs handled?
- Are partial failures safe?
- Is retry behavior correct?
- Are transaction rollback semantics preserved?
- Are edge cases from Task/Analysis ignored?

This is not exhaustive Testing, but code-level risk review.

---

## 12. Dimension 7 — Maintainability / duplication

Review should identify only material issues:

```text
duplicated project capability
unnecessary abstraction
over-complex code
large hidden side effect
dead code introduced
misplaced responsibility
```

Avoid subjective style comments where formatter/linter/project conventions already cover them.

Code Review is not a style-opinion generator.

---

## 13. Dimension 8 — Tests and testability

Questions:

- Did implementation add/update tests where the Plan expected them?
- Are existing tests invalidated?
- Is the changed design testable?
- Are important error paths testable?
- Did code introduce hidden hard-to-test coupling?
- Are mocks/stubs used consistently with project patterns?

The reviewer does not execute the final test suite.

Testing Subgraph remains the next stage.

---

## 14. Dimension 9 — Security / performance signals

Core Code Review performs only first-line checks.

Examples:

```text
unsafe input handling
authorization bypass
secret leakage
unsafe dynamic execution
obvious N+1/query explosion
unbounded loop
obvious resource leak
```

For high-risk tasks, specialized Security/Performance Review can be invoked conditionally in the future.

The core reviewer should not pretend to replace a dedicated security audit.

---

## 15. Finding taxonomy

Recommended categories:

```text
task_conformance
plan_conformance
scope
correctness
architecture
dependency
api_compatibility
data_integrity
transactionality
security
performance
error_handling
testing
maintainability
documentation
missing_context
missing_requirement
other
```

Severity:

```text
info
minor
major
critical
```

---

## 16. Finding ownership / routing

Correct routing is essential.

### Implementation defect

Examples:

- wrong logic;
- missing test;
- duplication;
- unapproved change;
- missed Plan step.

Route:

```text
changes_required → Implementation
```

### Plan defect

Examples:

- implementation revealed the approved strategy is impossible;
- required architecture change was absent from Plan;
- necessary migration was omitted.

Route:

```text
replanning_required → Planning
```

Then Plan Review must re-approve.

### Analysis defect

Examples:

- missed impact surface;
- hidden dependency discovered;
- original Analysis assumption was incorrect.

Route:

```text
reanalysis_required → Analysis
```

### Context defect

Examples:

- reviewer cannot verify contract behavior;
- relevant dependency evidence missing.

Route:

```text
more_context_required → Context Expand
```

### Requirement defect

Route:

```text
user_input_required → Ask User
```

### True blocker

Route:

```text
blocked → Task Blocked
```

Do not send every issue back to Implementation.

---

## 17. Review feedback

Feedback must be actionable.

Bad:

```text
This code could be cleaner.
```

Preferred:

```yaml
finding:
  category: correctness
  severity: major

  location:
    file: src/payment/service.py
    symbol: PaymentService.cancel

  summary: >
    The implementation updates payment state before transaction
    validation completes.

  evidence:
    - ANALYSIS-0042 invariant: validation before state mutation
    - changed symbol: PaymentService.cancel

  impact: >
    A validation failure can leave an invalid intermediate state.

  required_change: >
    Preserve the existing validation-before-mutation invariant.

  suggested_route: implementation
```

The reviewer should specify what property must be corrected, not produce a full replacement implementation.

---

## 18. Evidence discipline

Every major/critical finding should reference:

- changed file/object/symbol;
- Task/Plan/Analysis constraint where applicable;
- relevant Context/project rule;
- concrete behavior.

Avoid blocking based solely on generic personal preference.

---

## 19. Review loop

Candidate default:

```yaml
code_review:
  max_review_cycles: 2
```

Flow:

```text
Implementation v1
      ↓
Code Review 1
      ↓ changes_required
Implementation v2
      ↓
Code Review 2
```

If major findings remain after cycle 2, do not blindly repeat.

Reclassify root cause:

```text
implementation issue → escalation / human gate / blocked
plan issue → Planning
analysis issue → Analysis
context issue → Context
requirement issue → User
```

---

## 20. Delta review

After Implementation fixes review findings, use a delta-aware review when safe.

Inputs:

```text
previous review
previous diff
new diff
open findings
```

Delta review checks:

1. were previous findings resolved?
2. did fixes introduce regressions?
3. did changed scope expand?
4. did new dependencies/contracts appear?

Force full Code Review when:

- implementation changed strategy materially;
- large new code area changed;
- Planning/Analysis changed;
- public/data/security contract changed;
- previous critical finding required broad rewrite.

---

## 21. Finding lifecycle

```text
open
resolved
accepted_risk
obsolete
```

Persistent logical finding IDs prevent repeated critique under different wording.

Example:

```yaml
finding_resolution:
  finding_ref: CRF-01
  status: resolved
  evidence:
    - src/payment/service.py:PaymentService.cancel
```

---

## 22. Accepted risk

Some findings may be intentionally accepted.

Only policy/human authorization should accept major/critical risk by default.

Example:

```yaml
accepted_risk:
  finding_ref: CRF-03
  decision_by: human
  rationale: >
    Temporary compatibility shim is intentionally omitted
    for this internal-only API.
```

---

## 23. Context expansion

Code Reviewer may request additional context.

It should not independently load the entire project.

Example:

```yaml
result: more_context_required

context_request:
  mode: expand
  need:
    - callers of PaymentService.cancel
    - transaction contract for cancellation
```

This keeps review focused and auditable.

---

## 24. Specialized future reviews

Future conditional reusable checks may include:

```text
Security Review
Performance Review
Migration Review
Architecture Compliance Review
```

Do not make them always-on in v1.

Core Code Review should remain one strong independent reviewer.

---

## 25. What Code Review must NOT do

It must not:

- rewrite the implementation directly;
- change project files;
- become a second implementation agent;
- repeat all Testing;
- review unrelated legacy code unless directly relevant;
- generate stylistic noise;
- silently change Task scope;
- rely on implementer scratchpad;
- create unlimited implementation-review loops.

---

## 26. Handoff to Testing

On approval:

```text
Task
Approved Plan
Implementation Result
Code Review Result
Actual Workspace / Diff
      ↓
Testing Subgraph
```

Code Review approval means:

> No known review-level issue blocks test execution.

It does **not** mean the implementation is complete until Testing and later Final Validation pass.

---

## 27. Observability

Track:

```text
review depth
cycle count
findings by severity/category
resolution rate
route destinations
repeat finding rate
model profile
review duration
diff size
```

Important downstream metrics:

```text
test failures that Code Review should have caught
final-validation failures caused by implementation defects
production/incident defects traceable to missed review
```

These metrics should drive future tuning.

---

## 28. Model policy

Recommended:

| Review mode | Model |
|---|---|
| Light | standard |
| Standard | expert |
| Deep | expert |
| deterministic diff/schema checks | no LLM |
| delta review | standard/expert by risk |

Code Review is a justified strong-model stage.

---

## 29. Reuse

The same Code Review gate contract can be reused for:

```text
feature implementation
bugfix
refactoring
migration
configuration/code changes
```

via project/intent policy.

The gate should remain caller-independent and return structured outcomes.

---

## 30. Accepted decisions

1. Code Review is an independent gate over the actual implementation.
2. Reviewer receives evidence artifacts and diff/workspace, not implementer reasoning.
3. Review uses risk-adaptive depth.
4. Findings are structured, evidence-backed, severity-rated, and routed to the correct owner.
5. Maximum two direct Implementation↔Code Review cycles in v1.
6. Delta review is supported.
7. Review does not modify code itself.
8. Testing remains a separate authoritative downstream stage.
9. Specialized reviews are conditional future extensions.
10. Code Review is reusable across implementation-style workflows.
