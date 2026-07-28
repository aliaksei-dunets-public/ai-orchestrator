# English-First Project Language Migration Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Перевести внутренние и канонические артефакты проекта на английский язык, сохранить русскую и английскую версии пользовательских гайдов и инструкций, а Knowledge Graph сделать детерминированно English-only.

**Architecture:** Английский становится единственным каноническим языком кода, конфигурации, схем, registries, workflows, skills, specifications и maintainer-документации. Пользовательские материалы хранятся как связанные English canonical и Russian companion документы с явным language metadata; Knowledge Curator принимает только English sources и отклоняет русские или смешанные источники до записи в граф.

**Tech Stack:** Python 3.11+ standard library, JSON/JSONL, JSON Schema, YAML, Markdown, `unittest`, repository-local skill installer и Health Check.

## Global Constraints

- Не менять семантику Task Registry, Task Context, Memory или Knowledge Graph за пределами языковой политики и необходимой совместимости.
- Не ослаблять immutable security policies, source containment, provenance, approval и exclusion rules.
- `skills/` остаётся каноническим источником; `.codex/skills/` и `.agents/skills/` обновляются только через approved installer.
- Русские пользовательские companion-файлы сохраняются, но не являются canonical sources для graph retrieval, ontology proposals или graph provenance.
- Билингвальные документы не смешиваются в одном graph source: английская и русская версии имеют отдельные файлы и явную связь translation-of.
- Не коммитить `.orchestrator/tasks/tasks.json`, checkpoints, proposals, indexes, backups или releases.
- Сохранить существующие пользовательские изменения и совместимость с текущими API и release artifacts, если они не относятся к canonical source migration.

## Deliverables

- `config/language-policy.json` и runtime policy helper для классификации English/Russian/user-facing/internal документов.
- Английские canonical specifications, architecture/ADR, plans, validation reports, README, roadmap, skills, workflow text, CLI messages и test fixtures.
- Английская и русская версии пользовательских guides, README, migration и CLI instructions с проверяемыми translation links.
- English-only source-authority и Knowledge Curator policy с отказом для Russian, mixed-language и undocumented sources.
- Обновлённые schemas, registries, documentation map, Health Check, retrieval и regression/contract tests.
- Migration/release notes и финальная acceptance evidence без `ERROR` или `CRITICAL` в strict Health Check.

## Dependencies

- Completed `TASK-0002` full memory and knowledge lifecycle.
- Existing Knowledge Curator onboarding context `TASK-0003` and its graph proposal boundary.
- Existing canonical skill distribution and installer.
- Existing specifications in `docs/specifications/orchestrator-specification.md` and `docs/specifications/task-layer-specification.md` as the baseline to translate, not as future graph sources.

## Acceptance Criteria

- AC1: Language policy enumerates every canonical, bilingual and excluded document class and detects all repository files containing Cyrillic outside approved Russian companions/user text.
- AC2: Canonical code-facing artifacts, specifications, skills, workflows, registries, plans, tests, CLI messages and maintainer documents are English-only; references and generated projections agree.
- AC3: Every user-facing guide/instruction has an English canonical version and a Russian companion, reciprocal translation metadata, valid local links and equivalent command/contract content.
- AC4: Knowledge Curator and graph provenance accept English sources only; Russian companions, mixed-language documents, path aliases and missing language metadata are excluded or rejected deterministically before graph writes.
- AC5: Retrieval never returns graph nodes/edges sourced from Russian or mixed-language documentation, while empty or irrelevant stores remain a valid no-op.
- AC6: Existing Task Context, Memory, Knowledge Graph, onboarding, CLI and release contracts remain schema-compatible unless the language policy explicitly versions a changed field.
- AC7: Static language inventory, documentation/link checks, skill projection drift checks, focused tests, full discovery and strict Health Check pass.
- AC8: Migration notes explain canonical path changes, Russian companion policy, graph-source filtering, rollback and the compatibility window; release artifacts are regenerated rather than hand-edited.

## Testing Strategy

- Unit: language classification, metadata parsing, source authority and graph-source rejection.
- Contract: language-policy schema, canonical path inventory, documentation map, skill registry, task/specification contracts and graph retrieval policy.
- Scenario: bilingual documentation links, onboarding/knowledge proposal rejection, retrieval exclusion and empty-store no-op.
- Static: Cyrillic inventory, duplicate/missing translation detection, Markdown link validation and generated projection drift.
- Regression: affected memory, knowledge, onboarding, task creation, CLI, Health and release suites.
- Acceptance: full unittest discovery, acceptance matrix and `orchestrator health --strict --json` with no `ERROR` or `CRITICAL`.

