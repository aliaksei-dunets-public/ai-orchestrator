# Documentation Subgraph Architecture

**Status:** Accepted design draft v0.1  
**Scope:** Development Workflow — documentation impact detection, update, and validation

## 1. Recommendation

Documentation should be a **reusable subgraph**, but documentation updates must be conditional.

The subgraph first answers:

> Did this change create a documentation obligation?

Only then does it update documentation.

The preferred flow is:

```text
DOCUMENTATION REQUEST
      ↓
1. DOCUMENTATION IMPACT CHECK
      │
      ├── no impact ─────────────► NO_CHANGE
      │
      └── impact found
              ↓
2. RESOLVE DOCUMENTATION TARGETS
              ↓
3. CLASSIFY TARGET SAFETY
              ↓
4. BUILD DOCUMENTATION UPDATE PLAN
              ↓
5. UPDATE DOCUMENTATION
              ↓
6. VALIDATE DOCUMENTATION
              ↓
7. CLASSIFY POST-DOC REVIEW NEED
              ↓
DOCUMENTATION RESULT
```

Documentation is not generated merely because code changed.

---

## 2. Position in Development Workflow

Current flow:

```text
Implementation
      ↓
Code Review
      ↓
Testing
      ↓
Documentation
      ↓
Final Validation
```

This ordering is suitable if the Documentation stage primarily modifies non-executable documentation artifacts.

However, documentation may sometimes live close to source code. Therefore the subgraph must classify documentation targets before editing them.

---

## 3. Documentation target classes

### Class A — External / non-executable documentation

Examples:

```text
Markdown
project wiki
architecture docs
developer guides
README
runbooks
release notes
decision records
```

Typical behavior:

```text
update
→ documentation validation
→ Final Validation
```

No new Code Review is normally required unless project policy says otherwise.

### Class B — Source-adjacent documentation

Examples:

```text
docstrings
Javadoc
ABAP Doc
XML comments
inline API documentation
code comments
```

These change source files but normally do not change runtime behavior.

Typical behavior:

```text
update
→ lightweight/delta review
→ optional targeted syntax/build validation
→ continue
```

Whether a delta Code Review is required is project-policy dependent.

### Class C — Contract/runtime-affecting "documentation"

Examples:

```text
API annotations
schema annotations
OpenAPI source definitions
CDS annotations affecting exposure/UI/runtime
configuration treated as documentation
deployment descriptors
generated contract sources
```

These are **not documentation-only changes**.

They belong to Implementation.

If Documentation discovers such a required change:

```text
documentation
      ↓
implementation_change_required
      ↓
Planning / Implementation as appropriate
```

The Documentation subgraph must not silently modify runtime-affecting artifacts after Testing.

This distinction prevents the Documentation stage from invalidating already reviewed/tested code.

---


## 3A. Documentation domains

Documentation impact is evaluated across several documentation domains.

```text
DOCUMENTATION
│
├── Domain / Business Documentation
├── Technical Documentation
├── Architecture Documentation
├── API / Contract Documentation
├── Developer Documentation
└── Operational Documentation
```

### Domain / Business Documentation

This documentation describes **what the system does and why**, rather than how the code is implemented.

Typical content:

```text
business concepts
business rules
validations
allowed / prohibited operations
state transitions
lifecycle rules
business workflows
edge cases
terminology
business invariants
```

Example:

Bad domain documentation:

```text
PaymentService.cancel checks field X and calls method Y.
```

Preferred:

```text
A payment may be cancelled only before settlement completes.
After settlement, cancellation is rejected.
A rejected cancellation must not change payment state.
```

Domain documentation should remain implementation-independent where possible.

### Technical Documentation

Describes:

```text
components
APIs
data model
configuration
integrations
technical constraints
extension points
```

### Architecture Documentation

Describes:

```text
architectural boundaries
major decisions
layering
component responsibilities
cross-cutting patterns
ADRs
```

### Developer Documentation

Describes:

```text
setup
how to extend
project conventions
examples
development workflows
```

### Operational Documentation

Describes:

```text
deployment
migration
monitoring
recovery
runbooks
operational constraints
```

The same task may impact several documentation domains.


## 4. Inputs

The subgraph receives:

```text
Task Artifact
Implementation Analysis
Approved Plan
Implementation Result
Code Review Result
Testing Result
Project Profile
Context Package / documentation references
actual changed scope
```

Optional:

