# Post-Task Finalization Enforcement Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Устранить разрыв между декларативным workflow и runtime, сделав проверяемую финализацию документации, графа знаний и памяти обязательным условием завершения каждой задачи.

**Architecture:** Новый `TaskFinalizationCoordinator` выполняется после implementation/review/security gates и до task commit. Он вычисляет documentation impact, принимает и валидирует решение Knowledge Curator, создаёт и продвигает допустимые memory proposals, затем выпускает привязанный к Task Context и changed paths `FinalizationReceipt`; Task Manager проверяет структурную целостность receipt, не подменяя semantic review. Session Reporter остаётся post-loop механизмом: после остановки backlog он формирует отчёт и approval-gated session memory proposals, но не является условием статуса отдельной задачи `done`.

**Tech Stack:** Python 3.11+ standard library, JSON/JSON Schema, JSONL, YAML workflows, Markdown, `unittest`, temporary Git repositories.

## Global Constraints

- Нельзя переводить задачу в `done` без успешного `FinalizationReceipt`, созданного для текущих Task Context revision/baseline hash и changed paths digest.
- Documentation gate обязан либо подтвердить обновление каждого затронутого canonical document, либо сохранить явное обоснование `not_applicable`; local links должны быть валидны.
- Knowledge gate обязан получить валидный proposal Knowledge Curator; пустой proposal является допустимым доказательством отсутствия graph-relevant изменений.
- Непустой knowledge proposal применяется только через существующие provenance, ontology, secret-redaction, conflict и supersede checks; derived indexes остаются ignored и воспроизводимыми.
- Memory gate создаёт proposals с project-relative provenance и текущим source digest. Автопродвижение допускается только правилами source authority; instruction и non-authoritative candidates остаются approval-gated.
- Pending approval не маскируется как успешное продвижение: finalization возвращает `waiting_user` либо фиксирует approved non-promotion disposition, если сохранение proposal без promotion разрешено выбранной policy.
- Task Manager проверяет receipt schema, digest binding и успешные gate statuses, но не оценивает качество документации, graph semantics или memory content.
- Existing `done` records остаются читаемыми; новое требование применяется к последующим вызовам `complete`.
- `cancel` не требует finalization; failed/waiting tasks сохраняют checkpoint и незавершённый receipt для recovery.
- Operational receipts, temporary proposals, checkpoints and indexes не попадают в Git; canonical documentation, memory and knowledge stores остаются tracked according to existing ownership rules.
- Изменение не должно ослаблять security review, commit-per-task, workspace ownership, isolated worktree integration или approval policies.

## Deliverables

- Runtime `TaskFinalizationCoordinator` и versioned `FinalizationReceipt`.
- Documentation, knowledge and memory gate adapters с deterministic disposition/evidence.
- Completion guard в Task Manager и CLI, интегрированный в serial и isolated-parallel backlog paths.
- Post-loop session report и session-memory proposal orchestration без изменения per-task `done` semantics.
- Workflow, schema, Health, skill, specification, ADR, migration and guide updates.
- Unit, contract, scenario, recovery, security and regression evidence.

## Dependencies

- `TASK-0002` memory/knowledge lifecycle, `TASK-0003` Knowledge Curator onboarding и `TASK-0005` worktree-aware execution завершены.
- `TASK-0004` меняет язык canonical sources и пересекается со specifications/workflows; `TASK-0006` следует выполнять после `TASK-0004` либо в отдельной последовательной ветке с явным rebase/review.
- Existing `orchestrator.documentation`, `orchestrator.knowledge_bootstrap`, `orchestrator.memory`, `orchestrator.session_report`, Execution Runner and Task Manager contracts.

## Acceptance Criteria

- AC1: Каждый новый вызов `complete` требует receipt, связанный с task ID, текущей revision/baseline hash, changed paths digest и завершённым execution checkpoint; missing, stale, malformed или unsuccessful receipt отклоняется стабильной ошибкой.
- AC2: Documentation gate детерминированно вычисляет impact из `config/documentation-map.json`, требует update либо explicit non-applicability для каждого canonical document и блокируется на broken local links.
- AC3: Knowledge gate принимает proposal schema version 1, считает пустой proposal валидным no-op, а непустой применяет атомарно с provenance, ontology, secret, duplicate, conflict, supersede и effective-graph validation.
- AC4: Memory gate создаёт idempotent proposals из task evidence, автоматически продвигает только разрешённые authoritative observation/decision/lesson candidates и требует hash-bound approval для instruction/non-authoritative sources.
- AC5: Serial и isolated-parallel backlog вызывают finalization после execution gates и до commit; failure/waiting_user прекращает commit/complete, а успешный receipt проходит через commit/integration в assigned workspace.
- AC6: После остановки backlog Session Reporter формирует secret-safe report и session-sourced memory proposals; отсутствие отчёта не изменяет уже установленный task status, а promotion остаётся approval-gated.
- AC7: Existing completed registry entries and read/list/show operations remain compatible; cancellation and recovery preserve their current semantics.
- AC8: CLI, workflows, schemas, canonical skills, specifications, component contracts, ADR, migration, guide and documentation map describe one ordering and ownership model.
- AC9: Focused and full regression tests pass, strict Health has no `ERROR`/`CRITICAL`, repository audit is clean and security review finds no receipt bypass, path escape, secret leakage or unsafe canonical write.

