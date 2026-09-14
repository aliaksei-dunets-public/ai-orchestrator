# Knowledge Refresh Subgraph

**Status:** Detailed design draft v0.1  
**Scope:** Project Knowledge Map — incremental, targeted, and full refresh

## 1. Purpose

`Knowledge Refresh` keeps the Project Knowledge Map synchronized with the real project over time.

It consumes changes in the project and/or new knowledge discovered by workflows, determines what part of the map may be affected, invalidates stale knowledge, re-extracts the relevant structural region, re-evaluates semantic facts, validates the result, and persists a new PKM revision.

The central rule is:

> Refresh should update only the smallest safe affected region by default.

A full rescan is an exception, not the normal path.

---

## 2. Position in the orchestrator

Typical Development Workflow integration:

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
      ↓
Knowledge Refresh
      ↓
Complete
```

Other workflows may invoke it too:

```text
Investigation
Incident
Documentation Update
Architecture Change
Manual Maintenance
Health/Audit
```

---

## 3. Refresh is a subgraph

```text
REFRESH REQUEST
      │
      ▼
1. NORMALIZE TRIGGERS
      │
      ▼
2. BUILD / RESOLVE CHANGESET
      │
      ▼
3. DETERMINE REFRESH MODE
      │
      ▼
4. IDENTIFY AFFECTED REGION
      │
      ▼
5. INVALIDATE AFFECTED KNOWLEDGE
      │
      ▼
6. STRUCTURAL RE-EXTRACTION
      │
      ▼
7. SEMANTIC RE-EVALUATION
      │
      ▼
8. MERGE CANDIDATES
      │
      ▼
9. VALIDATE PKM DELTA
      │
      ▼
10. PERSIST ATOMIC UPDATE
      │
      ▼
11. UPDATE METADATA / COVERAGE
      │
      ▼
REFRESH RESULT
```

This is not one LLM node. Most stages should be deterministic.

---

## 4. Supported modes

```yaml
mode:
  enum:
    - incremental
    - targeted
    - full
```

### Incremental

Default mode after normal project changes.

Typical trigger:

```text
git diff
changed files
changed symbols
updated docs
```

### Targeted

Used when a specific area is suspected to be stale or incomplete.

Typical trigger:

```text
Context detected stale edge
Analysis requests deeper knowledge
Audit reports inconsistent component
```

### Full

Rare.

Typical trigger:

- large repository migration;
- branch synchronization after substantial divergence;
- ontology/adapters changed incompatibly;
- map corruption;
- prolonged stale state;
- major framework/platform migration;
- Health/Audit explicitly recommends rebuild.

---

## 5. Refresh inputs

```yaml
refresh_request:
  project_ref: PROJECT-001

  mode: incremental

  base_map_revision: PKM-00042
  project_revision_before: abc123
  project_revision_after: def456

  triggers:
    - type: git_diff
      ref: DIFF-0042

    - type: knowledge_candidates
      ref: KUB-0042

  target_scope: null

  policy:
    semantic_refresh: true
    refresh_summaries: true
    allow_full_fallback: true
```

For targeted refresh:

```yaml
refresh_request:
  mode: targeted

  target_scope:
    nodes:
      - PaymentService
    concepts:
      - PaymentCancellation

  reasons:
    - stale_relation_detected
```

---

## 6. Stage 1 — Normalize Triggers

**Type:** deterministic action

Refresh may be triggered by multiple sources:

```text
Git diff
workspace diff
changed files
changed symbols
documentation edits
ontology changes
adapter updates
knowledge candidates
audit findings
manual request
context inconsistency
```

The node normalizes them into a common trigger set.

Example:

```yaml
refresh_triggers:
  structural_changes:
    - src/payment/service.py

  documentation_changes:
    - docs/payment.md

  knowledge_candidates:
    - KC-0042
    - KC-0043

  audit_findings: []
