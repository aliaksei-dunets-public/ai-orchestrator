---
name: memory-manager
description: Curate append-only project observations, decisions, and lessons with source provenance, confidence, supersede links, and secret-safe promotion gates.
---

# Memory Manager

1. Propose entries only from confirmed sources and capture their current digest.
2. Redact and reject secret-like content before any persistence.
3. Use `orchestrator.memory.append_entry`; reject duplicates and stale sources.
4. Never promote an observation to an instruction automatically.
5. Preserve provenance through `supersedes`; disable bad entries rather than deleting history.
