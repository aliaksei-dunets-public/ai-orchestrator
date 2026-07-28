# ADR-0002: Project-owned Memory and Knowledge lifecycle

**Status:** accepted

## Context

The version 1 memory and knowledge primitives did not define ownership, promotion,
retrieval, or migration for target projects. Shared Core-owned data would mix project
state and violate ADR-0001.

## Decision

- Each target project owns tracked canonical JSONL stores below `.orchestrator/memory`
  and `.orchestrator/knowledge`.
- Proposals, derived indexes, and migration backups are operational artifacts and are
  excluded from Git.
- Observation, lesson, and decision proposals may be promoted automatically only when
  their unchanged source is authoritative. Instructions and non-authoritative sources
  always require an approval bound to the proposal and source hashes.
- Core ontology identifiers are immutable. Projects may add non-conflicting terms.
- Retrieval uses deterministic lexical ranking and bounded graph traversal. Embeddings,
  network services, and external databases are outside this decision.
- Schema-version-1 Python APIs and records remain readable throughout the 1.x line.

## Consequences

Canonical records remain portable and reviewable. Derived state is reproducible. The
runtime must validate provenance, effective lifecycle state, ontology additions, and
retrieval bounds before data reaches an agent context.

## Rollback

Disable workflow integration, restore canonical stores from Git or a verified migration
backup, and rebuild derived indexes. Canonical records are never deleted as a rollback
mechanism; corrections use append-only disable or supersede events.