```

---

## 7. Stage 2 — Build / Resolve ChangeSet

**Type:** deterministic/tool node

Create a normalized `ChangeSet`.

```yaml
changeset:
  project_ref: PROJECT-001

  before_revision: abc123
  after_revision: def456

  files:
    added: []
    modified:
      - src/payment/service.py
      - docs/payment.md
    deleted: []

  symbols:
    added: []
    modified:
      - PaymentService.cancel
    deleted: []

  configuration:
    modified: []

  documentation:
    modified:
      - docs/payment.md

  ontology:
    changed: false
```

If symbol-level diff is unavailable, the system may begin at file level and refine the scope during structural extraction.

---

## 8. Stage 3 — Determine Refresh Mode

**Type:** router / policy node

A requested mode may be escalated.

Example:

```text
incremental requested
      ↓
adapter version changed incompatibly
      ↓
escalate to targeted/full
```

Candidate escalation conditions:

- ontology breaking change;
- repository history rewritten;
- too many changed files;
- extraction coverage uncertain;
- base map revision does not match project ancestry;
- PKM audit reports widespread stale state.

Mode selection should be policy-driven, not model-driven where possible.

---

## 9. Stage 4 — Identify Affected Region

**Type:** hybrid impact-analysis node

Purpose:

> Determine the smallest graph region that must be invalidated and re-evaluated.

Inputs:

- ChangeSet;
- current Structural Graph;
- Semantic Layer;
- ontology;
- adapter capabilities.

Example:

```text
Changed:
PaymentService.cancel

Directly affected:
PaymentService

Structural neighbors:
PaymentRepository
PaymentController
CancellationService
PaymentServiceTest

Semantic neighbors:
PaymentCancellation
BackwardCompatibilityRule
ADR-0042
```

Output:

```yaml
affected_region:
  structural_nodes:
    direct:
      - PaymentService
    neighbors:
      - PaymentRepository
      - PaymentController
      - PaymentServiceTest

  semantic_nodes:
    - PaymentCancellation
    - BackwardCompatibilityRule

  documents:
    - docs/payment.md

  traversal:
    max_depth_used: 1

  confidence: high
```

The affected-region calculation should prefer graph traversal and static evidence over AI speculation.

---

## 10. Impact propagation rules

Refresh should use relation-aware propagation.

Examples:

```text
class modified
   → its calls/imports/tests may be stale

public API modified
   → consumers + docs + tests may be affected

data entity modified
   → readers/writers + API contracts may be affected

ADR modified
   → governed semantic facts may be affected

test modified
   → test relation may be affected
   → target implementation is not automatically stale
```

Each relation type can define refresh propagation rules in the registry.

Example:

```yaml
refresh_policy:
  relation: calls

  on_source_changed:
    invalidate_edge: true
    recheck_target: false

  on_target_deleted:
    invalidate_edge: true
    inspect_source: true
```

This should eventually be part of the Relation Registry.

---

## 11. Stage 5 — Invalidate Affected Knowledge

**Type:** deterministic action

Invalidation happens before re-extraction.

Do not delete immediately.

Example:

```yaml
status: potentially_stale
```

for:

- affected structural nodes;
- outgoing/incoming relations governed by propagation rules;
- semantic facts whose evidence intersects changed artifacts;
- derived summaries based on stale facts.

Why invalidation first:

1. prevents stale facts from being treated as current during refresh;
2. enables safe interruption/resume;
3. preserves auditability;
4. allows comparison of old and new knowledge.

---

## 12. Stage 6 — Structural Re-extraction

**Type:** Structural Extraction subgraph

Reuse the same extraction architecture as Bootstrap.

The difference is output:

```yaml
type: structural_delta
```

Example:

```yaml
structural_delta:
  added_nodes:
    - CancellationService

  changed_nodes:
    - PaymentService

  removed_nodes: []

  added_edges:
    - CancellationService -> PaymentRepository : calls

  removed_edges:
    - PaymentService -> LegacyCancellationAdapter : calls
