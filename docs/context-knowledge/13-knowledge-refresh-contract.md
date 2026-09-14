# Knowledge Refresh Contracts

**Status:** Candidate normalized contracts v0.1

## 1. Refresh Request

```yaml
refresh_request:
  project_ref: PROJECT-001

  mode: incremental | targeted | full

  base_map_revision: PKM-00042

  project_revision_before: abc123
  project_revision_after: def456

  triggers:
    - type: git_diff | workspace_diff | knowledge_candidates | audit_finding | manual | ontology_change | adapter_change
      ref: string

  target_scope:
    nodes: []
    concepts: []
    paths: []

  policy:
    semantic_refresh: true
    refresh_summaries: true
    allow_full_fallback: true
```

## 2. ChangeSet

```yaml
changeset:
  project_ref: PROJECT-001

  before_revision: abc123
  after_revision: def456

  files:
    added: []
    modified: []
    deleted: []
    renamed: []

  symbols:
    added: []
    modified: []
    deleted: []

  configuration:
    added: []
    modified: []
    deleted: []

  documentation:
    added: []
    modified: []
    deleted: []

  ontology:
    changed: false

  adapters:
    changed: []
```

## 3. Affected Region

```yaml
affected_region:
  project_ref: PROJECT-001

  structural:
    direct_nodes: []
    neighbor_nodes: []
    paths: []

  semantic:
    facts: []
    concepts: []
    summaries: []

  traversal:
    relations_used: []
    max_depth_used: 0

  evidence_refs: []

  confidence: high | medium | low

  unresolved: []
```

## 4. Invalidation Manifest

```yaml
invalidation_manifest:
  map_revision: PKM-00042

  structural_nodes:
    mark_potentially_stale: []

  structural_edges:
    mark_potentially_stale: []

  semantic_nodes:
    mark_potentially_stale: []

  semantic_edges:
    mark_potentially_stale: []

  derived_artifacts:
    invalidate: []

  reason_refs:
    - changeset:CHANGE-0042
```

## 5. Structural Delta

```yaml
structural_delta:
  project_ref: PROJECT-001
  project_revision: def456

  added_nodes: []
  changed_nodes: []
  removed_nodes: []

  added_edges: []
  changed_edges: []
  removed_edges: []

  coverage:
    scanned_roots: []
    status: complete | partial

  diagnostics:
    warnings: []
    errors: []
```

## 6. Semantic Evaluation Result

```yaml
semantic_refresh_result:
  evaluated_facts: []

  unchanged: []

  changed: []

  conflicted: []

  superseded: []

  invalidated: []

  candidates:
    accepted: []
    accepted_with_lower_confidence: []
    rejected: []
    conflicted: []
    needs_more_evidence: []

  diagnostics:
    warnings: []
```

## 7. PKM Delta

```yaml
pkm_delta:
  base_map_revision: PKM-00042
  target_project_revision: def456

  structural:
    added_nodes: []
    changed_nodes: []
    removed_nodes: []

    added_edges: []
    changed_edges: []
    removed_edges: []

  semantic:
    added_nodes: []
    changed_nodes: []
    superseded_nodes: []
    invalidated_nodes: []

    added_edges: []
    changed_edges: []
    superseded_edges: []
    invalidated_edges: []

  conflicts:
    created: []
    resolved: []

  derived:
    summaries_to_regenerate: []

  stale_regions_remaining: []
```

## 8. Validation Report

```yaml
refresh_validation:
  result: valid | valid_with_warnings | retry_required | invalid

  referential_integrity: pass | warn | fail
  ontology_integrity: pass | warn | fail
  revision_integrity: pass | warn | fail
  evidence_integrity: pass | warn | fail
  coverage_integrity: pass | warn | fail

  warnings: []
  errors: []

  recommended_action:
    type: persist | retry | targeted_refresh | full_refresh | abort
```

## 9. PKM Revision

```yaml
pkm_revision:
  id: PKM-00043
  parent: PKM-00042

  project_ref: PROJECT-001
  project_revision: def456

  ontology_versions:
    core: 1
    extensions: {}

  adapter_versions: {}

  refresh:
    mode: incremental
    result: success_with_warnings

  created_at: timestamp
```

## 10. Refresh Result

```yaml
refresh_result:
  status: success | success_with_warnings | stale_marked | failed

  mode: incremental | targeted | full

  old_map_revision: PKM-00042
  new_map_revision: PKM-00043 | null

  project_revision: def456

  structural_stats:
    added_nodes: 0
    changed_nodes: 0
    removed_nodes: 0
    added_edges: 0
    changed_edges: 0
    removed_edges: 0

  semantic_stats:
    accepted_candidates: 0
    changed_facts: 0
    conflicts_created: 0
    conflicts_resolved: 0

  stale_regions_remaining: []

  maintenance_findings: []

  warnings: []
  errors: []
```

## 11. Refresh propagation policy extension

Relation Registry may include:

```yaml
refresh_policy:
  relation: calls

  on_source_changed:
    invalidate_edge: true
    inspect_target: false

  on_target_changed:
    invalidate_edge: false
    inspect_source: optional

  on_source_deleted:
    remove_edge: true

  on_target_deleted:
    remove_edge: true
    inspect_source: true
```

This allows the affected-region engine to remain generic.

## 12. Design rules

- Refresh always operates against an explicit base map revision.
- Persistence creates a new logical PKM revision.
- Invalidation precedes mutation.
- Partial coverage is explicit.
- Semantic candidates are validated before persistence.
- Conflicts are preserved.
- Derived summaries are regenerated after underlying facts change.
- A stale base revision must trigger rebase/recompute rather than silent overwrite.
