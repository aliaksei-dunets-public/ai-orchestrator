# Knowledge Health / Audit Subgraph

**Status:** Detailed design draft v0.1  
**Scope:** Project Knowledge Map integrity, freshness, coverage, and quality audit

## 1. Purpose

`Knowledge Health / Audit` determines whether the Project Knowledge Map can be trusted as an efficient navigation and context-acceleration layer.

The audit does not ask:

> Is the project itself good?

It asks:

> Is the PKM sufficiently correct, fresh, complete, internally consistent, and evidence-backed for continued use?

The audit must identify problems and recommend remediation without unnecessarily rebuilding the entire map.

---

## 2. Audit is a reusable subgraph

```text
AUDIT REQUEST
      │
      ▼
1. RESOLVE AUDIT SCOPE
      │
      ▼
2. LOAD PKM METADATA
      │
      ▼
3. SAMPLE / VERIFY PROJECT STATE
      │
      ▼
4. RUN STRUCTURAL INTEGRITY CHECKS
      │
      ▼
5. RUN FRESHNESS CHECKS
      │
      ▼
6. RUN COVERAGE CHECKS
      │
      ▼
7. RUN SEMANTIC QUALITY CHECKS
      │
      ▼
8. RUN ADAPTER / PIPELINE CHECKS
      │
      ▼
9. RUN CONFLICT / DRIFT CHECKS
      │
      ▼
10. CALCULATE HEALTH METRICS
      │
      ▼
11. CLASSIFY FINDINGS
      │
      ▼
12. SELECT REMEDIATION
      │
      ▼
AUDIT REPORT
```

Most checks should be deterministic.

---

## 3. Audit modes

```yaml
mode:
  enum:
    - quick
    - standard
    - deep
    - targeted
```

### Quick

Cheap checks for frequent use:

- revision alignment;
- broken refs;
- stale markers;
- failed adapters;
- unresolved refresh errors;
- basic coverage metadata.

### Standard

Recommended periodic/default audit:

- quick checks;
- evidence sampling;
- structural coverage checks;
- semantic confidence/freshness checks;
- conflict analysis;
- adapter health;
- derived-summary validation.

### Deep

Expensive and rare:

- broad source-vs-map sampling;
- wider semantic cross-check;
- comprehensive relation verification;
- suspicious-region expansion;
- map drift estimation.

### Targeted

Checks only a requested component/region/finding.

---

## 4. Audit triggers

Audit may run:

- after Bootstrap;
- after full refresh;
- after repeated refresh warnings;
- on health-check command;
- on project onboarding;
- periodically;
- when Context detects suspicious PKM information;
- after adapter/ontology upgrades;
- after large merges/migrations;
- when stale coverage crosses policy thresholds.

---

## 5. Audit scope

```yaml
audit_scope:
  project_ref: PROJECT-001

  mode: standard

  regions:
    - all

  checks:
    structural_integrity: true
    freshness: true
    coverage: true
    semantic_quality: true
    adapters: true
    conflicts: true
    evidence: true
```

Targeted example:

```yaml
audit_scope:
  mode: targeted

  nodes:
    - PaymentService

  semantic_concepts:
    - PaymentCancellation
```

---

## 6. Structural integrity checks

Deterministic checks:

### Broken references

```text
edge source missing
edge target missing
evidence ref missing
summary references missing fact
```

### Duplicate identities

Detect:

- two logical nodes with same platform ID;
- duplicate qualified symbol identity;
- suspicious duplicate path/symbol pairs.

### Ontology violations

Detect:

- unregistered relations;
- invalid source/target kind combinations;
- invalid subtype mappings;
- unsupported extension versions.

### Invalid revision state

Detect:

- node newer than map revision;
- edge verified against unrelated project revision;
- impossible revision ancestry.

### Orphans

Potentially suspicious:

- tests with no target;
- semantic concepts with no links;
- documents indexed but disconnected;
- source entities with no repository/container ancestry.

Not every orphan is an error, so severity depends on type.

---

## 7. Freshness checks

Freshness answers:

> Is this knowledge likely to reflect the current project?

Checks:

- PKM project revision vs repository revision;
- stale/potentially_stale counts;
- last verification age;
- changed source evidence after last verification;
- adapter version changes;
- ontology version changes;
- unprocessed refresh triggers;
- failed refresh regions.

Example:

```yaml
freshness:
  current_project_revision: def456
  map_project_revision: def450

  revision_gap_detected: true
```

Freshness should be region-aware, not just global.

---

## 8. Coverage checks

Coverage is not simply:

```text
indexed files / all files
```

Useful coverage dimensions:

```text
project_index
structural_entities
dependency_relations
api_contracts
data_access
tests
documentation
semantic_overview
semantic_evidence
```

Coverage should be weighted by importance.

Generated/vendor code may be intentionally excluded and must not reduce health.

Example:

```yaml
coverage:
  structural:
    overall: 0.91
    first_party: 0.96
    excluded: 0.18

  api: 0.98
  tests: 0.84
  semantic: 0.42
```

Semantic coverage can be intentionally much lower than structural coverage.

---

## 9. Coverage gap detection

Examples:

- a first-party source directory has no indexed nodes;
- API endpoints exist in source but not PKM;
- test directory indexed but test relations absent;
- data layer exists but no read/write relationships;
- architecture docs exist but no semantic knowledge extracted;
- new module added after last map refresh.

Coverage gaps produce explicit findings.

---

## 10. Evidence quality checks

Semantic and important structural facts should be evidence-backed.

Checks:

- high-confidence fact with no evidence;
- evidence path no longer exists;
- evidence changed after last verification;
- AI inference marked high without corroboration;
- relation supported only by weak heuristic;
- conflicting evidence not reflected in status.

Candidate metric:

```text
evidence_ratio =
facts_with_valid_evidence / facts_requiring_evidence
```

---

## 11. Semantic quality checks

Check for:

- low-confidence clusters;
- stale semantic facts;
- unresolved candidates;
- outdated ADR links;
- unsupported business rules;
- semantic nodes disconnected from structural evidence;
- duplicate concepts;
- superseded facts still marked current;
- assumptions promoted to facts accidentally.

Semantic quality is not measured by quantity.

A small, well-evidenced semantic layer is preferable to a large speculative one.

---

## 12. Conflict checks

Conflicts are legitimate PKM content, but unresolved conflicts affect health.

Types:

```text
documentation vs code
ADR vs current implementation
semantic fact vs structural evidence
two documents disagree
two workflow discoveries disagree
```

Audit distinguishes:

```text
known_conflict
new_conflict
stale_conflict
resolved_but_not_closed
```

Known and properly tracked conflicts are less severe than silent contradictions.

---

## 13. Derived artifact checks

Derived artifacts include:

- component summaries;
- cached neighborhoods;
- materialized indexes;
- context hints;
- health metrics.

Audit checks whether dependencies changed since derivation.

Example:

```text
SEM-004 changed
      ↓
Component Summary still references old revision
      ↓
summary = stale
```

Derived artifacts can usually be regenerated rather than manually repaired.

---

## 14. Adapter health checks

Each adapter should expose diagnostics.

Audit checks:

- adapter available;
- compatible version;
- last successful run;
- parse failures;
- partial coverage;
- unsupported language/framework region;
- excessive unresolved symbols;
- repeated extraction warnings.

Example:

```yaml
adapter_health:
  adapter: sap-rap
  status: degraded

  unresolved:
    - 12 service bindings

  last_successful_revision: abc120
```

Adapter failure should map to affected PKM regions.

---

## 15. Refresh pipeline health

Audit evaluates Refresh history.

Checks:

- repeated `success_with_warnings`;
- stale regions surviving multiple refreshes;
- frequent full-refresh escalation;
- invalidation not resolved;
- refresh based on stale base revisions;
- persistence retries/failures;
- refresh duration/cost anomalies.

These can indicate architecture or adapter problems rather than project problems.

---

## 16. Project-vs-map sampling

Standard/deep audit should verify a sample of PKM facts directly against current sources.

Examples:

```text
sample nodes
sample calls
sample reads/writes
sample test links
sample semantic facts
```

Sampling strategy should favor:

- high-impact entities;
- recently changed entities;
- high-confidence semantic facts;
- stale-risk regions;
- low-coverage areas.

This detects silent drift that metadata alone cannot reveal.

---

## 17. Health dimensions

Recommended top-level dimensions:

```text
integrity
freshness
coverage
evidence
semantic_quality
conflict_health
adapter_health
refresh_health
```

Each dimension produces:

```yaml
score: 0.0 - 1.0
status: healthy | degraded | unhealthy | unknown
```

Do not rely on one global score alone.

---

## 18. Global health status

Suggested aggregation:

```text
healthy
degraded
unhealthy
critical
unknown
```

Rules should be policy-based.

Example:

```text
broken referential integrity → unhealthy/critical
small semantic coverage gap → degraded or healthy
one stale low-value doc → healthy/degraded
widespread project revision drift → unhealthy
map corruption → critical
```

Critical dimensions may override aggregate averages.

---

## 19. Finding severity

```text
info
low
medium
high
critical
```