```

Only the affected scope should be re-extracted by default.

---

## 13. Rename / move handling

Refresh should attempt to distinguish:

```text
delete + add
```

from:

```text
rename / move
```

Candidate evidence:

- Git rename detection;
- stable platform ID;
- matching symbol signature;
- high fingerprint similarity.

If confident:

```yaml
lineage:
  old_ref: PaymentServiceOld
  new_ref: PaymentService

  relation: supersedes
```

If ambiguous, preserve separate entities and emit a diagnostic rather than silently merging.

---

## 14. Stage 7 — Semantic Re-evaluation

**Type:** Semantic Refresh subgraph

Inputs:

- affected semantic facts;
- structural delta;
- changed docs;
- knowledge candidates;
- current evidence;
- task/workflow artifacts if available.

Flow:

```text
Affected Semantic Facts
       │
       ▼
Collect Current Evidence
       │
       ▼
Evaluate Existing Claims
       │
       ├── still valid
       ├── changed
       ├── conflicted
       ├── superseded
       └── invalid
       │
       ▼
Evaluate New Candidates
```

Important:

> Structural change does not automatically imply semantic change.

A semantic fact is re-evaluated only when its evidence, linked structure, or explicit candidate indicates possible impact.

---

## 15. Knowledge candidates

Workflow agents may supply:

```yaml
knowledge_candidates:
  added:
    - KC-0042

  changed: []

  challenged:
    - KC-0043

  superseded: []
```

Refresh validates them against current project evidence.

Possible candidate outcomes:

```text
accepted
accepted_with_lower_confidence
rejected
conflicted
needs_more_evidence
```

Agents do not persist semantic truth directly.

---

## 16. Stage 8 — Merge Candidates

**Type:** deterministic-first merge node

Merge inputs:

```text
old PKM
+
structural delta
+
semantic re-evaluation
+
validated knowledge candidates
+
conflict records
```

Rules:

1. verified facts are never silently overwritten by lower-confidence candidates;
2. duplicate nodes/edges merge evidence;
3. invalidated facts become current only after verification;
4. conflicting evidence creates conflict state;
5. superseded semantic facts remain traceable;
6. derived summaries are invalidated when dependencies change.

---

## 17. Stage 9 — Validate PKM Delta

**Type:** gate

Validation categories:

### Referential integrity

- all edge endpoints exist;
- no invalid references;
- no orphaned mandatory evidence refs.

### Ontology validity

- node kinds valid;
- relations registered;
- source/target kind constraints valid.

### Revision consistency

- refresh based on correct project/map revision;
- adapter outputs refer to intended revision.

### Evidence

- high-confidence facts have sufficient evidence;
- AI-inferred semantic changes are tagged.

### Coverage

- changed scope was actually scanned;
- unresolved areas are recorded.

Possible result:

```yaml
result:
  enum:
    - valid
    - valid_with_warnings
    - retry_required
    - invalid
```

---

## 18. Stage 10 — Persist Atomic Update

**Type:** deterministic action

Persistence should be atomic at the logical PKM revision level.

Conceptually:

```text
PKM revision N
      +
validated delta
      ↓
PKM revision N+1
```

If persistence fails:

```text
old PKM remains valid
new revision is not published
```

Avoid half-written maps.

Candidate metadata:

```yaml
pkm_revision:
  id: PKM-00043
  parent: PKM-00042

  project_revision: def456

  refresh:
    mode: incremental
    result: valid_with_warnings
```

---

## 19. Stage 11 — Update metadata / coverage

Update:

- current project revision;
- map revision;
- affected coverage;
- adapter versions;
- ontology versions;
- stale regions;
- conflict counts;
- last successful refresh;
- refresh warnings.

Example:

```yaml
knowledge_map_health:
  current_project_revision: def456

  stale_regions:
    - external/plugins

  conflicts: 2

  last_refresh:
    mode: incremental
    status: success
