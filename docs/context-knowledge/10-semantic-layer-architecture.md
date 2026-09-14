# Semantic Knowledge Layer Architecture

**Status:** Detailed design draft v0.1  
**Scope:** Project Knowledge Map — semantic understanding layer

## 1. Purpose

The Semantic Knowledge Layer gives meaning to the Structural Graph.

The Structural Graph answers:

- what exists;
- where it is;
- what calls or depends on what;
- what reads or writes data;
- what exposes APIs;
- what is tested.

The Semantic Layer answers:

- what a component is responsible for;
- which business concept it implements;
- which workflow it participates in;
- which architecture decision governs it;
- which constraints and invariants apply;
- which risks, assumptions, and conventions matter.

The layer must improve AI reasoning without turning inferred conclusions into unverified facts.

## 2. Core principle

```text
STRUCTURAL GRAPH
      +
SEMANTIC KNOWLEDGE
      =
PROJECT KNOWLEDGE MAP
```

Every semantic fact must preserve:

- provenance;
- evidence;
- confidence;
- freshness;
- scope.

## 3. Not one global summary

Do not store one giant project summary.

Prefer independently referenceable facts:

```text
PaymentModule --responsible_for--> PaymentLifecycle
PaymentService --participates_in--> PaymentCancellation
PaymentCancellation --governed_by--> ADR-0042
PaymentAPI --constrained_by--> BackwardCompatibilityRule
```

This enables targeted retrieval, verification, and refresh.

## 4. Core semantic entity types

Recommended kinds:

```text
business_concept
responsibility
workflow
architecture_decision
constraint
invariant
domain_rule
convention
risk
known_issue
assumption
capability
```

These use:

```yaml
layer: semantic
```

## 5. Core semantic relations

Recommended relations:

```text
responsible_for
participates_in
governed_by
constrained_by
implements_rule
depends_on_concept
related_to
affected_by
supersedes
replaces
violates
mitigates
assumes
requires
```

Structural and semantic relations coexist.

## 6. Progressive semantic knowledge

### L2 — Semantic Overview

Created during Initial Load:

- major components;
- top-level responsibilities;
- primary business concepts;
- major workflows;
- architecture decisions;
- major constraints;
- project conventions.

### L3 — Deep Semantic Knowledge

Accumulated during real work:

- edge cases;
- hidden rules;
- assumptions;
- historical decisions;
- tricky invariants;
- operational risks;
- failure modes;
- module-specific constraints.

The Initial Load should not attempt to reach complete L3 coverage.

## 7. Semantic Bootstrap Subgraph

```text
SEMANTIC OVERVIEW
       │
       ▼
SELECT HIGH-VALUE SOURCES
       │
       ▼
BUILD SEMANTIC CANDIDATES
       │
       ▼
LINK TO STRUCTURAL ENTITIES
       │
       ▼
VERIFY / CROSS-CHECK
       │
       ▼
RESOLVE CONFLICTS
       │
       ▼
ASSIGN CONFIDENCE
       │
       ▼
VALIDATE
       │
       ▼
PERSIST
```

This is AI-assisted but evidence-driven.

## 8. High-value sources

Priority:

1. architecture documentation;
2. ADRs;
3. domain documentation;
4. API contracts;
5. module documentation;
6. project conventions;
7. tests;
8. code structure;
9. Git history when useful.

Avoid full-repository semantic reading during bootstrap.

## 9. Semantic candidates

The AI extracts candidates, not final truth.

```yaml
semantic_candidate:
  type: responsibility

  subject_ref: PaymentService
  relation: responsible_for

  object:
    kind: business_concept
    name: PaymentValidation

  evidence:
    - docs/payment.md
    - src/payment/service.py

  proposed_confidence: high
```

Candidates must be validated before persistence.

## 10. Link to Structural Graph

Reuse existing structural nodes wherever possible.

```text
"PaymentService"
      ↓ identity resolution
structural node PaymentService
```

Do not create a duplicate semantic version of the same class/API/table.

Semantic nodes represent meaning. Structural nodes represent project objects.

## 11. Verification

Important claims should be cross-checked where feasible.

Possible result:

```text
supported
partially_supported
conflicted
unsupported
```

Unsupported facts must not silently become trusted knowledge.

## 12. Conflict is first-class knowledge

Example:

