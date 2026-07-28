# Task Context contract

The normative source is `docs/specifications/task-layer-specification.md`.
Use this file as a compact checklist; the specification wins if they differ.

## Frontmatter

Required fields:

```yaml
schema_version: 1
title: Short title
type: feature
mode: quick | standard | deep
risk: low | medium | high | critical
created_by: task-creation-workflow
```

A draft has no `id` or uses `id: null`. A registered context has
`id: TASK-XXXX` and a positive `revision`; `status` is forbidden. A deep draft
also has `approach_approved: true` after the user's explicit approval.

## Required sections

Quick contexts require User Request, Goal, Scope (including In Scope and Out of
Scope), Acceptance Criteria, Implementation Plan, and Open Questions.

Standard and deep contexts additionally require Problem or Need, Current
Behavior, Expected Behavior, Analysis, Selected Approach, Alternatives
Considered, Affected Components, Constraints, Risks, and Plan Review.

Registered contexts have a `# TASK-XXXX — <title>` heading and an
`# Execution Record`. Critical open questions block registration.
