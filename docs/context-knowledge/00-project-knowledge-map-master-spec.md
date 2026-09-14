# Project Knowledge Map — Master Specification

**Status:** Consolidated draft v0.3  
**Scope:** Project Knowledge Map lifecycle for the AI Orchestrator

## 1. Purpose

The Project Knowledge Map (PKM) is a reusable project-level capability that helps AI workflows understand and navigate a software project efficiently.

The PKM is not a replacement for source code, project documentation, runtime evidence, or other authoritative sources.

Its role is to provide:

- navigation;
- dependency knowledge;
- semantic knowledge;
- evidence references;
- impact-analysis support;
- context acceleration;
- incremental project memory;
- quality and freshness visibility.

## 2. Core architecture

```text
PROJECT KNOWLEDGE MAP
│
├── BOOTSTRAP
│     Initial project understanding
│
├── QUERY
│     Context/navigation access
│
├── REFRESH
│     Incremental/targeted/full update
│
└── HEALTH / AUDIT
      Integrity, freshness, coverage, conflicts
```

A logical `Knowledge Map Manager` exposes these capabilities.

```text
Knowledge Map Manager
│
├── Bootstrap Subgraph
├── Query Capability
├── Refresh Subgraph
└── Health/Audit Subgraph
```

## 3. Knowledge layers

```text
PROJECT KNOWLEDGE MAP
│
├── Structural Layer
│     deterministic/tool-first
│
└── Semantic Layer
      evidence-backed AI-assisted knowledge
```

### Structural Layer

Answers:

- what exists;
- where it is;
- what depends on what;
- what calls what;
- what reads/writes data;
- which tests cover what;
- which APIs are exposed.

### Semantic Layer

Answers:

- what components are responsible for;
- which business concepts exist;
- which workflows matter;
- which ADRs govern behavior;
- which constraints/invariants apply;
- which assumptions, risks, and known issues exist.

## 4. Bootstrap lifecycle

```text
PROJECT DISCOVERY
      ↓
SOURCE DISCOVERY
      ↓
PROJECT INDEX (S0)
      ↓
STRUCTURAL EXTRACTION (S1)
      ↓
DOCUMENTATION DISCOVERY
      ↓
SEMANTIC OVERVIEW (L2)
      ↓
EVIDENCE LINKING
      ↓
VALIDATION
      ↓
PERSISTENCE
```

Bootstrap is progressive and does not require exhaustive understanding.

Recommended initial readiness:

```text
S0 Project Index      → complete
S1 Structural Map     → usable/high coverage
L2 Semantic Overview  → partial but useful
L3 Deep Knowledge     → accumulated later
```

## 5. Structural extraction

Structural extraction is adapter-based and normalized.

```text
Project-specific source
      ↓
Adapter
      ↓
Normalized Node / Edge batch
      ↓
Identity Resolution
      ↓
Validation
      ↓
Structural Graph
```

Key decisions:

- small universal `kind` set;
- open `subtype`;
- canonical relation direction;
- inverse relations derived at query time;
- evidence/provenance preserved;
- S1 is default initial-load depth;
- S2 is lazy/targeted.

## 6. Semantic knowledge

Semantic knowledge is stored as structured facts rather than one global summary.

```text
Structural Node
   ├── responsible_for → Business Concept
   ├── participates_in → Workflow
   └── constrained_by → Constraint
```

Rules:

- every important fact has evidence;
- AI inference is explicit;
- conflicts are preserved;
- workflow agents emit candidates;
- Knowledge Refresh owns persistence.

## 7. Query / Context integration

The orchestrator exposes one logical `Context` capability.

```text
Context Strategy Router
   │
   ├── Direct Discovery
   │
   └── Knowledge-Assisted Discovery
```

PKM is a navigation accelerator, not a hard boundary.

Direct source search remains available.

## 8. Refresh lifecycle

