# Phase 25 — Full Memory and Knowledge Lifecycle Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Завершить безопасный, переносимый и проверяемый lifecycle Project Memory и Knowledge Graph в Core и target project.

**Architecture:** Target project владеет tracked canonical JSONL и approval provenance, а Core предоставляет platform-neutral runtime, schemas, ontology, retrieval и lifecycle operations. Operational proposals и derived indexes игнорируются Git; context retrieval детерминирован, ограничен бюджетом и не использует внешние зависимости.

**Tech Stack:** Python 3.11 standard library, JSON/JSONL, JSON Schema draft 2020-12, YAML workflows, Markdown, `unittest`, существующие argparse CLI и atomic file publication patterns.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md`, `docs/specifications/task-layer-specification.md` и ADR-0001.
- Сохранить совместимость существующих schema-version-1 memory/knowledge записей и публичных Python функций через compatibility adapters.
- Хранить project data только в target-owned `.orchestrator/`; Core не владеет данными нескольких проектов.
- Использовать один modifying process, Python standard library, atomic publication и deterministic JSON serialization.
- Не читать ignored/secret paths, не сохранять credential-like content и не ослаблять immutable security policies.
- Не редактировать `.codex/skills/` напрямую; синхронизировать projections из canonical `skills/`.
- Не коммитить proposals, indexes, migration backups, telemetry, Task Registry и checkpoints.
- Не добавлять embeddings, vector database, network service, UI или cross-project shared memory.

## Deliverables

- Revision-bound design and ADR for storage, promotion, ontology and retrieval.
- Project-owned memory entries/events/approvals and knowledge ontology/nodes/edges stores.
- Deterministic source-authority, promotion, effective-state, graph-index and bounded-retrieval APIs.
- Target onboarding/configuration, Git policy, migration and rollback support.
- JSON-first CLI commands, workflow integration, canonical skill updates and synchronized projections.
- Health Check, security checks, documentation, release 1.2 migration evidence and multi-project acceptance coverage.

## Dependencies

- Completed phases 17–19 and 24.
- Existing Session Reporter, approvals, onboarding, Task Manager, execution routing, Health Check and release infrastructure.
- Explicit user approval on 2026-07-28 for target-owned canonical stores, source-authority promotion, bounded deterministic retrieval and additive project ontology.

## Acceptance Criteria

- AC1: Onboarding creates or preserves tracked canonical memory/knowledge stores and ignores only proposals, derived indexes and migration backups.
- AC2: Existing schema-version-1 memory entries, nodes, edges and Python call sites remain readable; migration preview/apply/rollback preserves content and provenance.
- AC3: Observation, lesson and decision promotion without user approval succeeds only for a validated authoritative source and unchanged source digest.
- AC4: Instruction promotion and every non-authoritative proposal require explicit approval bound to proposal hash and source digest.
- AC5: Memory disable and supersede semantics are append-only, preserve history and produce deterministic effective state without duplicate or cyclic lifecycle references.
- AC6: Core ontology is immutable, project ontology is additive, and unknown or conflicting kinds/relations are rejected.
- AC7: Graph writes require contained existing provenance and effective endpoint nodes; conflicts never overwrite canonical records silently.
- AC8: Knowledge indexes rebuild atomically and byte-for-byte deterministically from canonical ontology, nodes and edges.
- AC9: Retrieval excludes disabled, superseded, stale, invalid and secret-like records and emits a deterministic context pack within configured entry, graph-depth and character limits.
- AC10: Every Task Creation and Task Execution route retrieves a fresh context pack before analysis or implementation, while empty or irrelevant stores remain a valid no-op.
- AC11: Memory, knowledge and context CLI commands provide JSON output, stable exit codes and no traceback for invalid input.
- AC12: Health Check detects malformed stores, unsafe paths, stale provenance, ontology/reference conflicts, stale indexes and incorrect Git-ignore policy.
- AC13: Onboarding, promotion, retrieval, migration and reports do not persist secrets or read excluded operational/release trees.
- AC14: Canonical skills, schemas, workflows, registries, specifications, guides, migration notes, version metadata and release artifacts agree, and all affected/full tests plus strict Health Check pass.

## Testing Strategy

| Check | Kind | Acceptance |
| --- | --- | --- |
| `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_memory_knowledge_contracts -v` | contract | AC1, AC2, AC6, AC14 |
| `.\.venv\Scripts\python.exe -m unittest tests.unit.test_memory tests.unit.test_source_authority tests.scenarios.test_memory_lifecycle -v` | focused/scenario | AC2–AC5, AC13 |
| `.\.venv\Scripts\python.exe -m unittest tests.unit.test_knowledge tests.unit.test_ontology tests.scenarios.test_knowledge_lifecycle -v` | focused/scenario | AC2, AC6–AC8, AC13 |
| `.\.venv\Scripts\python.exe -m unittest tests.unit.test_retrieval tests.scenarios.test_context_retrieval -v` | focused/scenario | AC9, AC10, AC13 |
| `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_onboarding_workflow tests.unit.test_onboarding_workflow tests.scenarios.test_agent_led_onboarding -v` | contract/scenario | AC1, AC12–AC14 |
| `.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_memory_knowledge_cli tests.scenarios.test_task_creation_retrieval tests.scenarios.test_implementation_runner -v` | scenario | AC10, AC11 |
| `.\.venv\Scripts\python.exe -m unittest tests.unit.test_health tests.scenarios.test_memory_knowledge_health tests.scenarios.test_security_review -v` | focused/scenario | AC12, AC13 |
| `.\.venv\Scripts\python.exe -m unittest tests.unit.test_documentation tests.contracts.test_specifications tests.acceptance.test_release -v` | contract/acceptance | AC2, AC14 |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` and `.\.venv\Scripts\python.exe -m orchestrator health --strict --json` | acceptance | AC1–AC14 |

