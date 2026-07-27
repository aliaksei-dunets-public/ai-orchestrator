---
name: knowledge-curator
description: Maintain portable JSONL project entities and relations with existing-source provenance, explicit conflict and supersede semantics, and reproducible derived indexes.
---

# Knowledge Curator

1. Treat source documents as canonical; the graph is navigation only.
2. Add nodes and edges only when their provenance source exists.
3. Reject conflicting IDs and require an explicit supersede link for replacement semantics.
4. Rebuild all indexes from canonical JSONL with `orchestrator.knowledge.rebuild_indexes`.
5. Verify deterministic byte-for-byte rebuild output.
