---
language: en
---

# Documentation policy

## Purpose

Versioned `docs/` is the source of truth for delivered AI Orchestrator and
target-project behaviour. A document must describe verified code, public
contracts, or an accepted decision. Plans and specifications are development
inputs, not published project truth.

## Ownership

Each topic has one canonical owner. `docs/INDEX.md` owns navigation; core and
Task Layer contracts live in `docs/architecture/`; the roadmap lives in
`docs/roadmap.md`; operational guidance lives in `docs/guides/`; upgrade
contracts live in `docs/migrations/`; accepted decisions live in `docs/adr/`.
The path-to-document relationship is declared in
`config/documentation-map.json`.

## Synchronization after a task

Before finalization, Documentation Manager loads this policy, the index, and
the documentation map; computes the changed-path impact; and updates only the
mapped, owner-controlled canonical documents. Every impact has exactly one
disposition: `updated`, or `not_applicable` with concrete evidence. Local links
in each impacted Markdown document must resolve before finalization.

Tasks, plans, and specifications may provide context, but documentation must
be validated against implemented behaviour, changed contracts, and test
evidence. A task must not mechanically publish unimplemented intent.

## Language and Knowledge Graph rules

Canonical documents are English. User-facing guides have Russian companions
when required by `config/language-policy.json`; companions are useful to users
but never canonical or Knowledge Graph sources. Knowledge Graph provenance
accepts only English canonical sources permitted by the language and
source-authority policies.

## Local artifacts and target projects

`.orchestrator/plans/` and `.orchestrator/specifications/` are local,
Git-ignored development artifacts. They are never released, indexed, or used
as required runtime documentation. Target onboarding preserves user-owned
documentation; any missing documentation baseline is previewed, approval-bound,
and rollback-safe.