## Risks and Rollback

- Risk: translation changes contract wording. Detection: specification/registry contract tests and semantic review. Rollback: restore the previous canonical document and keep the translation as a non-canonical companion until corrected.
- Risk: Russian documentation enters the graph through a stale node or bypass path. Detection: source-authority, provenance and retrieval exclusion tests. Rollback: reject/rebuild affected nodes and indexes from validated English canonical sources.
- Risk: path renames break links or downstream integrations. Detection: link checker, release tests and migration smoke tests. Rollback: retain compatibility redirects/aliases and restore the previous path mapping.
- Risk: generated projections drift from canonical skills. Detection: skill distribution contract and installer diff. Rollback: regenerate all projections from `skills/`.
- Risk: bilingual versions diverge. Detection: translation manifest, command/code-fence parity and review checklist. Rollback: mark the companion stale and block release until synchronized.

## Implementation Tasks

### Task 1: Language policy, inventory and canonical source manifest

**Files:**

- Create: `config/language-policy.json`
- Create: `orchestrator/language_policy.py`
- Create: `tests/unit/test_language_policy.py`
- Create: `tests/contracts/test_language_policy.py`
- Modify: `config/defaults.yaml`
- Modify: `config/documentation-map.json`
- Modify: `AGENTS.md`
- Modify: `.rgignore`

**Interfaces:**

- Consumes: repository-relative paths, Markdown frontmatter, language metadata and configured document classes.
- Produces: deterministic `language`, `document_class`, `canonical`, `translation_of`, `graph_eligible` and exclusion decisions used by documentation checks and graph retrieval.

**Acceptance:** The policy has schema-valid rules for English canonical files, Russian companions, bilingual user-document pairs, generated projections, operational/release exclusions and mixed/unknown documents. The inventory command reports exact files and fails on unclassified Cyrillic content outside approved classes.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.unit.test_language_policy tests.contracts.test_language_policy -v` passes and the inventory output is byte-for-byte stable on two runs.

- [ ] **Step 1:** Add contract fixtures for canonical English, Russian companion, mixed-language, generated, release and excluded paths.
- [ ] **Step 2:** Run the focused contract command and capture failures for missing policy and inventory behavior.
- [ ] **Step 3:** Implement path/metadata classification and deterministic repository inventory without changing graph writes.
- [ ] **Step 4:** Run focused policy tests and compare two inventory outputs.
- [ ] **Step 5:** Record the exact migration manifest and pass it to the translation tasks for review.

### Task 2: Translate canonical specifications, maintainer documentation and project text

**Files:**

- Create: `docs/specifications/orchestrator-specification.md`
- Create: `docs/specifications/task-layer-specification.md`
- Delete after link and compatibility verification: `docs/specifications/orchestrator-specification.md`
- Delete after link and compatibility verification: `docs/specifications/task-layer-specification.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `docs/adr/0001-core-boundaries.md`
- Modify: `docs/plans/2026-07-27-decisions.md`
- Modify: `docs/plans/2026-07-27-roadmap-index.md`
- Modify: `docs/plans/2026-07-27-phase-00-architecture-foundation.md`
- Modify: `docs/plans/2026-07-27-phase-01-repository-scaffold.md`
- Modify: `docs/plans/2026-07-27-phase-02-minimal-health-check.md`
- Modify: `docs/plans/2026-07-27-phase-03-session-reporter.md`
- Modify: `docs/plans/2026-07-27-phase-04-minimal-task-manager.md`
- Modify: `docs/plans/2026-07-27-phase-05-quick-task-creator.md`
- Modify: `docs/plans/2026-07-27-phase-06-standard-task-creator.md`
- Modify: `docs/plans/2026-07-27-phase-07-implementation-runner.md`
- Modify: `docs/plans/2026-07-27-phase-08-test-design-runner.md`
- Modify: `docs/plans/2026-07-27-phase-09-task-review.md`
- Modify: `docs/plans/2026-07-27-phase-10-code-review.md`
- Modify: `docs/plans/2026-07-27-phase-11-security-review.md`
- Modify: `docs/plans/2026-07-27-phase-12-approval-gates.md`
- Modify: `docs/plans/2026-07-27-phase-13-documentation-manager.md`
- Modify: `docs/plans/2026-07-27-phase-14-project-onboarding.md`
- Modify: `docs/plans/2026-07-27-phase-15-platform-profiles.md`
- Modify: `docs/plans/2026-07-27-phase-16-technology-profiles.md`
- Modify: `docs/plans/2026-07-27-phase-17-project-memory.md`
- Modify: `docs/plans/2026-07-27-phase-18-knowledge-graph.md`
- Modify: `docs/plans/2026-07-27-phase-19-backlog-loop.md`
- Modify: `docs/plans/2026-07-27-phase-20-orchestrator-audit.md`
- Modify: `docs/plans/2026-07-27-phase-21-controlled-self-improvement.md`
- Modify: `docs/plans/2026-07-27-phase-22-multi-project-validation.md`
- Modify: `docs/plans/2026-07-27-phase-23-stable-release-1-0.md`
- Modify: `docs/plans/2026-07-28-phase-24-skill-distribution.md`
- Modify: `docs/plans/2026-07-28-phase-25-memory-knowledge-full-lifecycle.md`
- Modify: `docs/plans/2026-07-28-skill-distribution-design.md`
- Modify: `docs/plans/2026-07-28-memory-knowledge-full-lifecycle-design.md`
- Modify: `docs/plans/2026-07-28-task-storage-layout-design.md`
- Modify: `docs/plans/2026-07-28-knowledge-curator-onboarding-design.md`
- Modify: `docs/plans/2026-07-28-knowledge-curator-onboarding.md`
- Modify: `docs/validation/roadmap-completion-report.md`
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `CHANGELOG.md`
- Modify: `tests/contracts/test_specifications.py`
- Modify: `tests/acceptance/test_roadmap_completion.py`

