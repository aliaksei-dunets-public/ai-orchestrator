# Knowledge Curator and Onboarding Integration Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Включить первичное evidence-based формирование Knowledge Graph в Project Onboarding и расширить существующий `knowledge-curator` до владельца полного graph lifecycle.

**Architecture:** Агент формирует `knowledge_graph` proposal, core валидирует и детерминированно объединяет его с target-owned canonical JSONL. Preview, approval, apply, rollback и Health Check остаются частью onboarding workflow.

**Tech Stack:** Python 3.11+, standard library, JSON/JSONL, JSON Schema, Markdown, `unittest`.

## Global Constraints

- Не создавать второй навык с пересекающейся ответственностью.
- Source documents остаются canonical truth; graph — navigation layer.
- Не писать в target до explicit approval конкретного `plan_hash`.
- Не ослаблять immutable security policy и source exclusion rules.
- Не коммитить proposals, derived indexes, backups, checkpoints или releases.
- Сохранить backward compatibility для onboarding без graph proposal и для существующих graph APIs.
- Сохранить пользовательские изменения вне managed blocks.

## Deliverables

- Валидируемый graph proposal contract и merge helper.
- Интеграция graph proposal в onboarding preview, hash, apply, rollback и validation.
- Расширенный canonical `knowledge-curator` skill и обновлённый `project-onboarding` skill.
- Обновлённые schemas, specs, component contracts, deployment guide и knowledge guide.
- Unit, scenario, contract и acceptance evidence.

## Dependencies

- Full memory/knowledge lifecycle TASK-0002.
- Existing `orchestrator.knowledge`, ontology, source authority and onboarding workflow.
- Canonical bundled skill distribution and installer.

## Acceptance Criteria

- AC1: Onboarding accepts an optional schema-versioned `knowledge_graph` proposal and includes validated graph changes in the same preview and `plan_hash`.
- AC2: Core recalculates project-relative provenance digests and rejects excluded/out-of-root sources, unknown ontology terms, conflicts, supersede cycles and dangling/non-effective edges before writes.
- AC3: Approved onboarding atomically persists canonical nodes/edges, preserves existing stores, rebuilds indexes deterministically and rolls back graph changes together with other onboarding changes.
- AC4: Empty or absent proposal remains a valid idempotent no-op; existing onboarding callers and current graph APIs continue to work.
- AC5: `knowledge-curator` explicitly owns discovery, proposal, validation, apply handoff, rebuild and ongoing graph maintenance; `project-onboarding` delegates graph semantics to it.
- AC6: Graph schema, onboarding answers contract, CLI/skill docs, specs and component contracts agree.
- AC7: Tests cover valid proposal, conflicts, invalid provenance, stale approval, rollback, idempotency, deterministic rebuild and retrieval after onboarding.
- AC8: Strict Health Check, documentation link validation, skill projection drift and repository audit have no ERROR or CRITICAL findings.

## Testing Strategy

- Unit: graph proposal parsing, canonical merge and provenance/ontology validation.
- Scenario: onboarding preview/apply/rollback/idempotency with nodes and edges.
- Contract: JSON schema, skill registry and canonical skill contents.
- Acceptance: end-to-end target project receives graph and retrieval can consume it.
- Regression: existing onboarding and knowledge tests remain green.

## Risks and Rollback

- Invalid or overbroad agent proposal: reject before target writes using schema and graph validation.
- Graph becoming an alternate truth source: preserve source provenance and document navigation-only semantics.
- Existing graph data overwritten: merge by stable IDs and reject conflicting payloads.
- Partial onboarding apply: reuse verified backup manifest and rollback over graph stores.
- Stale approval: recompute plan and require approval for the new hash.

## Implementation Tasks

### Task 1: Graph proposal contract and deterministic merge

**Files:**

- Modify: `orchestrator/knowledge.py`
- Create: `orchestrator/knowledge_bootstrap.py`
- Create: `config/schemas/knowledge-bootstrap.schema.json`
- Test: `tests/unit/test_knowledge.py`
- Test: `tests/scenarios/test_knowledge_bootstrap.py`

**Interfaces:**

- Input: target root, existing canonical nodes/edges, proposal mapping, merged ontology.
- Output: validated canonical JSONL content and effective graph summary without writing target files.

**Acceptance:** Valid proposal produces stable canonical records; invalid source, ontology, ID, endpoint and supersede inputs fail before writes; identical proposal is idempotent.

**Tests:** Focused unit and scenario tests for every rejection path and deterministic serialization.

