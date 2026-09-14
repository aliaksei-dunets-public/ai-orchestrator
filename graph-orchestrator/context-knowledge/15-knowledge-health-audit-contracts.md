# Knowledge Health / Audit Contracts

**Status:** Candidate normalized contracts v0.1

## 1. Audit Request

```yaml
audit_request:
  project_ref: PROJECT-001

  mode: quick | standard | deep | targeted

  map_revision: PKM-00043

  scope:
    regions: []
    nodes: []
    semantic_concepts: []

  checks:
    structural_integrity: true
    freshness: true
    coverage: true
    evidence: true
    semantic_quality: true
    conflicts: true
    adapters: true
    refresh_pipeline: true
    derived_artifacts: true

  budget:
    max_sample_size: 200
    max_semantic_checks: 50
    model_profile_ceiling: standard
```

## 2. Health Dimension Result

```yaml
health_dimension:
  id: freshness

  score: 0.87

  status: healthy | degraded | unhealthy | critical | unknown

  checks_run: 12
  checks_failed: 2
  checks_skipped: 0

  findings:
    - PKM-F-0042
```

## 3. Coverage Report

```yaml
coverage_report:
  project_index: 1.00

  structural:
    first_party: 0.96
    api: 0.98
    data_access: 0.91
    tests: 0.84
    documentation_links: 0.76

  semantic:
    overview: 0.42
    evidence_ratio: 0.89

  excluded:
    generated: true
    vendor: true

  gaps:
    - region: src/plugins
      type: structural
      severity: medium
```

## 4. Freshness Report

```yaml
freshness_report:
  project_revision: def456
  map_project_revision: def456

  stale:
    nodes: 3
    edges: 12
    semantic_facts: 5
    summaries: 2

  potentially_stale:
    nodes: 9
    semantic_facts: 7

  regions:
    - id: payment
      status: current

    - id: plugins
      status: stale
```

## 5. Adapter Health

```yaml
adapter_health:
  adapter_id: sap-rap
  version: 1.2

  status: healthy | degraded | failed | unknown

  last_successful_revision: def456

  coverage_status: complete | partial | failed

  diagnostics:
    warnings: []
    errors: []

  affected_regions: []
```

## 6. Refresh Pipeline Health

```yaml
refresh_pipeline_health:
  recent_runs: 20

  success: 17
  success_with_warnings: 2
  failed: 1

  recurring_stale_regions:
    - src/plugins

  full_refresh_escalations: 1

  persistence_failures: 0

  status: degraded
```

## 7. Finding

```yaml
finding:
  id: PKM-F-0042

  category:
    structural_integrity | freshness | coverage | evidence | semantic_quality | conflict | adapter | refresh_pipeline | derived_artifact

  severity:
    info | low | medium | high | critical

  title: string
  summary: string

  affected:
    regions: []
    nodes: []
    edges: []
    semantic_facts: []

  evidence: []

  confidence:
    high | medium | low

  auto_remediation_safe: false

  remediation:
    action:
      no_action | regenerate_derived_artifact | targeted_refresh | incremental_refresh | full_refresh | rebuild_map | manual_review | create_maintenance_task

    target_scope: {}
```

## 8. Semantic Conflict Health Record

```yaml
conflict_health:
  conflict_ref: CONFLICT-0001

  status:
    tracked | stale | newly_detected | resolved | unresolved

  severity: medium

  impact:
    context_risk: high
    implementation_risk: medium

  recommended_action: manual_review
```

## 9. Audit Metrics

```yaml
audit_metrics:
  integrity:
    score: 1.00
    status: healthy

  freshness:
    score: 0.91
    status: healthy

  coverage:
    score: 0.84
    status: degraded

  evidence:
    score: 0.93
    status: healthy

  semantic_quality:
    score: 0.78
    status: degraded

  conflict_health:
    score: 0.90
    status: healthy

  adapter_health:
    score: 0.88
    status: degraded

  refresh_health:
    score: 0.95
    status: healthy
```

## 10. Remediation Plan

```yaml
remediation_plan:
  overall_action: targeted_refresh

  actions:
    - id: REM-001
      priority: 1
      action: targeted_refresh
      scope:
        region: src/plugins

      reason_refs:
        - PKM-F-0042

      automatic: true

    - id: REM-002
      priority: 2
      action: manual_review

      reason_refs:
        - PKM-F-0043

      automatic: false
```

## 11. Audit Result

```yaml
audit_result:
  project_ref: PROJECT-001
  map_revision: PKM-00043

  mode: standard

  execution_status:
    complete | partial | failed

  health_status:
    healthy | degraded | unhealthy | critical | unknown

  metrics_ref: AUDIT-METRICS-0043

  findings:
    info: 2
    low: 3
    medium: 2
    high: 1
    critical: 0

  remediation_plan_ref: REM-PLAN-0043

  context_policy:
    recommended_strategy:
      knowledge_assisted | hybrid | direct_discovery

  warnings: []
  errors: []
```

## 12. Maintenance Finding

When remediation is deferred:

```yaml
maintenance_finding:
  id: MAINT-0042

  source: pkm_audit
  finding_ref: PKM-F-0042

  priority: medium

  suggested_task:
    type: maintenance
    objective: >
      Repair stale Project Knowledge Map coverage
      for the plugin integration region.
```

## 13. Design rules

- audit execution status is separate from PKM health status;
- `unknown` is preferred over false confidence;
- critical integrity failures can override aggregate scores;
- findings always include evidence and remediation;
- known intentional exclusions do not reduce coverage;
- conflicts are tracked, not automatically erased;
- remediation plans are explicit artifacts.