**Interfaces:**

- Consumes: current Russian normative specifications and existing English contract text.
- Produces: English canonical specification paths, updated references, preserved version/section semantics and English maintainer artifacts.

**Acceptance:** No canonical file in the manifest contains Russian prose; all links, versions, code fences, normative keywords and roadmap phase mappings remain intact; tests refer to English canonical paths and English contract markers.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_specifications tests.acceptance.test_roadmap_completion -v` passes, followed by the language inventory from Task 1.

- [ ] **Step 1:** Add English canonical specification fixtures and failing path/reference assertions.
- [ ] **Step 2:** Translate the listed normative and maintainer documents while preserving code blocks and contract identifiers.
- [ ] **Step 3:** Update source-of-truth references in `AGENTS.md`, README, tests and documentation map.
- [ ] **Step 4:** Run specification, roadmap, link and Cyrillic-inventory checks.
- [ ] **Step 5:** Review semantic parity against the Russian baseline and record the comparison evidence.

### Task 3: Bilingual user guides and instructions

**Files:**

- Create: `README.ru.md`
- Create: `docs/guides/deployment-to-target-project.md`
- Create: `docs/guides/development-environment.md`
- Create: `docs/guides/memory-and-knowledge.md`
- Modify: `docs/guides/deployment-to-target-project-ru.md`
- Modify: `docs/guides/development-environment-ru.md`
- Modify: `docs/guides/memory-and-knowledge-ru.md`
- Create: `docs/migrations/1.0.ru.md`
- Create: `docs/migrations/1.1.ru.md`
- Create: `docs/migrations/1.2.ru.md`
- Create: `docs/migrations/cli-contract.ru.md`
- Create: `skills/optional/python-code-review/README.md`
- Modify: `skills/optional/python-code-review/README.ru.md`
- Modify: `config/language-policy.json`
- Create: `tests/contracts/test_bilingual_documentation.py`
- Create: `tests/scenarios/test_bilingual_documentation.py`

**Interfaces:**

- English document is the canonical user-facing contract; Russian companion declares `language: ru` and `translation_of` the English path.
- Commands, paths, schema names, warnings, code fences and acceptance behavior are identical between companions unless a language-specific explanation is explicitly marked.

**Acceptance:** README, guides, migration instructions and optional user-facing skill documentation are available in both languages; every pair has reciprocal metadata/links, matching code fences and no broken local links. Russian companions are classified as non-canonical and non-graph-eligible.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_bilingual_documentation tests.scenarios.test_bilingual_documentation tests.unit.test_documentation -v` passes.

- [ ] **Step 1:** Add bilingual manifest and failing pair/link/code-fence parity checks.
- [ ] **Step 2:** Create English canonical documents from the current Russian guides and migration contracts.
- [ ] **Step 3:** Normalize existing Russian companions and add reciprocal language metadata without deleting user content.
- [ ] **Step 4:** Run link, parity, documentation-impact and language-policy checks.
- [ ] **Step 5:** Review user instructions for command correctness and hand the paired documents to documentation review.