```text
previous Documentation Result
documentation inventory/index
```

---

## 5. Stage 1 — Documentation Impact Check

**Type:** reusable deterministic-first / AI-assisted node

Purpose:

> Determine whether any documentation must change because of the implementation.

Candidate impact triggers:

```text
public API changed
behavior changed
configuration changed
architecture changed
new capability introduced
developer workflow changed
operational procedure changed
error/recovery behavior changed
migration introduced
user-facing behavior changed
obsolete documentation discovered
```

Possible result:

```yaml
documentation_impact:
  result:
    no_change | update_required | implementation_change_required | needs_context
```

---


## 5A. Domain / business impact checks

The Documentation Impact Check must explicitly ask:

```text
Did business behavior change?
Did a business rule change?
Did validation behavior change?
Did a state transition change?
Did a workflow change?
Did a business invariant change?
Did terminology change?
Did an edge case become newly supported or prohibited?
```

If yes, the subgraph must identify the authoritative Domain / Business documentation target when one exists.

If no authoritative domain document exists, project policy may choose to:

```text
create a new domain document
or
record a documentation maintenance candidate
```

The default should be to prefer existing project documentation structure over creating new files automatically.


## 6. No-change is a valid successful result

Example:

```yaml
documentation_impact:
  result: no_change
  reason: >
    Internal implementation changed without modifying behavior,
    contracts, configuration, architecture, or developer usage.
```

This avoids low-value documentation churn.

The final Documentation Result still records that impact was evaluated.

---

## 7. Reusable Documentation Impact capability

`documentation-impact` should be reusable independently.

Potential callers:

```text
Development Documentation
Code Review
Refactoring workflow
Migration workflow
Release workflow
Architecture change workflow
```

Candidate contract:

```yaml
documentation_impact_request:
  task_ref: TASK-0042
  changed_scope_ref: DIFF-0042
  analysis_ref: ANALYSIS-0042
  project_profile_ref: PROJECT-PROFILE
```

Output:

```yaml
documentation_impact_result:
  impacted: true
  targets: [...]
  reasons: [...]
```

This is a strong reusable subgraph/capability candidate.

---

## 8. Stage 2 — Resolve Documentation Targets

The subgraph identifies concrete documentation artifacts.

Examples:

```text
README.md
docs/architecture.md
docs/api/payment.md
ADR-0012
project wiki page
ABAP Doc for public class/interface
runbook
migration guide
```

Resolution should prefer existing project conventions.

Do not create a new documentation location if an authoritative existing location already exists.

---

## 9. Source of truth

Each target should have a source-of-truth relationship.

Example:

```yaml
documentation_target:
  path: docs/api/payment.md

  source_of_truth:
    - Payment API contract
    - implementation behavior
```

The Documentation agent should derive content from current verified project state, not from stale plan prose alone.

Priority:

```text
actual implemented behavior
+
approved task/plan intent
+
tested result
+
authoritative project docs
```

---


## 9A. Business truth source

Domain documentation must be synchronized from **verified system behavior**, not merely from planned behavior.

Recommended evidence priority:

```text
Task intent
+
approved Analysis constraints / business rules
+
actual Implementation
+
Code Review findings
+
passed Testing behavior
=
documented business behavior
```

Documentation must not preserve an Analysis assumption that was disproved during implementation or testing.

For important business rules, the documentation update should reference the behavior actually proven by the implementation/tests.


## 10. Stage 3 — Classify Target Safety

Every target is classified:

```yaml
target_class:
  external_doc
  source_adjacent_doc
  runtime_affecting_contract
```

This determines downstream routing.

The classification should be conservative.

If unsure whether an annotation affects runtime:

```text
treat as runtime-affecting
```

and route upstream.

---

## 11. Stage 4 — Documentation Update Plan

The update plan is intentionally small.

It contains:

```text
target
reason
required change
source evidence
validation
```

Example:

```yaml
documentation_update:
  target: docs/health-check.md

  reason: new capability

  required_change:
    - document invocation
    - document result contract
    - document extension point

  evidence:
    - IMPLEMENTATION-0042
    - TESTING-0042
```

This is not another full Development Plan.

---

## 12. Stage 5 — Update Documentation

**Type:** documentation agent / deterministic tools

The agent should:

- preserve existing documentation style;
- make the smallest coherent update;
- avoid rewriting unrelated sections;
- preserve authored examples unless invalid;
- update references/links where needed;
- avoid invented behavior;
- use verified names/contracts from implementation.