This is a new capability completion rather than a fixed defect, so no regression-labelled test is required. Existing suites remain affected regression evidence.

## Risks and Rollback

- Risk: migration corrupts canonical JSONL. Detection: digest/record-count mismatch. Rollback: restore the verified pre-apply backup and previous config.
- Risk: generated context becomes an implicit instruction channel. Detection: context-pack schema and instruction-promotion tests. Rollback: disable retrieval integration while retaining canonical stores.
- Risk: project ontology changes Core semantics. Detection: immutable-ID contract test. Rollback: reject the project extension before persistence.
- Risk: stale approval promotes changed content. Detection: proposal/source hash mismatch. Rollback: reject before canonical write.
- Risk: graph becomes a second source of truth. Detection: missing provenance and source-digest Health findings. Rollback: remove derived indexes and rebuild only from validated canonical records.
- Risk: canonical project knowledge is accidentally ignored. Detection: Git policy Health finding and onboarding scenario. Rollback: restore the managed `.gitignore` block from onboarding backup.

## Implementation Tasks

### Task 1: Contracts, storage layout and compatibility boundary

**Files:**

- Create: `docs/adr/0002-project-memory-knowledge-lifecycle.md`
- Create: `config/knowledge-ontology.json`
- Create: `config/schemas/memory-proposal.schema.json`
- Create: `config/schemas/memory-event.schema.json`
- Create: `config/schemas/memory-approval.schema.json`
- Create: `config/schemas/knowledge-ontology.schema.json`
- Create: `config/schemas/knowledge-index.schema.json`
- Create: `config/schemas/context-pack.schema.json`
- Modify: `config/schemas/memory-entry.schema.json`
- Modify: `config/schemas/knowledge-node.schema.json`
- Modify: `config/schemas/knowledge-edge.schema.json`
- Modify: `config/schemas/project-config.schema.json`
- Modify: `config/defaults.yaml`
- Test: `tests/contracts/test_memory_knowledge_contracts.py`

**Interfaces:**

- Consumes: existing schema-version-1 entries/nodes/edges and project config.
- Produces: additive project-store schemas, immutable Core ontology, retrieval limits and an explicit 1.x compatibility boundary.

**Acceptance:**

