# Semantic Knowledge Contract

**Status:** Candidate normalized contract v0.1

## 1. Semantic node

```yaml
semantic_node:
  id: SEM-0001

  project_ref: PROJECT-001
  layer: semantic

  kind: business_concept | responsibility | workflow | architecture_decision | constraint | invariant | domain_rule | convention | risk | known_issue | assumption | capability
  subtype: string

  name: string
  description: string

  scope:
    component_refs: []
    environment: all
    version_from: string | null
    version_to: string | null

  provenance:
    - source: architecture_document | adr | domain_document | api_contract | test_evidence | source_code | git_history | task_analysis | implementation_result | code_review | incident_analysis | ai_inference | human_input
      ref: string | null

  evidence:
    supporting: []
    conflicting: []

  confidence: verified | high | medium | low | unknown

  status: candidate | current | potentially_stale | conflicted | superseded | invalid

  revision:
    first_seen: string | null
    last_verified: string | null

  extensions: {}
```

## 2. Semantic edge

```yaml
semantic_edge:
  id: SEM-E-0001

  project_ref: PROJECT-001

  source: node_id
  relation: responsible_for | participates_in | governed_by | constrained_by | implements_rule | depends_on_concept | related_to | affected_by | supersedes | replaces | violates | mitigates | assumes | requires
  target: node_id

  evidence:
    supporting: []
    conflicting: []

  provenance: []

  confidence: verified | high | medium | low | unknown

  status: candidate | current | potentially_stale | conflicted | superseded | invalid

  revision:
    first_seen: string | null
    last_verified: string | null
```

`source` and `target` may reference structural or semantic nodes.

## 3. Semantic candidate

```yaml
semantic_candidate:
  candidate_id: KC-0001

  operation: add | modify | challenge | supersede

  subject_ref: node_id | null

  proposed_node: {}
  proposed_edge: {}

  rationale: string

  evidence_refs: []

  provenance:
    source: task_analysis

  proposed_confidence: medium
```

Candidates are not persistent truth until validated.

## 4. Conflict record

```yaml
semantic_conflict:
  id: CONFLICT-0001

  fact_ref: SEM-E-0001

  supporting_evidence:
    - docs/payment.md

  conflicting_evidence:
    - src/cancellation/service.py

  status: unresolved

  detected_at_revision: abc123
```

## 5. Component summary

```yaml
component_summary:
  component_ref: structural_node_id

  summary: string

  derived_from:
    - SEM-0001
    - SEM-E-0003

  revision: abc123
```

Summaries are derived and disposable.

## 6. Knowledge update batch

```yaml
knowledge_update_batch:
  project_ref: PROJECT-001
  revision: abc123

  candidates:
    added: []
    modified: []
    challenged: []
    superseded: []

  source_workflow:
    task_ref: TASK-0042
    stage: analysis
```

## 7. Design rules

- semantic facts require evidence;
- `ai_inference` is never hidden;
- conflicts are preserved;
- workflow agents submit candidates;
- validation and persistence are centralized in Knowledge Refresh;
- structural nodes are reused wherever possible;
- summaries are derived from facts, not primary knowledge.
