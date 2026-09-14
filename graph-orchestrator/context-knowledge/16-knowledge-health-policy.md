# Project Knowledge Map Health Policy

**Status:** Policy draft v0.1  
**Scope:** Health thresholds, routing, remediation, and Context behavior

## 1. Purpose

This policy defines how health findings influence:

- PKM trust;
- Context Strategy routing;
- refresh selection;
- maintenance actions;
- blocking/non-blocking behavior.

The exact numeric thresholds remain configurable.

---

## 2. Health dimensions

Required dimensions:

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

No single score replaces individual dimensions.

---

## 3. Suggested statuses

```text
healthy
degraded
unhealthy
critical
unknown
```

### Healthy

PKM can be used normally.

### Degraded

PKM remains useful but important claims may require direct verification.

### Unhealthy

PKM should not be trusted as the primary navigation source for affected regions.

### Critical

PKM integrity may be compromised. Query use should be restricted to diagnostics.

### Unknown

Audit could not establish health reliably.

---

## 4. Critical override conditions

Regardless of aggregate score, examples that may force `critical`:

- corrupted persistence;
- revision ancestry impossible;
- widespread dangling edge endpoints;
- ontology/storage incompatibility preventing correct interpretation;
- atomic-update failure exposing partial revision;
- severe identity collisions affecting large graph regions.

---

## 5. Context Strategy policy

```text
HEALTHY
  → Knowledge-Assisted Discovery

DEGRADED
  → Hybrid:
     PKM seed + direct verification

UNHEALTHY
  → Direct Discovery primary
     PKM only as hints/diagnostics

CRITICAL
  → Disable normal PKM-assisted context

UNKNOWN
  → Conservative Hybrid or Direct Discovery
```

This policy may also apply per region.

Example:

```text
Global PKM healthy
Payment region degraded
Plugin region unhealthy
```

Context chooses strategy for the region it needs.

---

## 6. Remediation hierarchy

Always prefer the smallest safe operation:

```text
regenerate derived artifact
        ↓
targeted refresh
        ↓
incremental refresh
        ↓
full refresh
        ↓
map rebuild
```

`manual_review` may occur at any level for semantic ambiguity.

---

## 7. Auto-remediation policy

Safe by default:

```text
regenerate summaries
clear stale cache/index
rerun deterministic adapter
targeted refresh of clearly bounded stale region
mark known invalid evidence stale
```

Approval/policy gate recommended:

```text
full rebuild
ontology migration
large semantic deletion
verified-fact replacement
automatic conflict resolution
large-scale identity merge
```

---

## 8. Blocking policy

PKM issues normally do not block unrelated development work.

### Non-blocking examples

- semantic coverage low;
- one stale documentation relation;
- derived summary stale;
- one adapter degraded in unrelated module.

### Potentially blocking examples

- PKM required by an explicit workflow policy;
- high-risk task depends on a critically unhealthy PKM region and direct verification is unavailable;
- persistent map corruption threatens further writes;
- audit detects revision mismatch that makes refresh unsafe.

---

## 9. Audit mode selection

Candidate defaults:

```text
after bootstrap          → standard
after incremental refresh → quick
after full refresh       → standard
after refresh failure    → targeted/standard
after adapter upgrade    → targeted/standard
after ontology migration → deep
manual health check      → standard
suspected corruption     → deep
```

---

## 10. Coverage policy

Coverage is weighted.

High-priority areas:

```text
first-party source
public APIs
data access
tests
architecture docs
active modules
recently changed regions
```

Low-priority/excluded:

```text
generated code
vendor code
third-party library internals
archived docs
disabled modules
```

Semantic coverage does not need to approach 100%.

---

## 11. Freshness policy

Freshness is region-sensitive.

A stale low-value region should not downgrade the whole PKM as strongly as:

```text
stale active core module
stale public API mapping
stale data model
stale architecture constraints
```

Recent project changes receive higher audit priority.

---

## 12. Evidence policy

Candidate rules:

```text
verified/high semantic fact
  → must have valid evidence

AI inference
  → may be medium/low until corroborated

high-confidence semantic fact
with missing evidence
  → audit finding high

structural edge from exact parser metadata
  → may use extractor evidence directly
```

---

## 13. Conflict policy

Conflicts are not automatically health failures.

```text
tracked + scoped + surfaced conflict
  → acceptable/degraded

silent contradiction
  → unhealthy finding

conflict affecting critical contract
  → high/critical severity
```

---

## 14. Adapter policy

One failed adapter should downgrade only its affected region when possible.

Example:

```text
Python adapter healthy
Docs adapter healthy
SAP adapter degraded
```

Do not mark the entire PKM unhealthy if the SAP region is irrelevant to the current project scope.

---

## 15. Refresh escalation policy

Examples:

```text
small stale region
→ targeted refresh

several independent stale regions
→ incremental refresh

large ancestry/revision drift
→ full refresh

storage/ontology incompatibility
→ migration or rebuild
```

---

## 16. Maintenance task creation

Audit may recommend a managed task when repair should not run automatically.

Example:

```yaml
task:
  type: maintenance

  objective: >
    Repair Project Knowledge Map extraction for the plugin subsystem.

  source:
    type: pkm_audit
    finding_ref: PKM-F-0042
```

This allows PKM maintenance to enter the same orchestrator workflow model.

---

## 17. Observability policy

Track over time:

```text
health trend
coverage trend
stale-region count
conflict count
adapter failure rate
refresh warning rate
full-refresh frequency
audit duration
audit cost
```

A degrading trend can trigger proactive maintenance before the map becomes unhealthy.

---

## 18. Initial threshold guidance

Exact thresholds remain configurable, but candidate semantics:

```text
healthy
  no integrity failures
  freshness acceptable
  high-value coverage strong

degraded
  limited gaps/staleness
  safe fallback exists

unhealthy
  broad stale/coverage/evidence issues
  PKM cannot safely guide primary discovery

critical
  map integrity/storage/revision correctness compromised
```

Avoid overfitting early architecture to arbitrary percentages.

---

## 19. Accepted decisions

1. Health is regional as well as global.
2. Context routing consumes PKM health.
3. Smallest-safe-remediation is the default.
4. Auto-remediation is limited to reversible, deterministic operations.
5. PKM problems usually do not block unrelated development.
6. Audit modes depend on trigger and risk.
7. Coverage is weighted, not raw file percentage.
8. Conflicts are valid knowledge when explicitly tracked.
9. Adapter failures are scoped.
10. Health trend is useful for proactive maintenance.