- Covers AC1, AC2, AC6 and the contract portion of AC14.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_memory_knowledge_contracts tests.contracts.test_specifications -v` passes.

- [ ] **Step 1:** Add failing contract tests for every new schema, Core ontology uniqueness, project config defaults and legacy record acceptance.
- [ ] **Step 2:** Run the focused contract command and capture the expected missing-contract failures.
- [ ] **Step 3:** Add the schemas, Core ontology and defaults without changing existing Task Registry or Task Context contracts.
- [ ] **Step 4:** Run focused contracts and schema discovery tests.
- [ ] **Step 5:** Review the compatibility boundary against `docs/migrations/1.0.md` and record documentation impact.

### Task 2: Project Memory store, lifecycle events and source authority

**Files:**

- Create: `orchestrator/source_authority.py`
- Modify: `orchestrator/memory.py`
- Modify: `orchestrator/approvals.py`
- Modify: `skills/bundled/memory-manager/SKILL.md`
- Test: `tests/unit/test_memory.py`
- Create: `tests/unit/test_source_authority.py`
- Create: `tests/scenarios/test_memory_lifecycle.py`

**Interfaces:**

- Consumes: project root, proposal content, project-relative source, source digest, confidence, optional supersede and optional approved proposal hash.
- Produces: deterministic proposal hashes, tracked entries/events/approval records, effective memory state and validation/migration results.
- Preserves: existing `MemoryEntry`, `append_entry`, `load_entries` and `source_digest` call behavior through compatibility adapters.

**Acceptance:**

- Covers AC2–AC5 and memory-specific portions of AC13.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.unit.test_memory tests.unit.test_source_authority tests.scenarios.test_memory_lifecycle -v` passes.

- [ ] **Step 1:** Add failing cases for source classification, stale hashes, manual approval binding, instruction gates, append-only disable/supersede and compatibility reads.
- [ ] **Step 2:** Run the focused command and verify failures cover each local criterion.
- [ ] **Step 3:** Implement project-relative paths, proposal canonicalization, authoritative-source validation and atomic logical append.
- [ ] **Step 4:** Implement approval records, lifecycle events, effective-state resolution and cycle/duplicate checks.
- [ ] **Step 5:** Run focused tests plus existing approval, session-report and memory suites; review persisted fields for secret leakage.

### Task 3: Additive ontology and complete Knowledge Graph lifecycle

**Files:**

- Create: `orchestrator/ontology.py`
- Modify: `orchestrator/knowledge.py`
- Modify: `skills/bundled/knowledge-curator/SKILL.md`
- Test: `tests/unit/test_knowledge.py`
- Create: `tests/unit/test_ontology.py`
- Modify: `tests/scenarios/test_phase_18.py`
- Create: `tests/scenarios/test_knowledge_lifecycle.py`

**Interfaces:**

- Consumes: Core ontology, optional project ontology, project-relative provenance, node/edge records and explicit supersede links.
- Produces: merged validated ontology, effective nodes/edges, referential validation and atomic deterministic indexes by kind, relation, source and adjacency.
- Preserves: existing `KnowledgeNode`, `KnowledgeEdge`, `add_node`, `add_edge` and `rebuild_indexes` compatibility behavior.

**Acceptance:**

- Covers AC2 and AC6–AC8 plus graph-specific portions of AC13.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.unit.test_knowledge tests.unit.test_ontology tests.scenarios.test_phase_18 tests.scenarios.test_knowledge_lifecycle -v` passes.

- [ ] **Step 1:** Add failing tests for immutable Core terms, additive project terms, unknown relations, unsafe provenance, dangling/superseded endpoints and conflicting IDs.
- [ ] **Step 2:** Add a failing double-rebuild scenario for the complete index contract.
- [ ] **Step 3:** Implement ontology loading/merge and effective graph validation without platform-name branches.
- [ ] **Step 4:** Extend atomic index rebuild with stable ordering, canonical store digest, incoming/outgoing adjacency and source/relation lookups.
- [ ] **Step 5:** Run focused and existing phase-18 tests and compare rebuilt index bytes.

### Task 4: Deterministic bounded retrieval and context packs

**Files:**

- Create: `orchestrator/retrieval.py`
- Create: `tests/unit/test_retrieval.py`
- Create: `tests/scenarios/test_context_retrieval.py`

**Interfaces:**

- Consumes: project root, Task Context text, affected paths, explicit terms, effective memory/graph state and configured limits.
- Produces: schema-valid deterministic context pack with query/store digests, bounded records, provenance and freshness metadata.
- Excludes: ignored paths, disabled/superseded/stale records, secret-like content and graph traversal beyond the relation/depth allowlist.

**Acceptance:**

- Covers AC9, retrieval portions of AC10 and AC13.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.unit.test_retrieval tests.scenarios.test_context_retrieval -v` passes.

- [ ] **Step 1:** Add failing scoring, stable tie-break, graph-depth, character-budget, empty-store and exclusion tests.
- [ ] **Step 2:** Run focused tests and confirm deterministic/budget failures before implementation.
- [ ] **Step 3:** Implement normalized lexical scoring, bounded graph expansion and stable selection.
- [ ] **Step 4:** Implement canonical context-pack serialization and digest calculation.
- [ ] **Step 5:** Run the same retrieval twice byte-for-byte, then run focused security exclusion cases.