## Testing Strategy

- Unit: receipt canonicalization/digests, documentation dispositions, empty/non-empty graph proposals, memory promotion policy, idempotency, redaction and stale source detection.
- Contract: JSON schema, Task Manager completion API/CLI, workflow ordering, skill ownership, documentation map and legacy registry readability.
- Scenario: successful serial finalization, documentation N/A, graph update, memory auto-promotion, pending approval, stale receipt, interrupted recovery and isolated worktree integration.
- Git sandbox: verify finalization changes are committed before `done`, operational receipts remain ignored and post-complete cleanup creates no tracked changes.
- Regression: Task Manager, Execution Runner, Backlog Loop, Session Reporter, memory/knowledge CLI, onboarding and release acceptance suites.
- Security: forged/stale receipt, path traversal, proposal source escape, secret-like graph labels/memory content, approval replay and worktree ownership mismatch.

## Risks and Rollback

- Risk: receipt becomes a caller-supplied bypass token. Detection: negative tests with forged gate statuses and altered source/context digests. Rollback: fail closed and require coordinator-produced schema-valid evidence bound to the current checkpoint.
- Risk: finalization writes canonical graph or memory before a later gate fails. Detection: transactional scenario tests. Rollback: prepare every write first, apply atomically only after all validation succeeds, and use append-only disable/supersede recovery where canonical history already changed.
- Risk: mandatory memory approval blocks unattended backlog runs. Detection: candidates classified as non-authoritative/instruction. Rollback: stop in `waiting_user`, preserve proposal and checkpoint, then resume with hash-bound approval; never silently promote.
- Risk: duplicate memory/knowledge records on retry. Detection: repeated finalization with identical inputs. Rollback: content/source digests and stable proposal IDs make retries idempotent.
- Risk: TASK-0004 causes documentation conflicts. Detection: freshness/revision mismatch or changed canonical paths. Rollback: execute serially after TASK-0004 and regenerate the documentation impact set.
- Risk: release compatibility breaks existing completed tasks. Detection: legacy registry fixtures. Rollback: require receipts only for new completion transitions while preserving read-only compatibility for historical `done` entries.

## Implementation Tasks

### Task 1: Finalization contract, receipt schema and checkpoint binding

**Files:**

- Create: `orchestrator/finalization.py`
- Create: `config/schemas/task-finalization.schema.json`
- Modify: `config/schemas/task-registry.schema.json`
- Modify: `orchestrator/execution.py`
- Create: `tests/contracts/test_task_finalization_contract.py`
- Create: `tests/unit/test_finalization.py`

**Interfaces:**

- Consumes: task ID, registered Task Context path/revision/baseline hash, execution checkpoint, normalized changed paths, documentation dispositions, knowledge proposal and memory candidates.
- Produces: schema-version-1 `FinalizationReceipt` containing input digests, per-gate status/evidence, pending approvals, canonical write digests and `ready_for_completion`.

**Acceptance:**

