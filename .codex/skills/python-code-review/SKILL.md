---
name: python-code-review
version: 2.1.0-orchestrator.1
description: >-
  Review Python changes, components, or projects for evidence-backed correctness,
  architecture, failure-flow, and test defects. Use for Python semantic review;
  select quick, standard, or deep scope before loading detailed references.
---

# Python Code Review

Review only unless the user explicitly requests fixes. Reconstruct enough of the
affected behavior to find demonstrable defects; tools and checklists widen
coverage but do not replace judgment.

## Route before loading

Choose the smallest sufficient mode:

- `quick`: narrow low/medium-risk diff with no public API, persistence,
  migration, concurrency, authentication, security-sensitive, or irreversible
  behavior. Use this entrypoint and only the relevant section of
  `references/python-review.md`.
- `standard`: non-trivial change or component review. Read
  `references/system-analysis.md`, then retrieve only the relevant headings from
  `references/review-workflow.md` and `references/python-review.md`.
- `deep`: project audit, release candidate, high/critical risk, or sensitive
  boundary. Read the full `references/review-workflow.md` and the relevant
  supporting references.

Read `references/tooling.md` only before selecting automated checks. Use
`templates/review-report.md` only when a durable detailed report is requested.

## Review invariants

1. Establish target, context, requirements, exclusions and system horizon.
2. Search entry points, changed symbols, callers, state boundaries and tests
   before opening large files.
3. Trace at least one affected normal path and applicable failure/recovery path.
4. Form semantic hypotheses before consulting detailed checklists.
5. Run only targeted checks that can confirm or disprove material hypotheses.
6. Report only actionable findings with exact location, evidence, impact and
   remediation; reject preference-only or unproven concerns.
7. Preserve security, data integrity, compatibility and acceptance gates.

## Independent-review admission

Dispatch at most one independent reviewer only for:

- a deep/project audit or release candidate;
- high/critical risk or security-, data-, financial-, concurrency-,
  authentication-, migration-, persistence-, public-API-, or irreversible
  behavior;
- a Critical or Blocking candidate finding that needs challenge.

Do not dispatch for quick reviews. Provide assignment, scope, invariants, source
pointers, compact validation summaries and known limitations—not primary
findings, conversation history or unbounded raw logs. The reviewer returns only
new findings, validation, risks, blockers and required next actions.

If required isolation is unavailable, perform the clean-context fallback from
`references/review-workflow.md` and disclose it.

## Result contract

Return findings first, ordered by severity. Each finding includes:

- severity and verdict impact;
- file and tight line range;
- concise evidence and affected behavior;
- smallest effective remediation;
- validation that would prove the fix.

When there are no material findings, say so and report only material coverage
limits. Omit task restatement, routine tool narration, raw successful logs,
empty sections and repeated context.

## Completion

Stop when affected behavior and material risks are covered, candidate findings
are verified, required independent review is reconciled, and further scanning
is unlikely to change the verdict.
