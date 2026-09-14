---
name: memory-manager
description: Curate append-only project observations, decisions, and lessons with source provenance, confidence, supersede links, and secret-safe promotion gates.
---

# Memory Manager

1. Create proposals with `orchestrator.memory.create_proposal`; use project-relative
   provenance and capture the current source digest.
2. Redact and reject secret-like content before any persistence.
3. Use `promote_proposal`; observation, lesson, and decision may auto-promote only
   from an unchanged specification, accepted ADR, completed Task Context, or approved review.
4. Instructions and non-authoritative sources always require explicit approval bound
   to both `proposal_hash` and `source_digest`.
5. Preserve provenance through append-only events; disable or supersede bad entries
   rather than deleting history.
6. Retrieve only `effective_entries`; proposals and disabled/superseded records are not
   agent context.
7. During task finalization, turn confirmed task evidence into idempotent
   proposals. Auto-promote only authoritative observation, decision and lesson
   candidates; return pending proposal hashes for every required approval and
   block completion until each proposal is explicitly approved or rejected.
