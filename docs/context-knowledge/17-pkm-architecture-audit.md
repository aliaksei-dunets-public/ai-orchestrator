# Project Knowledge Map — Architecture Audit

**Status:** Completed design audit v0.1  
**Scope:** PKM / Context documentation 00–16  
**Audit goal:** Verify architectural consistency, implementation readiness, lifecycle correctness, contract quality, scalability, and failure behavior.

---

## 1. Executive conclusion

The overall PKM architecture is **sound and worth keeping**.

Strong design decisions already in place:

- clear separation of Structural and Semantic knowledge;
- evidence-first design;
- progressive Bootstrap rather than full-repository AI reading;
- Direct Discovery fallback when PKM is unavailable;
- incremental / targeted Refresh;
- semantic candidates rather than direct agent writes;
- explicit conflicts;
- revisioned PKM;
- Health/Audit lifecycle;
- bounded use of expensive models;
- platform adapters separated from PKM core.

However, the architecture is **not yet implementation-ready at the persistence / refresh boundary**.

The audit found several contract-level gaps that should be resolved before building the PKM runtime.

Audit disposition:

```text
ARCHITECTURE
   → APPROVED WITH REQUIRED HARDENING

Bootstrap / adapters / ontology prototypes
   → can proceed

Persistent PKM + Refresh runtime
   → resolve P0 findings first
```

---

## 2. Audit dimensions

The audit covered:

```text
architecture boundaries
data contracts
identity
evidence/provenance
revision model
bootstrap
query
refresh
semantic lifecycle
health/audit
context integration
concurrency
persistence
security/data governance
documentation consistency
implementation readiness
```

---

# 3. Critical findings — P0

## PKM-AUD-001 — Logical identity is not actually stable

**Severity:** Critical  
**Area:** Node identity / Refresh

Current structural design describes `id` as logical identity, but candidate IDs include qualified name/path:

```text
main:python:class:src.payment.service.PaymentService
```

A rename or move changes this value.

Therefore the value is a **natural key**, not a stable logical ID.

### Risk

Rename/move can appear as:

```text
DELETE old node
ADD new node
```

and break:

- semantic links;
- history;
- evidence references;
- graph lineage;
- task-derived knowledge.

### Required correction

Separate:

```yaml
id: immutable PKM entity ID

natural_key:
  repository: main
  qualified_name: ...

fingerprint: ...
```

Recommended:

```text
immutable id
+
current natural key
+
aliases / lineage
+
fingerprint
```

Platform-native stable IDs can be retained as external identity keys.

---

## PKM-AUD-002 — Invalidation-before-refresh conflicts with atomic publication

**Severity:** Critical  
**Area:** Refresh transaction semantics

Refresh currently says:

```text
mark affected knowledge potentially_stale
↓
re-extract
↓
persist atomic update
```

It also says:

```text
if persistence fails, old PKM remains valid
```

Those rules conflict if invalidation modifies the currently published PKM revision.

### Required correction

Invalidation must happen in a **staging transaction / refresh workspace**, not in the published map.

Correct model:

```text
Published PKM N
      │
      ├── create Refresh Workspace
      │
      ▼
staged invalidation
      ↓
re-extraction
      ↓
validation
      ↓
atomic commit
      ↓
Published PKM N+1
```

If refresh fails:

```text
PKM N remains unchanged
```

---

## PKM-AUD-003 — Failed refresh needs state outside the published PKM

**Severity:** Critical  
**Area:** Sync state / Failure handling

Current policy says that after non-critical Refresh failure the system may:

```text
mark affected knowledge stale
create maintenance finding
complete task
```

But if the PKM update itself failed atomically, it cannot safely write the stale marker into that same failed update.

### Required correction

Introduce a separate **Knowledge Sync State / Refresh Journal** owned by Knowledge Map Manager.

Example:

```yaml
knowledge_sync_state:
  project_ref: PROJECT-001

  published_map_revision: PKM-0042
  current_source_revision: SRC-0048

  sync_status: behind

  pending_regions:
    - payment

  failed_refresh_ref: REFRESH-0091
```

Context Router and Health/Audit must consult this state.

---

## PKM-AUD-004 — Evidence references are insufficient for freshness verification

**Severity:** Critical  
**Area:** Evidence / Audit / Semantic trust

Current evidence usually stores:

```yaml
ref: src/payment/service.py
symbol: PaymentService.cancel
```

This does not say **which version** of the evidence supported the fact.

Health/Audit therefore cannot reliably determine whether evidence changed after verification.

### Required correction

Create a canonical `EvidenceRef` contract:

```yaml
evidence:
  source_ref: ...
  source_type: code

  source_revision: SRC-0048

  path: src/payment/service.py
  symbol: PaymentService.cancel

  fingerprint: sha256:...

  locator:
    start: ...
    end: ...
```

