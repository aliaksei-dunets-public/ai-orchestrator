---
language: en
---

# ADR-0004: Task Finalization receipts

- Status: accepted
- Date: 2026-07-28

## Context

Execution specifications required documentation, Knowledge Graph, and memory
updates before commit and `done`, but Backlog Loop moved directly from execution
to commit/complete. `TaskManager.complete()` checked status and workspace/commit
evidence only, so a direct caller could skip the three gates.

## Decision

An obligatory `TaskFinalizationCoordinator` runs after implementation, reviews,
and security, and before commit. It receives task ID and registered context,
completed checkpoint, normalized changed paths, Documentation Manager
dispositions, an explicit schema-version-1 Knowledge Curator proposal, and
secret-safe memory candidates.

The coordinator validates inputs, applies policy-safe knowledge/memory changes,
and creates a versioned receipt. The receipt binds task ID, context
revision/baseline hash, checkpoint, and changed paths. `complete` accepts only
`.orchestrator/tasks/finalization/<TASK-ID>.json`, verifies hash/freshness/readiness,
and stores its digest in Task Registry.

Empty knowledge proposals and empty memory candidate lists are valid explicit
no-ops. Missing proposals or documentation disposition block finalization.
Instruction and non-authoritative memory require hash-bound approval and return
`waiting_user` until decided. Session Reporter remains a post-loop step and
never auto-promotes non-authoritative memory.

## Consequences

- Direct API/CLI and serial/isolated backlog cannot skip finalization.
- Historical `done` records remain readable; every new completion needs a receipt.
- Receipts and derived indexes are operational state; canonical docs, memory, and
  knowledge stores are committed with the task.
- Pending approval stops commit and preserves checkpoint/proposal for idempotent
  resume.
- Task Manager remains a structural gate, not a semantic-content owner.

## Rollback

Stop before commit, preserve receipt/checkpoint, and revert runtime, workflow,
CLI/schema, and skills in one commit. Do not delete append-only memory; use
disable/supersede. Correct Knowledge Graph content with a new
provenance-backed proposal. Historical registry records remain readable.
