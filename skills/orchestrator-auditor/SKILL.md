---
name: orchestrator-auditor
description: Audit the orchestrator for evidenced contradictions, dead workflows, drift, duplication, and test gaps, deduplicating stable findings and emitting proposals without applying changes.
---

# Orchestrator Auditor

1. Build a deterministic inventory and run `orchestrator.audit.audit_repository`.
2. For deep instruction, skill, agent, or workflow analysis, route the semantic pass through the atomic `optimizer` skill.
3. Keep only findings with concrete source pointers and a severity.
4. Deduplicate findings by stable fingerprint, including against the previous report.
5. Add an improvement proposal to each finding, but never apply it.
6. Route accepted proposals through the ordinary Task Creator and approval workflow.