---

## 13. Documentation content types

Possible updates:

```text
architecture docs
technical design docs
developer guides
API docs
configuration docs
runbooks
migration docs
ADRs
inline/source-adjacent documentation
release/change notes
```

Not every task needs each type.

---

## 14. ADR handling

Architecture Decision Records require special treatment.

A normal feature should not automatically create an ADR.

ADR creation/update is appropriate when:

```text
new architecture decision was explicitly made
existing decision was superseded
meaningful architectural trade-off must be preserved
project policy requires ADR for this class of change
```

If implementation introduces a previously unapproved architecture decision, this is not merely a documentation task; it may require replanning/review.

---

## 15. Stage 6 — Documentation Validation

Validation is tool-first where possible.

Possible checks:

```text
Markdown lint
broken links
reference existence
code sample validation
schema/document consistency
documentation build
generated-doc diff
spell/style checks if configured
source symbol existence
```

AI validation may check:

- consistency with actual implementation;
- missing important behavior;
- contradictions;
- stale examples;
- audience appropriateness.

---

## 16. Documentation truth validation

The strongest validation question is:

> Does the updated documentation describe the implementation that actually passed review/testing?

For important claims, compare against:

```text
Implementation Result
Code Review Result
Testing Result
actual source/contracts
```

Do not validate documentation only against the Plan because implementation may contain approved minor deviations.

---

## 17. Source-adjacent documentation handling

If Documentation edits source files only for non-runtime documentation:

```text
Documentation Update
      ↓
Delta Code Review?
      ↓
Targeted syntax/build check?
```

Project Profile may define:

```yaml
documentation:
  source_adjacent:
    require_delta_code_review: true
    require_targeted_validation: true
```

This avoids silently changing reviewed source after Code Review.

---

## 18. Runtime-affecting documentation discovery

If a required "documentation" update changes runtime semantics:

```text
API annotation
CDS annotation
schema contract
runtime metadata
```

return:

```yaml
result: implementation_change_required
```

Routing depends on materiality:

```text
minor already-approved implementation omission
→ Implementation
→ Code Review
→ Testing

material strategy/scope change
→ Planning
→ Plan Review
→ Implementation
```

Documentation must never bypass those gates.

---

## 19. Documentation drift discovered during update

The agent may discover pre-existing stale documentation unrelated to the Task.

Default:

```text
do not expand current task
```

Record:

```yaml
maintenance_candidate:
  type: documentation_drift
```

Only fix it in the current task if:

- it directly conflicts with the changed area;
- leaving it unchanged would make new documentation misleading;
- project policy permits small adjacent cleanup.

This prevents documentation scope creep.

---

## 20. Failure outcomes

Recommended:

```text
success
no_change
needs_context
implementation_change_required
needs_input
blocked
failure
```

### needs_context

Authoritative behavior/source cannot be resolved.

### implementation_change_required

Required update belongs in executable/contract code.

### needs_input

Documentation policy/audience/business behavior is ambiguous.

### blocked

Required documentation system/access is unavailable and documentation is mandatory.

---

## 21. Reuse

The Documentation subgraph is reusable across:

```text
feature
bugfix
refactoring
migration
release
architecture change
configuration change
```

Reusable internal capability:

```text
documentation-impact
```

Possible future reusable capability:

```text
documentation-validation
```

---

## 22. Model policy

| Stage | Policy |
|---|---|
| Impact check | deterministic-first + cheap/standard |
| Target resolution | deterministic + standard |
| Target safety classification | deterministic-first |
| Update plan | cheap/standard |
| Documentation update | standard |
| Validation | deterministic + standard |
| complex architecture consistency | expert escalation |

---

## 23. Accepted decisions

1. Documentation is a reusable subgraph.
2. Documentation starts with an Impact Check.
3. `no_change` is a normal successful outcome.
4. Documentation targets are classified as external, source-adjacent, or runtime-affecting.
5. Runtime-affecting artifacts return to Implementation/Planning and never bypass review/testing.
6. Source-adjacent docs may require delta Code Review.
7. Documentation derives truth from actual reviewed/tested implementation.
8. Unrelated documentation drift becomes a maintenance candidate instead of expanding scope.
9. ADRs are updated only when a real architecture decision exists.
10. Documentation validation is tool-first where possible.