```

---

## 20. Refresh result

```yaml
refresh_result:
  status: success_with_warnings

  mode: incremental

  old_map_revision: PKM-00042
  new_map_revision: PKM-00043

  project_revision: def456

  structural:
    added_nodes: 1
    changed_nodes: 2
    removed_nodes: 0
    added_edges: 3
    removed_edges: 1

  semantic:
    accepted_candidates: 2
    changed_facts: 1
    conflicts_created: 1

  remaining_stale_regions:
    - external/plugins

  warnings:
    - dynamic plugin wiring not fully resolved
```

---

## 21. Development task failure policy

Knowledge Refresh is important but usually secondary to successful delivery.

Default policy:

```text
Implementation validated successfully
      ↓
Knowledge Refresh fails non-critically
      ↓
mark affected PKM region stale
      ↓
create maintenance finding
      ↓
Complete task
```

Task should fail only if:

- project delivery itself depends on PKM update;
- persistence corruption threatens PKM integrity;
- policy marks knowledge synchronization as mandatory;
- high-risk environment requires successful knowledge update.

---

## 22. Retry policy

Candidate retries:

```yaml
retry:
  structural_adapter_failure:
    max_attempts: 2

  semantic_validation_failure:
    max_attempts: 1
    escalation_profile: expert

  persistence_failure:
    max_attempts: 2
```

Retries must be bounded.

Repeated failures create maintenance findings.

---

## 23. Checkpoints / resumability

Recommended checkpoints:

```text
Normalized Triggers
ChangeSet
Affected Region
Invalidation Manifest
Structural Delta
Semantic Evaluation
Merged Delta
Validation Report
Persisted PKM Revision
```

Refresh can resume after interruption without recomputing every stage.

---

## 24. Concurrency

Two tasks may complete near each other.

The refresh system must detect stale base revisions.

Example:

```text
Task A refresh based on PKM-42 → writes PKM-43
Task B refresh based on PKM-42 → conflict
```

Candidate policy:

```text
Task B
  ↓
detect base revision mismatch
  ↓
rebase refresh inputs onto PKM-43
  ↓
recompute affected overlap
  ↓
validate
  ↓
persist PKM-44
```

Do not allow last-writer-wins silent overwrite.

---

## 25. Full refresh fallback

Incremental refresh may escalate when safety cannot be guaranteed.

Example:

```text
affected region too broad
or
repository ancestry mismatch
or
adapter/ontology incompatibility
      ↓
full refresh recommended
```

Full refresh may still preserve semantic history and conflict records where valid.

---

## 26. Model policy

| Stage | Policy |
|---|---|
| Trigger normalization | deterministic |
| ChangeSet | deterministic |
| Mode routing | deterministic |
| Affected region | deterministic-first / cheap escalation |
| Invalidation | deterministic |
| Structural re-extraction | deterministic |
| Semantic re-evaluation | standard → expert |
| Candidate merge | deterministic-first |
| Validation | deterministic + standard if semantic ambiguity |
| Persistence | deterministic |
| Metadata | deterministic |

The expensive model is concentrated in semantic reasoning.

---

## 27. Observability

Each refresh should record:

```text
duration
mode
affected scope size
adapters used
nodes/edges changed
semantic facts changed
conflicts created/resolved
warnings
retries
model profiles used
token/cost estimate
```

This supports future optimizer and health-check skills.

---

## 28. Accepted design decisions

1. Incremental refresh is the default.
2. Targeted and full refresh are first-class modes.
3. Invalidation occurs before re-extraction.
4. Structural extraction machinery is reused from Bootstrap.
5. Semantic refresh is targeted, not global.
6. Workflow agents emit candidates; Refresh owns validation/persistence.
7. PKM updates are atomic and revisioned.
8. Refresh is resumable.
9. Non-critical refresh failure normally does not fail the development task.
10. Concurrency uses revision checks/rebase, not last-writer-wins.
11. Relation registry will eventually contain propagation rules.
12. Full refresh is a safety fallback, not the normal workflow.
