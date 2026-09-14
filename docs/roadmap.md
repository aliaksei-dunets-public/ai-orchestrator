# Graph Orchestrator migration roadmap

The graph-based framework is not yet implemented. The documents in this directory are design inputs, with status recorded in each document. Delivery is sequential; a phase is complete only when its contracts, runtime, tests, and user documentation agree.

1. **Repository boundary (current):** preserve the previous product and its old local state and release artifacts in `obsolete/`; move the graph design documents into root `docs/`; establish new root guidance. Verify file preservation and links.
2. **Contract consolidation:** reconcile draft and accepted design artifacts into one authoritative set of task, workflow-run, artifact, and transition contracts. Resolve contradictions explicitly before coding.
3. **Deterministic foundations:** implement persistent Task Manager Service, artifact repository, schema validation, and graph state/transition engine with focused tests.
4. **Preparation workflow:** implement context, analysis, specification, planning, review, and the durable `ready` boundary.
5. **Execution workflow:** implement atomic claims and recovery, execution preflight, implementation, reviews, tests, documentation, final validation, and user acceptance.
6. **Knowledge and integrations:** implement Project Knowledge Map lifecycle and optional tracker/platform adapters after core contracts are stable.
7. **End-to-end validation:** run scenario, recovery, concurrency, security, and portability tests; publish operational guides and release evidence.

Do not reuse legacy code implicitly. A needed legacy skill, idea, or contract must be deliberately adapted into the new root and validated against the consolidated graph contracts.
