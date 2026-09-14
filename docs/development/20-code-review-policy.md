# Code Review Policy

**Status:** Accepted policy draft v0.1

## 1. v1 default

```yaml
code_review:
  enabled: true

  default_depth: standard

  max_review_cycles: 2

  delta_review: true

  independent_reviewer: true

  specialized_reviews:
    enabled: false
```

Code Review is mandatory for managed implementation work in v1.

---

## 2. Independent reviewer

The Code Reviewer must not be the implementation agent continuing in the same reasoning context.

At minimum:

```text
fresh reviewer context
independent role/skill
actual diff
Task/Plan/Analysis evidence
no implementation scratchpad
```

---

## 3. Review depth

### Light

Only when:

```text
small local diff
low risk
no public/data/security impact
```

### Standard

Default.

### Deep

Force for:

```text
security-sensitive changes
public API changes
data-model changes
transaction/concurrency changes
architecture changes
large cross-module diffs
critical business flows
migration changes
```

---

## 4. Approval policy

Approve when:

- no unresolved major/critical findings;
- implementation satisfies Task and approved Plan;
- material deviations are documented/approved;
- changed scope is justified;
- code is coherent enough to proceed to Testing;
- no known review-level blocker remains.

Info findings never block.

Minor findings block only when they affect correctness/maintainability materially according to project policy.

---

## 5. Routing policy

```text
code defect
→ Implementation

plan defect
→ Planning + Plan Review

analysis defect
→ Analysis

missing evidence
→ Context Expand

requirement ambiguity
→ User

hard blocker
→ Task Blocked
```

The Code Reviewer should not use Implementation as a universal dumping ground.

---

## 6. Review cycles

Default:

```yaml
max_review_cycles: 2
```

After two direct cycles, classify root cause and escalate.

Do not automatically start a third code-fix loop.

---

## 7. Delta review

Use when:

```text
Plan unchanged
Analysis unchanged
fix scope limited
previous findings known
```

Force full review when:

```text
large rewrite
scope expansion
new dependency
Plan changed
Analysis changed
public/data/security contract changed
```

---

## 8. Specialized reviews

Not enabled by default in v1.

Possible future conditional reviewers:

```text
security
performance
migration
architecture compliance
```

They should be invoked only by risk/policy.

Their findings should merge into the same Code Review result model.

---

## 9. Context efficiency

Reviewer receives:

```text
Task
Approved Plan
Implementation Analysis
Implementation Result
actual diff/changed objects
relevant Context refs
Project Profile constraints
previous findings
```

Do not automatically provide the full repository.

Use Context expansion when needed.

---

## 10. Anti-noise policy

Do not create findings for:

- formatting handled by formatter;
- purely subjective naming preferences;
- unrelated legacy debt;
- broad refactor suggestions outside task scope;
- hypothetical micro-optimizations with no evidence.

The reviewer should prioritize correctness, risk, scope, architecture, and maintainability that matters.

---

## 11. Accepted risk

Major/critical risks require:

```text
human decision
or
explicit project policy
```

The reviewer may not silently mark them accepted.

---

## 12. Testing boundary

Code Review may inspect tests and flag missing/incorrect test changes.

It does not replace actual test execution.

Approved Code Review always proceeds to Testing Subgraph.

---

## 13. Metrics

Track:

```text
first-pass approval rate
average cycles
finding categories
repeat finding rate
routing destinations
test failures after approved review
final-validation defects after approved review
review duration/cost
```

Particularly useful metric:

> What percentage of later Testing failures were predictable from the reviewed diff?

This helps tune Code Review quality.

---

## 14. Reuse

The same policy/contract is intended for:

```text
feature
bugfix
refactoring
migration
```

with project-specific risk configuration.

---

## 15. Accepted decisions

1. Code Review mandatory in v1.
2. Independent reviewer.
3. Maximum two direct review/fix cycles.
4. Risk-adaptive depth.
5. Delta review after bounded fixes.
6. Correct-owner routing.
7. No direct source modification by reviewer.
8. Specialized reviewers deferred.
9. Testing remains separate.