### Task 5: Target onboarding, project configuration and migration

**Files:**

- Modify: `orchestrator/onboarding_workflow.py`
- Create: `orchestrator/memory_knowledge_migration.py`
- Modify: `skills/system/project-onboarding/SKILL.md`
- Modify: `skills/system/project-onboarding/scripts/onboard_project.py`
- Modify through installer: `.codex/skills/project-onboarding/`
- Modify: `.gitignore`
- Create: `.orchestrator/memory/entries.jsonl`
- Create: `.orchestrator/memory/events.jsonl`
- Create: `.orchestrator/knowledge/ontology.json`
- Create: `.orchestrator/knowledge/nodes.jsonl`
- Create: `.orchestrator/knowledge/edges.jsonl`
- Modify: `tests/contracts/test_onboarding_workflow.py`
- Modify: `tests/unit/test_onboarding_workflow.py`
- Modify: `tests/scenarios/test_agent_led_onboarding.py`
- Create: `tests/scenarios/test_memory_knowledge_migration.py`

**Interfaces:**

- Consumes: target project evidence, existing project config/stores, selected profiles and approved onboarding or migration plan hash.
- Produces: preserved/initialized tracked stores in external targets and this self-hosted repository, managed Git-ignore entries for proposals/indexes/backups, validated config, migration report and verified rollback.

**Acceptance:**

- Covers AC1, migration portions of AC2, AC12–AC14 and onboarding idempotency.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_onboarding_workflow tests.unit.test_onboarding_workflow tests.scenarios.test_agent_led_onboarding tests.scenarios.test_memory_knowledge_migration -v` passes.

- [ ] **Step 1:** Add failing onboarding preview tests for exact tracked/ignored paths and preservation of pre-existing canonical data.
- [ ] **Step 2:** Add failing migration preview, stale-plan, content-count/digest and rollback scenarios.
- [ ] **Step 3:** Extend onboarding plan/apply/validation and managed Git-ignore blocks atomically.
- [ ] **Step 4:** Implement migration inspect/plan/apply/rollback with verified backup and compatibility import.
- [ ] **Step 5:** Synchronize the project-onboarding projection and run onboarding/migration tests twice for idempotency.

### Task 6: CLI, task workflows and skill routing

**Files:**

- Create: `orchestrator/memory_cli.py`
- Create: `orchestrator/knowledge_cli.py`
- Create: `orchestrator/context_cli.py`
- Modify: `orchestrator/cli.py`
- Modify: `workflows/task-creation-standard.yaml`
- Modify: `workflows/task-execution.yaml`
- Modify: `workflows/backlog-loop.yaml`
- Modify: `registries/workflows.json`
- Modify: `skills/system/task-creator/SKILL.md`
- Modify: `skills/bundled/task-analyzer/SKILL.md`
- Modify: `skills/bundled/implementation-runner/SKILL.md`
- Modify: `skills/bundled/orchestrator-auditor/SKILL.md`
- Modify: `skills/bundled/session-reporter/SKILL.md`
- Modify through installer: `.codex/skills/task-creator/`
- Modify through installer: `.codex/skills/task-analyzer/`
- Modify through installer: `.codex/skills/implementation-runner/`
- Modify through installer: `.codex/skills/orchestrator-auditor/`
- Modify through installer: `.codex/skills/session-reporter/`
- Create: `tests/scenarios/test_memory_knowledge_cli.py`
- Create: `tests/scenarios/test_task_creation_retrieval.py`
- Modify: `tests/scenarios/test_implementation_runner.py`
- Modify: `tests/scenarios/test_backlog_loop.py`
- Modify: `tests/unit/test_session_report.py`

**Interfaces:**

- Consumes: `--root`, JSON files/arguments, canonical stores, task inputs and existing execution policy.
- Produces: stable JSON CLI results/exit codes, pre-analysis/pre-implementation context packs and post-session memory proposals.
- Workflow order: retrieval precedes every quick/standard/deep analysis or implementation; Session Reporter emits structured candidates after validated evidence, and curation never bypasses promotion policy.

**Acceptance:**

- Covers AC3, AC4, AC9–AC11 and workflow portions of AC13–AC14.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_memory_knowledge_cli tests.scenarios.test_task_creation_retrieval tests.scenarios.test_implementation_runner tests.scenarios.test_backlog_loop tests.unit.test_session_report -v` passes.

