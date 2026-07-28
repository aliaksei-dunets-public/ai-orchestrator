---
language: en
---

# AI Orchestrator documentation

This index is the entry point for the versioned documentation of the
orchestrator core. It describes delivered behaviour and verified contracts; it
does not contain local task plans or specifications.

## Canonical documents

- [Documentation policy](documentation-policy.md) — ownership, update rules,
  language policy, and the boundary between delivered documentation and local
  development artifacts.
- [Core architecture](architecture/orchestrator-core.md) — architecture,
  lifecycle, configuration hierarchy, and core boundaries.
- [Task Layer contract](architecture/task-layer.md) — Task Context, registry,
  execution, and finalization contracts.
- [Component contracts](architecture/component-contracts.md) — responsibility
  boundaries for runtime components.
- [Project roadmap](roadmap.md) — ordered delivery phases and milestones.

## Supporting documentation

- [Architecture decisions](adr/) record accepted irreversible decisions.
- [Guides](guides/) explain user and operator workflows. English guides are
  canonical; Russian companions exist where required by the language policy.
- [Migrations](migrations/) describe supported upgrades and rollback.
- [Validation](validation/) preserves published compatibility and release
  evidence.

## Local development artifacts

Plans and specifications live only in `.orchestrator/plans/` and
`.orchestrator/specifications/`. They are ignored by Git, excluded from release
artifacts and Knowledge Graph provenance, and may inform implementation but
never replace a canonical document.