Evidence freshness should be evaluated against revision/fingerprint.

---

## PKM-AUD-005 — Knowledge Query is a major capability but has no real contract

**Severity:** Critical  
**Area:** Query / Context Graph B

`Knowledge Query Capability` exists conceptually, but there is no canonical request/result contract.

Context Graph B depends heavily on it.

### Required correction

Define:

```text
Query Request
Query Result
Traversal policy
Layer filters
Relation filters
Depth/budget
Confidence/verification filters
Freshness filters
Evidence expansion
Region health metadata
```

Example capabilities:

```text
resolve entity
neighbors
dependencies
consumers
tests
data access
semantic facts
ADRs/constraints
evidence
```

The Query API should be deterministic and backend-independent.

---

## PKM-AUD-006 — Persistence semantics are under-specified

**Severity:** Critical  
**Area:** Storage / Atomic updates / Concurrency

Storage technology is intentionally deferred, which is reasonable.

But the **storage interface semantics** cannot remain deferred before Refresh implementation.

Required operations include:

```text
get published revision
open read snapshot
open refresh workspace
query
stage delta
validate
commit atomically
abort
checkpoint
compare revisions
```

### Required correction

Define a backend-neutral `PKM Store` contract before choosing SQLite/JSON/etc.

Technology may remain replaceable.

---

## PKM-AUD-007 — Project/source revision semantics are ambiguous

**Severity:** Critical  
**Area:** Git / workspace / Refresh

Many contracts assume:

```yaml
project_revision: abc123
```

but the Development Workflow may be operating on uncommitted changes.

A Git commit ID may not yet exist when Knowledge Refresh runs.

### Required correction

Introduce abstract `SourceRevision`:

```yaml
source_revision:
  type: vcs_commit | workspace_snapshot
  id: ...
  base_commit: ...
  dirty: true | false
  fingerprint: ...
```

Then define where Knowledge Refresh occurs relative to:

```text
implementation
tests
documentation
commit
task completion
```

This is required to make revision-based freshness correct.

---

# 4. High-priority findings — P1

## PKM-AUD-008 — `verified` is mixed into `confidence`

Current contracts use:

```text
verified | high | medium | low | unknown
```

`verified` is not a confidence level.

It is verification state.

### Recommended correction

Separate:

```yaml
verification_status:
  verified | supported | inferred | unverified | conflicted

confidence:
  high | medium | low | unknown
```

This improves semantic policy and audit logic.

---

## PKM-AUD-009 — Status fields mix different dimensions

Structural status:

```text
current
potentially_stale
stale
invalid
```

Semantic status:

```text
candidate
current
potentially_stale
conflicted
superseded
invalid
```

This mixes:

- lifecycle;
- freshness;
- conflict state;
- validity.

### Recommended correction

Prefer orthogonal fields:

```yaml
lifecycle_status:
  candidate | active | superseded | invalid

freshness_status:
  current | potentially_stale | stale

verification_status:
  verified | supported | inferred | conflicted
```

Not every object needs every field, but meanings should not overlap.

---

## PKM-AUD-010 — Context Strategy Router is now outdated

The original router chooses based on:

```text
map available
map freshness
map coverage
```

Later Health policy introduced:

```text
healthy
degraded
unhealthy
critical
unknown
```

including regional health.

These are currently two competing routing policies.

### Recommended correction

Make Health Policy authoritative:

```text
Context Router
   ↓
Knowledge Sync State
+
Regional PKM Health
   ↓
strategy
```

Freshness and coverage become inputs to health, not independent router policies.

---

## PKM-AUD-011 — Bootstrap contains overlapping validation/evidence stages

Top-level Bootstrap includes:

```text
Structural Extraction
Semantic Overview
Evidence Linking
Validation
```

But Structural Extraction and Semantic Overview already perform their own:

```text
evidence linking
validation
```

### Risk

Unclear ownership and duplicate work.

### Recommended correction

Rename/separate levels:

```text
Local Subgraph Validation
      ↓
Bootstrap Integration Validation
```

Top-level bootstrap validation should check:

- cross-layer integrity;
- revision alignment;
- aggregate coverage;
- persistence readiness.

It should not repeat internal extraction validation.

---

## PKM-AUD-012 — Knowledge Map Manager API is inconsistent

Architecture says the manager owns:

```text
Bootstrap
Refresh
Query
Health/Audit
```

but candidate API is:

```text
bootstrap()
refresh()
query()
validate()
rebuild()
```

`audit()` is missing and `validate()` is ambiguous.

### Recommended API

```text
bootstrap()
query()
refresh()
audit()
rebuild()
get_status()
```

`validate()` remains an internal operation used by Bootstrap/Refresh/Audit.

---

## PKM-AUD-013 — Full Refresh and Rebuild are not sufficiently distinguished