### Task 4: English-only Knowledge Graph source policy

**Files:**

- Modify: `orchestrator/source_authority.py`
- Modify: `orchestrator/knowledge.py`
- Modify: `orchestrator/retrieval.py`
- Modify: `orchestrator/knowledge_cli.py`
- Modify: `config/defaults.yaml`
- Modify: `config/schemas/project-config.schema.json`
- Modify: `config/schemas/knowledge-node.schema.json`
- Modify: `config/schemas/knowledge-edge.schema.json`
- Modify: `skills/bundled/knowledge-curator/SKILL.md`
- Modify: `skills/system/project-onboarding/SKILL.md`
- Modify: `tests/unit/test_source_authority.py`
- Modify: `tests/unit/test_knowledge.py`
- Modify: `tests/unit/test_retrieval.py`
- Modify: `tests/contracts/test_retrieval_policy.py`
- Modify: `tests/scenarios/test_knowledge_lifecycle.py`
- Modify: `tests/scenarios/test_context_retrieval.py`
- Modify: `tests/scenarios/test_agent_led_onboarding.py`

**Interfaces:**

- `classify_source` and graph writes consume language-policy results and reject Russian, mixed-language, unknown-language and bilingual single-file documentation sources with stable error codes.
- Retrieval consumes effective graph records but returns only nodes/edges whose provenance is English canonical and current; the graph remains navigation-only and source documents remain canonical truth.
- `knowledge-curator` emits an English-only source inventory and never proposes nodes or edges from `*_ru.md`, `*.ru.md`, language-ru metadata, mixed files or excluded paths.

**Acceptance:** Direct graph API, CLI, onboarding proposal and retrieval paths all enforce the same English-only rule; legacy schema-version-1 records are readable only when their source passes the new policy or are deterministically marked stale/excluded; empty graph retrieval remains valid.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.unit.test_source_authority tests.unit.test_knowledge tests.unit.test_retrieval tests.contracts.test_retrieval_policy tests.scenarios.test_knowledge_lifecycle tests.scenarios.test_context_retrieval tests.scenarios.test_agent_led_onboarding -v` passes.

- [ ] **Step 1:** Add failing cases for Russian companion, mixed-language, missing metadata, path alias and English canonical sources.
- [ ] **Step 2:** Implement one shared language/source classification boundary for API, CLI, onboarding and retrieval.
- [ ] **Step 3:** Update Knowledge Curator instructions and project-onboarding handoff to use only English source inventory.
- [ ] **Step 4:** Run focused graph/retrieval/onboarding tests, including legacy-record compatibility and empty-store no-op.
- [ ] **Step 5:** Rebuild indexes from English canonical sources and verify deterministic output plus no Russian provenance.

### Task 5: Translate canonical skills, workflows, runtime messages and projections

**Files:**

- Modify: `skills/system/task-creator/SKILL.md`
- Modify: `skills/system/task-creator/references/plan-format.md`
- Modify: `skills/system/task-creator/references/task-context-contract.md`
- Modify: `skills/system/task-context-validator/SKILL.md`
- Modify: `skills/bundled/task-analyzer/SKILL.md`
- Modify: `skills/bundled/plan-writer/SKILL.md`
- Modify: `skills/bundled/plan-reviewer/SKILL.md`
- Modify: `skills/bundled/session-reporter/SKILL.md`
- Modify: `orchestrator/task_creation.py`
- Modify: `orchestrator/task_manager.py`
- Modify: `templates/task-context.md`
- Modify: `tests/contracts/test_task_context.py`
- Modify: `tests/unit/test_task_manager.py`
- Modify: `tests/scenarios/test_standard_task_creation.py`
- Regenerate: `.codex/skills/` and `.agents/skills/` through the canonical installer.

**Interfaces:**

- Agent skill descriptions, task headings, validator errors and runtime user-facing messages use English identifiers and prose while preserving machine-readable schema keys and CLI exit codes.
- Generated projections are byte-equivalent to their canonical skill sources under the existing distribution contract.

**Acceptance:** No canonical skill, workflow instruction or runtime message contains Russian prose; all registered skill IDs, frontmatter, task headings, validator behavior and projection hashes remain valid.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_task_context tests.contracts.test_skill_distribution tests.unit.test_task_manager tests.scenarios.test_standard_task_creation -v` passes.

