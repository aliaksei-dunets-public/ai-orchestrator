# Plan Review Policy

**Status:** Accepted policy draft v0.1

## 1. Objective

Minimize bad implementation plans while avoiding review deadlocks, excessive token cost, and repeated low-value critique.

---

## 2. Default policy

```yaml
plan_review:
  enabled: true

  default_depth: standard

  max_review_cycles: 2

  delta_review: true

  independent_reviewer: true
```

---

## 3. Mandatory review

Plan Review should normally be mandatory for managed Development work.

A project may later define a bypass for genuinely trivial tasks, but bypass should be explicit policy rather than an implicit model decision.

Candidate future option:

```yaml
plan_review:
  bypass_for:
    risk: low
    planning_depth: simple
```

For initial orchestrator version, recommendation:

```text
always review managed implementation plans
```

This keeps behavior predictable while the system matures.

---

## 4. Review depth selection

```text
simple + low risk
→ light/standard

standard task
→ standard

complex/high risk
→ deep
```

Force deep review for:

```text
security-sensitive changes
data migration
public API breaking change
architecture changes
high-value transaction flow
irreversible operations
```

---

## 5. Approval rules

Approve when:

- no major/critical findings remain;
- task objective/acceptance criteria are represented;
- Analysis constraints are respected;
- work units are executable;
- meaningful validation exists;
- no unresolved blocker is hidden.

Info findings do not block.

Minor findings may block according to project policy.

Recommended v1 behavior:

```text
minor-only findings
→ changes_required only if they affect implementation correctness
→ otherwise approved with findings recorded
```

---

## 6. Routing policy

Use root cause, not symptom.

```text
plan structure/strategy problem
→ Planning

incorrect/incomplete technical understanding
→ Analysis

insufficient evidence
→ Context Expand

requirement ambiguity
→ User

hard external/constraint blocker
→ Blocked
```

Avoid routing everything to Planning.

---

## 7. Review cycle policy

Default:

```text
maximum 2 Planning↔Plan Review cycles
```

After cycle exhaustion:

```text
classify unresolved problem
      │
      ├── context → expand
      ├── analysis → reanalyse
      ├── requirement → user
      ├── reviewer uncertainty → expert escalation
      └── persistent contradiction → blocked/human gate
```

No automatic third planning cycle.

---

## 8. Escalation policy

Escalate reviewer model when:

- major findings conflict with planner position;
- architecture constraints are ambiguous;
- review cycle 2 remains unresolved;
- security/data-integrity risk is high;
- reviewer confidence is low on a blocking issue.

Example:

```yaml
execution:
  primary_profile: expert
  escalation_profile: expert
```

Depending on model catalog, Plan Review may already use the strongest standard reviewer.

---

## 9. Delta review policy

Use Delta Review only when:

```text
Analysis unchanged
Context materially unchanged
main strategy unchanged
scope unchanged
revision addresses known findings
```

Force Full Review when:

```text
strategy changed
scope expanded
Analysis changed
new high-risk dependency introduced
public contract changed
```

---

## 10. Repeated finding policy

A finding with the same underlying issue should keep the same logical ID across plan revisions.

Do not generate:

```text
PRF-01 API compatibility
PRF-07 compatibility concern
PRF-12 preserve consumers
```

for the same unresolved defect.

This enables measurable resolution.

---

## 11. Specialized review triggers

Candidate conditional checks:

```yaml
specialized_reviews:

  security:
    when:
      - security_sensitive == true

  migration:
    when:
      - data_migration == true

  architecture:
    when:
      - architecture_change == true

  compatibility:
    when:
      - public_contract_change == true
```

These may later become reusable subgraphs.

Their findings are aggregated into the core Plan Review result.

---

## 12. Human gate

A human gate is optional, not default.

Recommended triggers:

```text
critical unresolved finding
business/requirement decision
irreversible high-impact migration
explicit project policy
review cycles exhausted with conflicting expert opinions
```

The orchestrator should not request human approval for routine implementation plans.

---

## 13. Token / context efficiency

Reviewer receives:

```text
Task
Implementation Analysis
Plan
relevant Context refs
Project Profile constraints
previous findings
```

Do not automatically send:

```text
entire repository
full original conversation
planner scratchpad
all raw Context content
```

Reviewer may request Context expansion if evidence is insufficient.

---

## 14. Quality metrics

Track:

```text
first-pass approval rate
average review cycles
percentage routed to Analysis
percentage routed to Context
percentage requiring user input
repeat-finding rate
approved-plan implementation rework rate
code-review defects traceable to plan
test failures traceable to plan
```

The last two are especially useful:

> If Code Review repeatedly catches issues that Plan Review should have caught, improve Plan Review policy.

---

## 15. Anti-bottleneck rules

Because Plan Review is a potential bottleneck:

1. use risk-adaptive depth;
2. use delta review after revisions;
3. cap review cycles;
4. route defects to their true owner;
5. avoid stylistic findings;
6. keep feedback structured/actionable;
7. use deterministic checks for schema/dependency validation;
8. invoke specialized reviewers only conditionally;
9. reuse previous findings rather than rediscovering them;
10. collect downstream metrics and tune the gate.

---

## 16. Recommended v1

For the first implementation:

```yaml
plan_review:
  enabled: true
  default_depth: standard
  max_review_cycles: 2
  delta_review: true
  independent_reviewer: true

  specialized_reviews:
    enabled: false
```

Start with one high-quality independent reviewer.

Add specialized reviewers later based on measured failure patterns.

---

## 17. Accepted decisions

1. Plan Review is mandatory in v1 for managed implementation tasks.
2. Maximum two direct Planning↔Review cycles.
3. Reviewer routes defects to Planning/Analysis/Context/User/Blocked.
4. Delta review is supported.
5. Blocking feedback must be evidence-backed and actionable.
6. Review findings persist across plan versions.
7. Specialized reviewers are conditional/future, not default v1.
8. Reviewer context is evidence-focused and independent from planner scratchpad.
9. Plan Review is monitored as a measurable bottleneck.
