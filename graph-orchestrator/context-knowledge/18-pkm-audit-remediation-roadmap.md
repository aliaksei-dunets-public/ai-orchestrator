# PKM Audit Remediation Roadmap

**Status:** Proposed remediation order v0.1  
**Source:** `17-pkm-architecture-audit.md`

## Goal

Resolve the audit findings in dependency order before implementing the persistent PKM runtime.

---

## Phase A — Core contracts

### A1. Canonical Identity model

Resolve:

- PKM-AUD-001
- PKM-AUD-019
- PKM-AUD-028

Define:

```text
immutable EntityId
NaturalKey
Alias / Lineage
Fingerprint
Repository identity
```

### A2. Source Revision model

Resolve:

- PKM-AUD-007
- part of PKM-AUD-019

Define:

```text
VCS commit revision
workspace snapshot revision
revision ancestry
content fingerprint
```

### A3. Evidence / Provenance model

Resolve:

- PKM-AUD-004
- PKM-AUD-008
- PKM-AUD-016
- PKM-AUD-030

Define:

```text
EvidenceRef
Provenance
VerificationStatus
Confidence
Evidence fingerprint/revision
```

### A4. Status model

Resolve:

- PKM-AUD-009

Define orthogonal:

```text
lifecycle
freshness
verification/conflict
```

### A5. Scope / Region model

Resolve:

- PKM-AUD-020
- PKM-AUD-028

Define:

```text
ScopeRef
RegionRef
cross-repository scope
```

---

## Phase B — Query and storage boundary

### B1. Knowledge Query contract

Resolve:

- PKM-AUD-005
- PKM-AUD-023

Define:

```text
resolve entity
traverse graph
relation filters
semantic filters
health/freshness filters
evidence expansion
query budgets
extension relation entailment
```

### B2. PKM Store contract

Resolve:

- PKM-AUD-006
- PKM-AUD-002
- PKM-AUD-003

Define:

```text
read snapshot
refresh workspace
stage delta
atomic commit
abort
checkpoint
revision comparison
query access
```

### B3. Knowledge Sync State

Resolve:

- PKM-AUD-003
- PKM-AUD-010

Define state outside published map:

```text
published revision
current source revision
sync status
pending/stale regions
failed refresh journal
```

---

## Phase C — Refresh hardening

### C1. Transaction semantics

Resolve:

- PKM-AUD-002

Make invalidation staged, not published.

### C2. Relation propagation registry

Resolve:

- PKM-AUD-014
- PKM-AUD-024

Move refresh propagation into canonical relation definitions.

### C3. Full Refresh vs Rebuild

Resolve:

- PKM-AUD-013
- PKM-AUD-021

Define lifecycle behavior and migration policy.

### C4. Concurrent refresh

Resolve:

- PKM-AUD-019

Define rebase / overlap / conflict algorithm.

---

## Phase D — Context integration

### D1. Replace legacy Context Strategy policy

Resolve:

- PKM-AUD-010

New router inputs:

```text
Knowledge Sync State
Regional PKM Health
Task/context scope
PKM availability
```

### D2. Lazy S2 enrichment

Resolve:

- PKM-AUD-025

Use targeted Refresh with requested structural depth.

---

## Phase E — Semantic cleanup

### E1. Semantic representation rules

Resolve:

- PKM-AUD-018

Clarify:

```text
responsibility node vs responsible_for edge
ADR document vs ArchitectureDecision semantic node
constraint vs domain rule
assumption vs inferred fact
```

### E2. Semantic coverage

Resolve:

- PKM-AUD-015

Replace unknown-denominator percentages with explicit target coverage / known gaps.

---

## Phase F — Health/Audit hardening

### F1. Audit remediation bounds

Resolve:

- PKM-AUD-026

Define:

```yaml
max_auto_remediation_cycles: 1
```

### F2. Reproducible sampling

Resolve:

- PKM-AUD-027

Record audit sampling policy and seed.

### F3. Derived artifact fingerprints

Resolve:

- PKM-AUD-030

---

## Phase G — Security and governance

Resolve:

- PKM-AUD-017

Define:

```text
source permissions
secret exclusion
redaction
raw-content persistence rules
sensitive-source classification
audit trail
```

This should be completed before production use of external/runtime/config sources.

---

## Phase H — Documentation consolidation

Resolve:

- PKM-AUD-011
- PKM-AUD-012
- PKM-AUD-022

Actions:

1. consolidate all PKM specs into one directory;
2. establish one canonical master spec;
3. add `supersedes` metadata to replaced docs;
4. distinguish local validation from integration validation;
5. normalize Knowledge Map Manager API.

---

## Recommended implementation gate

Do not begin persistent PKM runtime implementation until:

```text
Phase A complete
Phase B complete
C1 transaction semantics complete
```

Adapter/static-analysis prototypes may continue in parallel.

---

## Suggested immediate design sequence

```text
1. Core Contracts
2. Query Contract
3. PKM Store / Transaction Contract
4. Sync State
5. Refresh rewrite against those contracts
6. Context Router alignment
7. Semantic cleanup
8. Audit cleanup
9. Security/governance
10. Documentation consolidation
```