- Receipt serialization and digesting are deterministic; unknown fields, missing gates, stale context/checkpoint, duplicate paths and caller-provided success without matching evidence fail closed.
- Historical registry records without finalization metadata remain readable, while new completion metadata validates against the updated schema.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_task_finalization_contract tests.unit.test_finalization -v` passes.

- [ ] **Step 1:** Add failing tests for valid, missing, forged, stale and legacy receipt states.
- [ ] **Step 2:** Run the focused command and confirm the expected contract failures.
- [ ] **Step 3:** Implement canonical models, digest binding and checkpoint validation.
- [ ] **Step 4:** Run focused tests plus `tests.unit.test_execution` and `tests.unit.test_task_manager`.
- [ ] **Step 5:** Record the accepted receipt/checkpoint contract for coordinator adapters.

### Task 2: Documentation finalization gate

**Files:**

- Modify: `orchestrator/documentation.py`
- Modify: `orchestrator/finalization.py`
- Modify: `config/documentation-map.json`
- Modify: `tests/unit/test_documentation.py`
- Modify: `tests/unit/test_finalization.py`

**Interfaces:**

- Consumes: normalized changed paths, documentation map and per-document disposition `{updated | not_applicable, reason, evidence_ref}`.
- Produces: complete sorted impact/evidence records and a blocking result for missing ownership evidence or broken local links.

**Acceptance:**

- Every impacted canonical document has exactly one disposition; `updated` requires the document in changed paths, `not_applicable` requires a non-empty reason, generator-owned files are routed to their owner, and all inspected Markdown links resolve inside the repository.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.unit.test_documentation tests.unit.test_finalization -v` passes.

- [ ] **Step 1:** Add failing tests for missing, duplicate, false-updated, unsupported-owner and broken-link dispositions.
- [ ] **Step 2:** Confirm the failures against current documentation helpers.
- [ ] **Step 3:** Implement deterministic documentation gate evaluation and bounded evidence.
- [ ] **Step 4:** Run focused tests and documentation contract regression.
- [ ] **Step 5:** Update the map for all new finalization runtime/public interfaces.

### Task 3: Knowledge and memory finalization gates

**Files:**

- Modify: `orchestrator/finalization.py`
- Modify: `orchestrator/knowledge_bootstrap.py`
- Modify: `orchestrator/memory.py`
- Modify: `orchestrator/session_report.py`
- Create: `tests/scenarios/test_task_finalization_memory_knowledge.py`
- Modify: `tests/unit/test_session_report.py`
- Modify: `tests/scenarios/test_memory_knowledge_cli.py`

**Interfaces:**

- Knowledge consumes schema-version-1 proposal plus ontology/canonical store paths; produces `empty`, `applied` or blocking disposition and rebuilt index digest.
- Memory consumes secret-safe task candidates with source provenance; produces stable proposal IDs, promoted entry IDs and pending approval hashes under existing source-authority rules.

**Acceptance:**

- Empty graph proposal succeeds without canonical writes; non-empty proposals are prepared and applied atomically and idempotently.
- Memory retries do not duplicate proposals/entries; authoritative candidates follow existing auto-promotion policy, while instructions and session/non-authoritative candidates cannot bypass approval.
- A failure in either gate leaves the receipt not ready and preserves recoverable proposal/evidence state without partial untracked canonical corruption.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_task_finalization_memory_knowledge tests.unit.test_session_report tests.scenarios.test_memory_knowledge_cli -v` passes.

- [ ] **Step 1:** Add failing scenarios for empty/applied/conflicting graph proposals and memory authority/approval/idempotency.
- [ ] **Step 2:** Confirm current helpers are not orchestrated and expose the expected failures.
- [ ] **Step 3:** Extract reusable atomic graph apply and idempotent memory proposal operations, then connect them to finalization.
- [ ] **Step 4:** Run focused memory/knowledge, onboarding and migration regressions.
- [ ] **Step 5:** Preserve provenance, proposal hashes, source digests and resulting store/index digests in receipt evidence.

### Task 4: Task Manager, CLI and backlog enforcement

**Files:**

- Modify: `orchestrator/task_manager.py`
- Modify: `orchestrator/task_cli.py`
- Modify: `orchestrator/cli.py`
- Modify: `orchestrator/backlog.py`
- Modify: `orchestrator/execution.py`
- Modify: `workflows/task-execution.yaml`
- Modify: `workflows/backlog-loop.yaml`
- Modify: `tests/unit/test_task_manager.py`
- Modify: `tests/scenarios/test_task_cli.py`
- Modify: `tests/scenarios/test_backlog_loop.py`
- Modify: `tests/scenarios/test_parallel_task_claim.py`
- Modify: `tests/scenarios/test_worktree_sandbox.py`

**Interfaces:**

- `finalize-task` consumes the assigned workspace evidence and returns a receipt or `waiting_user`/`blocked`/`failed`.
- `complete` consumes receipt evidence plus existing commit/workspace evidence; it stores the receipt digest and rejects missing/stale/non-ready receipts.
- Backlog callbacks become execution → finalization → commit → integration where applicable → complete.

**Acceptance:**

- Neither direct API/CLI completion nor serial/isolated backlog can skip finalization.
- A finalization stop condition prevents commit and `done`, preserves checkpoint/worktree/proposals, and resumes idempotently.
- Sequence-1 main and sequence-2+ worktree ownership and commit/integration checks remain unchanged.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.unit.test_task_manager tests.scenarios.test_task_cli tests.scenarios.test_backlog_loop tests.scenarios.test_parallel_task_claim tests.scenarios.test_worktree_sandbox -v` passes.