Every finding should include:

- category;
- severity;
- affected region;
- evidence;
- confidence;
- remediation;
- whether automatic repair is safe.

---

## 20. Finding examples

```yaml
finding:
  id: PKM-F-0042

  category: stale_region
  severity: high

  summary: >
    Payment module structural graph is based on an older repository revision.

  affected:
    - src/payment

  evidence:
    - current_revision: def456
    - last_verified_revision: abc123

  remediation:
    action: targeted_refresh
```

---

## 21. Remediation decision

Audit recommendations:

```text
no_action
regenerate_derived_artifact
targeted_refresh
incremental_refresh
full_refresh
rebuild_map
manual_review
create_maintenance_task
```

Default principle:

> Choose the smallest safe remediation.

Examples:

```text
stale component summary
→ regenerate summary

one module stale
→ targeted refresh

large revision drift
→ incremental/full refresh

ontology incompatibility
→ rebuild/migration

semantic conflict
→ manual review or targeted semantic refresh
```

---

## 22. Auto-remediation

Only safe operations should run automatically.

Good candidates:

- regenerate summaries;
- remove invalid caches;
- targeted structural refresh for clearly stale region;
- re-run failed deterministic adapter;
- mark invalid refs stale;
- update health metadata.

Require explicit policy/human approval for:

- deleting large semantic regions;
- rebuilding whole PKM;
- resolving semantic conflicts;
- overwriting verified facts;
- ontology migrations with data loss.

---

## 23. Integration with orchestrator Health Check

The PKM audit is a specialized subgraph that can be called by the wider orchestrator `health-check` capability.

```text
ORCHESTRATOR HEALTH CHECK
      │
      ├── configuration health
      ├── graph/workflow health
      ├── skills health
      ├── task-manager health
      └── PKM HEALTH / AUDIT
```

This avoids duplicating PKM logic inside the general orchestrator audit.

---

## 24. Context behavior under degraded health

Context Strategy Router should inspect PKM health.

```text
PKM healthy
   → Knowledge-Assisted Context

PKM degraded
   → Knowledge-Assisted + direct verification

PKM unhealthy
   → Direct Discovery first

PKM critical
   → disable PKM query except diagnostics
```

This is an important safety boundary.

---

## 25. Model policy

| Check | Policy |
|---|---|
| Referential integrity | deterministic |
| Revision/freshness | deterministic |
| Coverage | deterministic |
| Evidence existence | deterministic |
| Adapter health | deterministic |
| Refresh health | deterministic |
| Semantic contradiction | standard |
| Architecture/doc conflict interpretation | standard → expert |
| Finding summarization | cheap |
| Remediation routing | deterministic-first |

---

## 26. Audit frequency

Candidate policy:

### Event-driven

Run targeted/quick audit after:

- Bootstrap;
- full refresh;
- adapter upgrade;
- ontology upgrade;
- failed refresh;
- suspicious Context finding.

### Periodic

Configurable, e.g.:

```text
quick   → frequent
standard → less frequent
deep    → rare/on demand
```

The architecture should not hard-code calendar frequency.

---

## 27. Performance / cost controls

Audit should support budgets:

```yaml
budget:
  max_sample_size: 200
  max_semantic_checks: 50
  max_runtime: TBD
  model_profile_ceiling: standard
```

Deep audit may override limits explicitly.

---

## 28. Checkpoints

Recommended artifacts:

```text
Audit Scope
Integrity Results
Freshness Results
Coverage Results
Evidence Results
Semantic Results
Adapter Results
Refresh Pipeline Results
Health Metrics
Finding Set
Remediation Plan
Audit Report
```

Audit is resumable.

---

## 29. Failure policy

Audit failure does not automatically mean PKM is unhealthy.

Possible result:

```text
audit incomplete
```

The system distinguishes:

```text
PKM problem
vs
audit execution problem
```

If critical checks could not run, global health may become `unknown` rather than falsely `healthy`.

---

## 30. Accepted design decisions

1. PKM Health/Audit is a reusable subgraph.
2. Quick, standard, deep, and targeted modes are supported.
3. Health is multi-dimensional, not one score.
4. Critical dimensions may override aggregate score.
5. Coverage is weighted and scope-aware.
6. Known conflicts are preserved and evaluated separately from silent contradictions.
7. Adapter and Refresh pipeline health are first-class.
8. Audit samples current project evidence to detect silent drift.
9. Remediation chooses the smallest safe action.
10. Context behavior changes according to PKM health.
11. PKM Audit plugs into the general orchestrator Health Check.
12. Audit failure and PKM failure are distinct states.