- [ ] **Step 1:** Add language assertions to skill, task-context and runtime-message tests.
- [ ] **Step 2:** Translate canonical system/bundled skills and task/runtime prose without changing contract keys.
- [ ] **Step 3:** Regenerate projections with the approved installer and update registries only when metadata changes.
- [ ] **Step 4:** Run distribution, task, scenario and Cyrillic-inventory checks.
- [ ] **Step 5:** Review generated diffs and document installer evidence.

### Task 6: Health, documentation ownership and release migration

**Files:**

- Modify: `orchestrator/health.py`
- Modify: `orchestrator/documentation.py`
- Modify: `config/documentation-map.json`
- Modify: `tests/unit/test_health.py`
- Modify: `tests/unit/test_documentation.py`
- Modify: `tests/scenarios/test_memory_knowledge_health.py`
- Modify: `tests/acceptance/test_release.py`
- Create: `docs/migrations/1.3.md`
- Modify: `pyproject.toml`
- Modify: `orchestrator/__init__.py`
- Modify: `CHANGELOG.md`

**Interfaces:**

- Health consumes the language manifest, translation links, canonical source inventory and graph provenance, and emits stable findings for missing pairs, mixed sources, stale references and Russian graph provenance.
- Documentation Manager maps changed English canonical contracts to both English and Russian user-facing companions; release metadata identifies the language-policy migration.

**Acceptance:** Health detects all language-policy violations without traceback; documentation impact includes both members of every user-document pair; migration 1.2→1.3 documents path aliases, rollback, graph rebuild and compatibility behavior; release tests pass.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.unit.test_health tests.unit.test_documentation tests.scenarios.test_memory_knowledge_health tests.acceptance.test_release -v` passes.

- [ ] **Step 1:** Add failing Health and release cases for missing translations, invalid metadata and Russian graph provenance.
- [ ] **Step 2:** Implement bounded language findings and documentation-owner mapping.
- [ ] **Step 3:** Write migration/rollback notes and synchronize version metadata/changelog.
- [ ] **Step 4:** Run focused checks, local-link validation and release artifact generation.
- [ ] **Step 5:** Review the migration against the previous release and record compatibility evidence.

### Task 7: Full acceptance, security review and final evidence

**Files:**

- Create: `docs/validation/english-first-language-migration-report.md`
- Modify: `tests/contracts/test_specifications.py`
- Modify: `tests/contracts/test_retrieval_policy.py`
- Modify: `tests/acceptance/matrix.json`
- Test: `tests/unit/test_language_policy.py`
- Test: `tests/unit/test_source_authority.py`
- Test: `tests/unit/test_knowledge.py`
- Test: `tests/unit/test_retrieval.py`
- Test: `tests/unit/test_health.py`
- Test: `tests/unit/test_documentation.py`
- Test: `tests/contracts/test_language_policy.py`
- Test: `tests/contracts/test_bilingual_documentation.py`
- Test: `tests/contracts/test_specifications.py`
- Test: `tests/contracts/test_retrieval_policy.py`
- Test: `tests/scenarios/test_bilingual_documentation.py`
- Test: `tests/scenarios/test_knowledge_lifecycle.py`
- Test: `tests/scenarios/test_context_retrieval.py`
- Test: `tests/acceptance/test_release.py`

**Interfaces:**

- Consumes: language manifest, translated canonical sources, bilingual pairs, graph policy, migration notes and generated projections.
- Produces: AC1–AC8 evidence, security/documentation review results, full test status and strict Health result.

**Acceptance:** All acceptance criteria map to executable checks; full discovery, acceptance matrix, security review, documentation checks and strict Health complete with no `ERROR` or `CRITICAL`; no untracked operational artifacts or accidental Russian graph provenance remain.

**Tests:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` and `.\.venv\Scripts\python.exe -m orchestrator health --strict --json` pass; run the repository's approved security and release validation commands and capture exit codes.

- [ ] **Step 1:** Map each AC to focused and full executable checks.
- [ ] **Step 2:** Run focused suites, full discovery, acceptance matrix and strict Health.
- [ ] **Step 3:** Run security, documentation, projection-drift and release reviews.
- [ ] **Step 4:** Inspect graph provenance and bilingual manifest for policy violations.
- [ ] **Step 5:** Write final validation evidence and hand the implementation to Task Review and Code Review.

## Rollback Procedure

Before each path or schema migration, record the language manifest digest and preserve the previous canonical path mapping. If semantic, link, Health or graph-provenance validation fails, restore the prior canonical documents and mapping, rebuild graph indexes from the last validated English sources, and retain new translations only outside canonical retrieval until corrected. Regenerate projections from the restored canonical skills; do not hand-edit generated trees.