- [ ] **Step 1:** Add failing bypass, ordering, stop/resume and worktree receipt tests.
- [ ] **Step 2:** Confirm current `complete` and backlog paths bypass all three finalization gates.
- [ ] **Step 3:** Integrate coordinator callbacks, receipt verification and stable CLI errors.
- [ ] **Step 4:** Run focused serial/parallel regressions in temporary Git repositories.
- [ ] **Step 5:** Verify operational receipt/checkpoint cleanup leaves no tracked post-commit changes.

### Task 5: Post-loop session finalization, Health and canonical instructions

**Files:**

- Modify: `orchestrator/backlog.py`
- Modify: `orchestrator/session_report.py`
- Modify: `orchestrator/health.py`
- Modify: `skills/system/implementation-runner/SKILL.md`
- Modify: `skills/system/documentation-manager/SKILL.md`
- Modify: `skills/system/knowledge-curator/SKILL.md`
- Modify: `skills/system/memory-manager/SKILL.md`
- Modify: `skills/system/session-reporter/SKILL.md`
- Modify: `workflows/backlog-loop.yaml`
- Create: `tests/scenarios/test_post_loop_session_finalization.py`
- Modify: `tests/unit/test_health.py`
- Modify: `tests/contracts/test_skill_distribution_contract.py`

**Interfaces:**

- Backlog loop emits a bounded session summary after a terminal loop status and invokes Session Reporter once.
- Session Reporter writes a secret-safe report and idempotent approval-gated proposals sourced from that report.
- Health reports malformed/stale finalization receipts, pending approval information and canonical/projection drift without treating legitimate pending approval as silent success.

**Acceptance:**

- Session reporting happens once after loop stop, does not retroactively change task status and does not auto-promote session-sourced candidates.
- Canonical skills describe ownership and ordering consistently; generated platform projections are regenerated through their owner and pass drift checks.

**Tests:** `.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_post_loop_session_finalization tests.unit.test_health tests.contracts.test_skill_distribution_contract -v` passes.

- [ ] **Step 1:** Add failing post-loop, redaction, idempotency, Health and skill-contract tests.
- [ ] **Step 2:** Confirm declarative `post_task` steps currently have no runtime invocation.
- [ ] **Step 3:** Implement post-loop orchestration and Health findings, then update canonical skill sources.
- [ ] **Step 4:** Regenerate managed skill projections with the repository owner command and run drift checks.
- [ ] **Step 5:** Verify pending approvals remain visible/recoverable and do not masquerade as canonical memory.

### Task 6: Specifications, migration and acceptance evidence

**Files:**

- Modify: `docs/specifications/orchestrator-specification-ru.md`
- Modify: `docs/specifications/task-layer-specification-ru.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `docs/guides/memory-and-knowledge-ru.md`
- Modify: `docs/migrations/cli-contract.md`
- Create: `docs/migrations/1.4-task-finalization.md`
- Create: `docs/adr/0004-task-finalization-receipts.md`
- Create: `docs/validation/task-finalization-report.md`
- Modify: `tests/acceptance/test_release.py`

**Interfaces:**

- Documents define exact execution → finalization → commit → complete → post-loop-report ordering, gate ownership, receipt lifecycle, approval behavior, recovery and rollback.
- Acceptance report maps AC1–AC9 to commands, outputs and evidence paths.

**Acceptance:**

- Specifications, workflows, CLI, schemas, skills and component contracts agree; migration explains existing `done` compatibility and new `complete` requirements.
- Full tests pass, strict Health has no `ERROR`/`CRITICAL`, audit is clean and security review approves the raw diff/staged scope.

**Tests:** `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` and `.\.venv\Scripts\orchestrator health --strict` pass.

- [ ] **Step 1:** Add acceptance assertions for release contents, workflow order and completion migration.
- [ ] **Step 2:** Update canonical documentation through Documentation Manager and validate all mapped links.
- [ ] **Step 3:** Run focused suites, full regression, strict Health and repository audit.
- [ ] **Step 4:** Run deterministic and semantic security review for receipt bypass, secret leakage, approvals and path handling.
- [ ] **Step 5:** Record AC1–AC9 evidence, remaining limitations and rollback commands in the validation report and Task Context Execution Record.
