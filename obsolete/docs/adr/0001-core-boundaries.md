---
language: en
---

# ADR-0001: Core boundaries and sources of truth

This decision establishes the source of truth for portable architecture.

**Status:** accepted

## Context

The orchestrator must work across agent platforms and technology stacks.
Mixing project state, platform adapters, and orchestration logic would make
portability unverifiable.

## Decision

- `orchestrator/` contains the platform-neutral runtime.
- `skills/` is the canonical skill source; platform directories are installable projections.
- `registries/` maps logical identifiers to existing artifacts.
- `profiles/` describes platform and stack capabilities without changing Core.
- `docs/architecture/orchestrator-core.md` defines architecture and lifecycle.
- `docs/architecture/task-layer.md` defines Task Layer contracts.
- `.orchestrator/tasks/tasks.json` is local operational state and is not stored in Git.
- Task Context and Execution Record remain versioned.

Contracts change through a new specification revision, migration note, and
regression/contract tests. Immutable security policies have priority over every
local layer.

## Consequences

Core depends on capabilities rather than platform names. A new platform
integration must implement the shared contract and pass the acceptance suite
before it becomes stable.

## Rollback

Before dependent runtime code exists, this ADR can be replaced by a new
decision. After a contract is published, an incompatible change requires a
superseding ADR and migration.
