---
name: knowledge-curator
description: Maintain portable JSONL project entities and relations with existing-source provenance, explicit conflict and supersede semantics, and reproducible derived indexes.
---

# Knowledge Curator

1. Treat source documents as canonical; the graph is navigation only.
2. Merge the immutable Core ontology with additive, non-conflicting project terms.
3. Add nodes and edges only when their project-relative provenance source exists and
   its digest can be captured.
4. Reject conflicting IDs, unknown ontology terms, supersede cycles, and edges to
   dangling or superseded nodes.
5. Rebuild all indexes atomically from effective canonical JSONL with
   `orchestrator.knowledge.rebuild_indexes`.
6. Verify deterministic byte-for-byte rebuild output; never edit or commit indexes.