```text
TRIGGERS
   ↓
CHANGESET
   ↓
MODE SELECTION
   ↓
AFFECTED REGION
   ↓
INVALIDATION
   ↓
STRUCTURAL RE-EXTRACTION
   ↓
SEMANTIC RE-EVALUATION
   ↓
MERGE
   ↓
VALIDATION
   ↓
ATOMIC PKM REVISION
```

Modes:

```text
incremental
targeted
full
```

Incremental is the default.

## 9. Health / Audit lifecycle

```text
AUDIT REQUEST
      ↓
SELECT AUDIT SCOPE
      ↓
COLLECT MAP + PROJECT EVIDENCE
      ↓
RUN DETERMINISTIC CHECKS
      ↓
RUN SEMANTIC / CONSISTENCY CHECKS
      ↓
CALCULATE HEALTH METRICS
      ↓
CLASSIFY FINDINGS
      ↓
SELECT REMEDIATION
      ↓
AUDIT REPORT
```

Health/Audit must detect:

- broken references;
- stale map regions;
- coverage gaps;
- ontology violations;
- adapter failures;
- revision drift;
- low-evidence knowledge;
- semantic conflicts;
- suspicious low-confidence clusters;
- source/documentation contradictions;
- derived artifact drift;
- incremental-refresh failures.

The audit recommends one of:

```text
no_action
targeted_refresh
incremental_refresh
full_refresh
rebuild
manual_review
maintenance_task
```

## 10. PKM revision model

Every persisted map revision is explicit.

```text
PKM-42
  ↓ refresh
PKM-43
  ↓ refresh
PKM-44
```

Each revision records:

- project revision;
- ontology version;
- adapter versions;
- refresh mode;
- audit state;
- coverage/freshness metadata.

No silent last-writer-wins behavior is allowed.

## 11. Failure philosophy

The PKM should improve workflows without becoming a fragile single point of failure.

If PKM is unavailable or unhealthy:

```text
Context
   ↓
Direct Discovery
```

A non-critical PKM failure should generally:

```text
mark knowledge stale
      ↓
create maintenance finding
      ↓
allow main task to complete
```

Critical corruption or integrity failure may require stronger blocking policy.

## 12. Model policy

Use deterministic tooling wherever possible.

LLM-heavy reasoning is concentrated in:

- Semantic Overview;
- semantic conflict analysis;
- ambiguous identity resolution;
- difficult impact analysis;
- audit interpretation where deterministic rules are insufficient.

## 13. Current document set

Design documents created so far:

```text
01 Context Graph — Direct Discovery
02 Context Graph — Knowledge-Assisted Discovery
03 PKM Architecture
04 Context Strategy Router
05 Knowledge Bootstrap / Initial Load
06 Structural Extraction Architecture
07 PKM Node / Edge Contract
08 PKM Ontology / Relation Registry
09 Structural Bootstrap Profiles
10 Semantic Layer Architecture
11 Semantic Knowledge Contract
12 Knowledge Refresh Subgraph
13 Knowledge Refresh Contracts
14 Knowledge Health / Audit Subgraph
15 Knowledge Health / Audit Contracts
16 Knowledge Health Policy
```

## 14. Current lifecycle

```text
ONBOARDING
   ↓
BOOTSTRAP
   ↓
QUERY / CONTEXT
   ↓
TASK WORK
   ↓
KNOWLEDGE CANDIDATES
   ↓
REFRESH
   ↓
AUDIT
   ↓
TARGETED MAINTENANCE / CONTINUE
```

This closes the first complete PKM lifecycle design.


---

## 15. Architecture audit status

A full architecture audit has been completed.

Result:

```text
APPROVED WITH REQUIRED HARDENING
```

The main PKM architecture remains valid. Before implementation of persistent storage and atomic Refresh, the P0 contract findings must be resolved.

Primary hardening areas:

```text
stable identity
SourceRevision
EvidenceRef
Knowledge Query contract
PKM Store transaction contract
Knowledge Sync State
```

See:

- `17-pkm-architecture-audit.md`
- `18-pkm-audit-remediation-roadmap.md`
