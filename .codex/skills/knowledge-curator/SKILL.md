---
name: knowledge-curator
description: Maintain portable JSONL project entities and relations with existing-source provenance, explicit conflict and supersede semantics, and reproducible derived indexes.
---

# Knowledge Curator

Use this skill for initial project graph bootstrap during onboarding and for every
later Knowledge Graph maintenance task.

## Ownership

1. Treat source documents as canonical; the graph is a navigation layer only.
2. Own source inventory, node/edge proposal, provenance validation, canonical
   merge, effective-graph validation, index rebuild and graph maintenance.
3. Let `project-onboarding` own target bootstrap, preview, approval, apply and
   rollback. Do not bypass its approval boundary.

## Initial onboarding workflow

1. Read the project structure and canonical sources first: specifications, accepted
   ADRs, project context, public contracts, component documentation and relevant
   completed tasks. Do not crawl secrets, generated trees, releases or `.git`.
2. Produce a concise evidence-based proposal with `schema_version: 1`, `nodes`
   and `edges`. Every item must contain a stable ID, one project-relative source
   path and only an assertion supported by that source.
3. Use only known Core ontology terms or additive project terms. Prefer a small
   useful graph over speculative coverage. An empty proposal is valid when evidence
   is insufficient.
4. Never provide `source_digest` in the proposal. Core calculates it from the
   current source file. Never put credentials or secret material in labels.
5. Return the proposal to onboarding as `answers.knowledge_graph`; do not write
   nodes, edges or indexes directly during discovery.
6. Show the proposed nodes, edges, sources and rejected/uncertain candidates so the
   user can review the complete onboarding plan and its `plan_hash`.

## Proposal contract

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "reports-api",
      "kind": "component",
      "label": "Reports API",
      "source": "docs/architecture/api-contract.md",
      "supersedes": null,
      "enabled": true
    }
  ],
  "edges": [
    {
      "id": "reports-api-depends-on-auth",
      "source_node": "reports-api",
      "target_node": "authorization-service",
      "relation": "depends_on",
      "source": "docs/adr/0010-api-authorization.md",
      "enabled": true
    }
  ]
}
```

## Validation and maintenance

1. Merge the immutable Core ontology with additive, non-conflicting project terms.
2. Add nodes and edges only when their project-relative provenance source exists and
   its digest can be captured.
3. Reject conflicting IDs, unknown ontology terms, excluded/out-of-root sources,
   supersede cycles, and edges to dangling or superseded nodes.
4. Preserve existing canonical records; identical IDs are idempotent, conflicting
   payloads are errors, and corrections use `supersedes` or disable semantics.
5. Rebuild indexes atomically from effective canonical JSONL with
   `orchestrator.knowledge.rebuild_indexes`.
6. Verify deterministic byte-for-byte rebuild output; never edit or commit indexes.
7. During task finalization, always return an explicit schema-version-1 proposal.
   Use an empty `nodes`/`edges` proposal when the task changed no graph-relevant
   project facts. Apply non-empty maintenance proposals only through Core
   validation and atomic graph update helpers.