- [ ] **Step 1:** Add proposal fixtures and failing validation tests.
- [ ] **Step 2:** Implement non-mutating validation and stable canonical merge.
- [ ] **Step 3:** Run focused knowledge unit and scenario tests.
- [ ] **Step 4:** Record evidence and hand the task to review.

### Task 2: Onboarding preview/apply integration

**Files:**

- Modify: `orchestrator/onboarding_workflow.py`
- Modify: `skills/system/project-onboarding/SKILL.md`
- Test: `tests/scenarios/test_agent_led_onboarding.py`

**Interfaces:**

- Input: validated `answers.knowledge_graph` proposal.
- Output: plan changes for canonical graph files, plan hash coverage, atomic apply, rollback and validation evidence.

**Acceptance:** Preview shows graph changes; approval hash covers them; apply writes and validates them; rollback removes/restores them; absent proposal is no-op.

**Tests:** Valid proposal, stale plan, forced validation failure, manual change protection and repeated onboarding.

- [ ] **Step 1:** Add onboarding scenario cases for proposal preview and apply.
- [ ] **Step 2:** Integrate proposal content into plan hash, backup and validation.
- [ ] **Step 3:** Run onboarding regression scenarios.
- [ ] **Step 4:** Record evidence and hand the task to review.

### Task 3: Knowledge Curator ownership and distribution

**Files:**

- Modify: `skills/bundled/knowledge-curator/SKILL.md`
- Modify: `registries/skills.json` only if contract metadata requires it
- Regenerate: `.codex/skills/knowledge-curator` and `.agents/skills/knowledge-curator` via canonical installer
- Test: `tests/contracts/test_skill_distribution.py`

**Interfaces:**

- Define the agent workflow for source inventory, proposal generation, approval handoff, graph application and rebuild.

**Acceptance:** The skill is the single owner of graph semantics and gives an agent enough deterministic instructions to produce the onboarding proposal without editing generated projections.

**Tests:** Registry, projection, drift and skill contract checks.

- [ ] **Step 1:** Expand the canonical skill workflow and proposal contract instructions.
- [ ] **Step 2:** Regenerate platform projections through the canonical installer.
- [ ] **Step 3:** Run skill registry and drift checks.
- [ ] **Step 4:** Record evidence and hand the task to review.

### Task 4: Documentation and public contracts

**Files:**

- Modify: `docs/specifications/orchestrator-specification.md`
- Modify: `docs/specifications/task-layer-specification.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `docs/guides/deployment-to-target-project-ru.md`
- Modify: `docs/guides/memory-and-knowledge-ru.md`
- Modify: `docs/plans/2026-07-27-roadmap-index.md`
- Modify: `config/documentation-map.json` if new owner mapping is required
- Test: `tests/unit/test_documentation.py`

**Acceptance:** Documentation describes onboarding graph preview, approval/hash, apply/rollback and skill ownership; all local links resolve.

**Tests:** Documentation impact and broken-local-link checks.

**Interfaces:**

- Consumes: final proposal contract and onboarding behavior.
- Produces: synchronized canonical specifications, guides and ownership map.

- [ ] **Step 1:** Update normative specifications and component contracts.
- [ ] **Step 2:** Update deployment and memory/knowledge guides and roadmap index.
- [ ] **Step 3:** Validate documentation impact and local links.
- [ ] **Step 4:** Record evidence and hand the task to review.

### Task 5: End-to-end validation and evidence

**Files:**

- Modify: `docs/validation/knowledge-curator-onboarding-report.md`
- Test: affected unit/scenario/contract/acceptance suites.

**Acceptance:** Test matrix maps AC1–AC8, full discovery passes, strict Health has no ERROR/CRITICAL, audit and security review pass, and operational artifacts remain ignored.

**Tests:** Approved `orchestrator.testing.run_test` commands with captured exit code and concise output.

**Interfaces:**

- Consumes: implementation, tests, canonical skill projections and documentation.
- Produces: validation report, acceptance evidence and release-ready workspace state.

- [ ] **Step 1:** Build the acceptance matrix for AC1–AC8.
- [ ] **Step 2:** Run focused, affected, full, Health and audit checks.
- [ ] **Step 3:** Run security and documentation gates.
- [ ] **Step 4:** Record evidence, review scope and finalize the task.

## Rollback Procedure

Before apply, retain the approved onboarding plan and backup manifest. If validation reports ERROR or CRITICAL, restore the complete manifest including graph files. If only the skill projection is stale, regenerate it from canonical `skills/bundled/knowledge-curator/SKILL.md`.