- [ ] **Step 1:** Add failing CLI JSON/exit-code tests for valid, malformed, stale, unauthorized and empty-store operations.
- [ ] **Step 2:** Add failing quick/standard/deep workflow-order tests for retrieval freshness, no-op empty stores and policy-gated Session Report curation.
- [ ] **Step 3:** Implement thin CLI adapters over domain APIs without duplicating memory/knowledge rules.
- [ ] **Step 4:** Add declarative workflow steps and update canonical skills, keeping Core platform-neutral.
- [ ] **Step 5:** Synchronize affected projections and run CLI/workflow plus skill-drift tests.

### Task 7: Health, security and audit integration

**Files:**

- Modify: `orchestrator/health.py`
- Modify: `orchestrator/security.py`
- Modify: `orchestrator/audit.py`
- Modify: `config/policies/security.yaml`
- Modify: `tests/unit/test_health.py`
- Create: `tests/scenarios/test_memory_knowledge_health.py`
- Modify: `tests/scenarios/test_security_review.py`
- Modify: `tests/scenarios/test_audit.py`

**Interfaces:**

- Consumes: project config, canonical stores, derived index metadata, Git-ignore rules and repository paths.
- Produces: bounded findings for malformed records, unsafe/stale provenance, lifecycle/ontology/reference errors, secret indicators, stale indexes and Git-policy drift.
- Audit consumes bounded context packs read-only and does not mutate memory or graph.

**Acceptance:**

- Covers AC5–AC9, AC12 and AC13.

**Tests:**

- `.\.venv\Scripts\python.exe -m unittest tests.unit.test_health tests.scenarios.test_memory_knowledge_health tests.scenarios.test_security_review tests.scenarios.test_audit -v` passes.

- [ ] **Step 1:** Add failing Health cases for each new invariant and verify no traceback on corrupted JSONL.
- [ ] **Step 2:** Add security cases for path escape, ignored-source access, credential-like proposals and unbounded retrieval.
- [ ] **Step 3:** Implement defensive Health and security boundaries with stable finding codes and severities.
- [ ] **Step 4:** Integrate read-only context packs into audit inputs without changing audit proposal semantics.
- [ ] **Step 5:** Run focused Health/security/audit suites and strict Health against the repository.

### Task 8: Canonical documentation, release 1.2 and final acceptance

**Files:**

- Modify: `docs/specifications/orchestrator-specification.md`
- Modify: `docs/specifications/task-layer-specification.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `docs/guides/deployment-to-target-project-ru.md`
- Modify: `docs/migrations/cli-contract.md`
- Create: `docs/migrations/1.2.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `orchestrator/__init__.py`
- Modify: `tests/unit/test_documentation.py`
- Modify: `tests/contracts/test_specifications.py`
- Modify: `tests/acceptance/test_release.py`
- Modify: `tests/acceptance/test_roadmap_completion.py`
- Modify: `tests/acceptance/matrix.json`

**Interfaces:**

- Consumes: implemented contracts, CLI behavior, migration commands, validation evidence and release artifact builder.
- Produces: synchronized version 1.2 documentation, migration/rollback instructions, release metadata and multi-project acceptance evidence.

**Acceptance:**

- Covers AC2 and AC14 and documents all user-visible behavior from AC1–AC13.

**Tests:**

- Focused documentation/release tests, full discovery, acceptance matrix and strict Health Check pass with no `ERROR` or `CRITICAL`.

- [ ] **Step 1:** Update normative memory/knowledge, task-flow, target-layout, CLI and component-ownership contracts.
- [ ] **Step 2:** Document supported 1.1-to-1.2 migration, backup, rollback, compatibility window and known limitations.
- [ ] **Step 3:** Synchronize version metadata, changelog, roadmap and ignored release-artifact expectations.
- [ ] **Step 4:** Run `.\.venv\Scripts\python.exe -m unittest tests.unit.test_documentation tests.contracts.test_specifications tests.acceptance.test_release tests.acceptance.test_roadmap_completion -v`.
- [ ] **Step 5:** Run full discovery, acceptance matrix, Task Review, Code Review, Security Review and `.\.venv\Scripts\python.exe -m orchestrator health --strict --json`; record final evidence before release.