```text
Documentation says:
PaymentService owns cancellation

Code says:
CancellationService owns cancellation
```

Persist the disagreement:

```yaml
status: conflicted

evidence:
  supporting:
    - docs/payment.md

  conflicting:
    - src/cancellation/service.py
```

Context can then surface the conflict to downstream agents.

## 13. Confidence

Semantic confidence should derive from evidence, not only model certainty.

Factors:

- authority of source;
- number of independent supporting sources;
- source freshness;
- agreement with structural graph;
- agreement between docs and code;
- explicit vs inferred statement.

Candidate levels:

```text
verified
high
medium
low
unknown
```

## 14. Provenance

Candidate provenance types:

```text
architecture_document
adr
domain_document
api_contract
test_evidence
source_code
git_history
task_analysis
implementation_result
code_review
incident_analysis
ai_inference
human_input
```

`ai_inference` must never be hidden.

## 15. Scope

Semantic facts need explicit scope.

```yaml
scope:
  project: PROJECT-001
  components:
    - payment
  environment: all
```

Scope prevents local knowledge from being treated as global.

## 16. Semantic lifecycle

```text
candidate
   ↓
current
   ↓
potentially_stale
   ↓
revalidation
   ├── current
   ├── conflicted
   ├── superseded
   └── invalid
```

Recommended states:

```text
candidate
current
potentially_stale
conflicted
superseded
invalid
```

## 17. Semantic Refresh

Refresh is targeted by default.

Triggers include:

- code changes;
- documentation changes;
- ADR changes;
- structural graph changes;
- context inconsistencies;
- analysis discoveries;
- code review findings;
- incidents.

Flow:

```text
CHANGE / DISCOVERY
       │
       ▼
FIND AFFECTED SEMANTIC FACTS
       │
       ▼
MARK POTENTIALLY STALE
       │
       ▼
RE-EVALUATE EVIDENCE
       │
       ▼
UPDATE / CONFLICT / SUPERSEDE / INVALIDATE
```

## 18. Task-derived enrichment

Real task execution is the main source of L3 knowledge.

Task agents must not write directly to PKM.

They emit:

```yaml
knowledge_candidates:
  added: []
  changed: []
  challenged: []
  superseded: []
```

Knowledge Refresh validates and persists them.

## 19. Anti-hallucination rules

1. No evidence-free high-confidence facts.
2. AI inference is explicitly tagged.
3. Inferred facts cannot overwrite verified facts directly.
4. Contradictory evidence creates conflict.
5. Agent memory is not evidence by itself.
6. Summaries reference underlying facts.
7. Stale knowledge remains visible.
8. Low-confidence facts may guide search but are not authoritative.

## 20. Derived summaries

The system may generate disposable summaries for fast retrieval.

```yaml
component_summary:
  component_ref: PaymentModule

  summary: >
    Handles core payment lifecycle operations.

  derived_from:
    - SEM-001
    - SEM-002

  revision: abc123
```

The summary is not the primary knowledge object.

## 21. Context integration

Knowledge-Assisted Context can retrieve:

```text
Structural neighbors
        +
Semantic facts
        +
Derived summaries
```

For important decisions, the downstream agent can inspect the underlying evidence.

## 22. Model policy

| Stage | Policy |
|---|---|
| Source selection | cheap |
| Candidate extraction | standard |
| Cross-check | standard |
| Ambiguous architecture interpretation | expert escalation |
| Conflict analysis | standard → expert |
| Confidence assignment | deterministic policy + AI evidence analysis |
| Summary generation | cheap |
| Persistence | deterministic |

## 23. Initial Load limits

During Initial Load, target only:

```text
major components
major responsibilities
main domain concepts
main workflows
ADRs
major constraints
project conventions
```

Do not attempt to discover every edge case or business rule.

## 24. Accepted design decisions

1. Semantic knowledge is stored as structured facts, not one global summary.
2. Structural nodes are reused instead of duplicated.
3. Semantic knowledge is progressive: L2 bootstrap + L3 enrichment.
4. Every semantic claim preserves evidence and provenance.
5. Conflicts are first-class knowledge.
6. AI inference is explicitly distinguishable.
7. Workflow agents submit candidates instead of mutating PKM.
8. Semantic refresh is targeted by default.
9. Derived summaries are rebuildable.
10. Low-confidence knowledge can guide discovery but is not treated as authoritative.