Both concepts exist, but their semantic difference is unclear.

### Recommended definition

**Full Refresh**

```text
Re-extract entire current project
while preserving PKM identity/history/lineage.
```

**Rebuild**

```text
Create a new PKM baseline/storage generation
because old representation cannot safely be evolved.
```

Typical rebuild triggers:

- corruption;
- incompatible ontology migration;
- storage migration;
- widespread identity failure.

---

## PKM-AUD-014 — Relation propagation policy is defined too late

Refresh relies on relation-specific propagation:

```text
calls
reads
writes
tests
...
```

A policy example exists in Refresh contracts, but it is not part of the canonical Relation Registry design.

### Recommended correction

Move `refresh_policy` into each Relation Registry entry.

The relation registry should own:

```text
direction
inverse alias
allowed kinds
parent relation
evidence policy
materialization policy
refresh propagation
query behavior
```

---

## PKM-AUD-015 — Semantic coverage percentages have no stable denominator

Structural coverage can often be measured.

Semantic coverage cannot honestly mean:

```text
42% of all semantic truth in the project
```

because the denominator is unknown.

### Recommended correction

Use semantic coverage against an explicit target set:

```text
identified major components covered
identified ADRs indexed
known domain areas represented
expected semantic sources processed
```

Or report:

```text
semantic coverage: partial
known gaps: [...]
```

Avoid false precision.

---

## PKM-AUD-016 — Canonical Evidence / Provenance / Revision primitives are duplicated

Structural, semantic, refresh, and audit contracts independently define similar concepts.

### Risk

Schema drift.

### Recommended correction

Create common PKM Core Contracts:

```text
EntityId
NaturalKey
SourceRevision
EvidenceRef
Provenance
Scope
RegionRef
Verification
Freshness
RevisionMetadata
```

Structural and semantic contracts should reuse these primitives.

---

## PKM-AUD-017 — Security / secret filtering is missing from PKM lifecycle

PKM may inspect:

```text
source code
configuration
CI/CD
runtime logs
documentation
external systems
```

Some sources may contain secrets or restricted data.

### Required design before production

Add:

```text
source classification
exclusion policy
secret filtering
permission-aware adapters
redaction rules
persistence rules
audit logging
```

The PKM should store references/summaries without unnecessarily copying sensitive raw data.

---

## PKM-AUD-018 — Semantic ontology has ambiguous duplicate representations

Examples:

```text
kind = responsibility
```

and:

```text
relation = responsible_for
```

Similarly:

```text
document node ADR
```

versus:

```text
semantic architecture_decision node
```

### Recommended correction

Define representation rules.

Example:

```text
Responsibility as concept node
only when responsibility itself needs identity/evidence/history.

Otherwise use:
StructuralNode --responsible_for--> BusinessConcept
```

For ADR:

```text
Document node = physical ADR artifact
ArchitectureDecision node = decision itself
ArchitectureDecision --documented_by--> ADR document
```

This avoids duplication.

---

## PKM-AUD-019 — Concurrency design needs a concrete merge/rebase contract

Current Refresh correctly rejects last-writer-wins.

But “rebase refresh inputs” is still conceptual.

Before implementation define:

```text
base PKM revision
base SourceRevision
current PKM revision
current SourceRevision
overlap detection
delta replay
semantic conflict handling
retry bounds
```

---

## PKM-AUD-020 — Region is used heavily but not defined

Audit, Health, Refresh and Context all refer to:

```text
region
affected region
stale region
component region
```

There is no canonical `RegionRef`.

### Recommended correction

Define region as a queryable scope selector, e.g.:

```yaml
region:
  id: ...
  type: repository | module | package | path_prefix | component | semantic_domain
  selector: ...
```

Regions should be derived/grouping constructs, not necessarily persistent graph nodes.

---

## PKM-AUD-021 — Ontology and adapter migrations need explicit version behavior

Versions are recorded, but migration behavior is not defined.

Need policies for:

```text
compatible adapter upgrade
incompatible adapter upgrade
core ontology minor change
core ontology breaking change
extension removal
relation rename
```

These policies determine:

```text
no action
targeted re-extraction
full refresh
migration
rebuild
```

---

## PKM-AUD-022 — Documentation is split across two physical spec directories

Current artifacts exist in:

```text
orchestrator-context-knowledge-spec/
orchestrator-context-knowledge-spec-v2/
```

The master spec logically references one document set.

### Recommended correction

Before repository transfer, consolidate into a single canonical directory and mark old versions as superseded.

Example:

```text
docs/pkm/
  00-master.md
  01-...
  ...
```

---

# 5. Medium findings — P2

## PKM-AUD-023 — Relation inheritance needs explicit query semantics

Extension relations may specify:

```yaml
parent_relation: depends_on
```

Define whether this means:

```text
query-time entailment only
```

or materialized duplicate edge.

Recommendation: query-time entailment only.

---

## PKM-AUD-024 — `contains` vs `declares` requires sharper semantics

Recommended:

```text
contains = physical/logical ownership hierarchy
declares = artifact defines a symbol/contract
```

Do not emit both unless both relationships are meaningful.

---

## PKM-AUD-025 — S2 enrichment needs an explicit entry path

S2 is designed as lazy/targeted but there is no explicit flow.

Recommended:

```text
Context detects insufficient structural detail
      ↓
Knowledge Enrichment Request
      ↓
Targeted Structural Extraction S2
      ↓
Refresh validation/persistence
```

This can be implemented as a targeted Refresh mode rather than a new top-level subsystem.

---

## PKM-AUD-026 — Audit remediation can create recursive loops

Example:

```text
Audit
→ Targeted Refresh
→ Audit
→ Targeted Refresh
...
```

Add bounded remediation execution:

```yaml
max_auto_remediation_cycles: 1
```

Further unresolved findings become maintenance tasks.

---

## PKM-AUD-027 — Audit sampling should be reproducible

Deep/standard audits sample source-vs-map facts.

Record:

```text
sampling strategy
seed
population definition
sample size
risk weighting
```

This makes audits comparable over time.

---

## PKM-AUD-028 — Multi-repository edge ownership needs clarification

An edge can connect entities in different repositories.

A single:

```yaml
repository_ref:
```

on an edge may become misleading.

Recommendation:

- project-level edge ownership;
- source/target nodes carry repository identity;
- optional `scope_ref`.

---

## PKM-AUD-029 — Snapshot/delta retention is not defined

Revisioned PKM will accumulate history.

Eventually define:

```text
snapshot cadence
delta retention
compaction
semantic history retention
audit log retention
```

Not required for architecture prototype, but required before large-scale operation.

---

## PKM-AUD-030 — Derived summaries need dependency fingerprints

`derived_from` IDs are useful but not enough.

Store the revision/fingerprint of inputs so stale summaries can be invalidated cheaply.

---

# 6. Cross-cutting correction model

The audit suggests introducing a compact common core:

```text
PKM CORE CONTRACTS
│
├── Entity Identity
├── Natural Key
├── Source Revision
├── Evidence Reference
├── Provenance
├── Scope / Region
├── Verification
├── Freshness
└── Revision Metadata
```

Then:

```text
Structural Contract
Semantic Contract
Query Contract
Refresh Contract
Audit Contract
```

all reuse the same primitives.

This will substantially reduce schema drift.

---

# 7. Recommended target architecture after remediation

```text
                         PROJECT SOURCES
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
         Direct Discovery                PKM Adapters
                                               │
                                               ▼
                                      Knowledge Map Manager
                                               │
                   ┌──────────────┬────────────┼──────────────┐
                   ▼              ▼            ▼              ▼
               Bootstrap         Query       Refresh          Audit
                   │              │            │              │
                   └──────────────┴─────┬──────┴──────────────┘
                                        ▼
                                   PKM Store API
                                        │
                           ┌────────────┴────────────┐
                           ▼                         ▼
                    Published Revision         Refresh Workspace
                           │                         │
                           └────────────┬────────────┘
                                        ▼
                              Knowledge Sync State
```

Context Router consumes:

```text
Query capability
+
regional Health
+
Knowledge Sync State
```

rather than raw “map exists” state.

---

# 8. Audit verdict by subsystem

| Subsystem | Verdict |
|---|---|
| Overall PKM concept | Strong |
| Context fallback model | Strong |
| Bootstrap strategy | Strong |
| Structural extraction | Strong, identity contract needs correction |
| Ontology | Strong, registry needs propagation semantics |
| Semantic layer | Strong, metadata model needs normalization |
| Refresh | Good architecture, transaction semantics must be fixed |
| Health/Audit | Strong, coverage/region semantics need refinement |
| Query | Under-specified |
| Persistence | Under-specified |
| Security/data governance | Missing |
| Documentation/versioning | Needs consolidation |

---

# 9. Implementation readiness

### Safe to prototype now

```text
Project Discovery
Source Discovery
Project Index
adapter interfaces
Structural Extraction adapters
ontology registry
semantic candidate extraction
Direct Context Discovery
```

### Resolve P0 first

```text
persistent Node/Edge storage
Knowledge Query runtime
atomic Refresh
revision synchronization
concurrent Refresh
production semantic persistence
```

---

# 10. Final audit conclusion

No redesign of the main PKM idea is required.

The architecture should **not** be replaced.

The required work is mostly contract hardening around:

```text
identity
evidence
revision
query
transaction/persistence
sync state
```

After those points are resolved, the design is suitable to move from conceptual architecture into implementation planning.
