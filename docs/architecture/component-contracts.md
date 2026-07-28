# Контракты компонентов

## Core

- Входы: defaults, policies, registries, profiles, Project Context и task-specific instructions.
- Выходы: выбранный workflow, структурированные findings и итог сессии.
- Не владеет: project-specific business rules и platform-specific tool syntax.

## Task Creator

- Входы: пользовательский запрос, Project Context, profiles и repository evidence.
- Выходы: валидированный Task Context draft.
- Не владеет: Task Registry и execution status.

## Task Manager

- Входы: валидированный Task Context, допустимая status transition и для
  `complete` — schema-valid finalization receipt.
- Выходы: локальный Task Registry result, ссылка `contexts/<TASK-ID>.md` на Task Context, canonical checkpoint path `checkpoints/<TASK-ID>.checkpoint.lock` и digest успешной финализации в terminal record.
- Владеет: вычислением безопасных путей Task Context/checkpoint и удалением checkpoint после перехода в `done`; `cancelled` checkpoint сохраняет.
- Не владеет: planning, implementation, semantic reviews, commits, documentation,
  graph curation или memory content. Он проверяет только receipt schema,
  hash/freshness binding и `ready_for_completion`.
- В `serial` режиме сохраняет один active slot. В `isolated_parallel` хранит
  run/sequence/workspace/branch/base/commit assignment и допускает несколько
  active задач только при уникальных workspace и соблюдении `max_workers`.
- Все registry mutations сериализуются `RegistryLock`; stale lock
  восстанавливается только после проверки отсутствия live owner.

## Worktree Manager

- Входы: Git repository root, валидированный worktree root, task ID, run ID и
  полный base commit.
- Выходы: task-owned branch/worktree assignment, ownership inspection,
  commit verification, explicit integration и guarded cleanup.
- Владеет: безопасными Git argument arrays, path/branch derivation и ownership
  manifest.
- Не владеет: Task Registry status, автоматическим разрешением merge conflicts
  или удалением failed worktrees.

## Task Execution Workflow

- Входы: claimed Task Context, capabilities и limits.
- Выходы: Execution Record, bounded test/review evidence, optional numeric
  telemetry, Task Finalization receipt и запрос status transition.
- Не владеет: правила переходов Task Manager.
- Проверяет, что Task Context и checkpoint находятся внутри назначенного
  workspace; silent workspace switching запрещён.

## Task Finalization Coordinator

- Входы: task ID, текущие context revision/baseline hash, completed checkpoint,
  normalized changed paths, documentation dispositions, Knowledge Curator
  proposal и memory candidates.
- Выходы: versioned receipt с digest binding, status/evidence каждого gate,
  canonical store digests, promoted memory IDs и pending approval hashes.
- Владеет: порядком documentation → knowledge → memory, deterministic
  validation, policy-safe canonical apply и idempotent recovery.
- Не владеет: качеством semantic content. Documentation Manager, Knowledge
  Curator и Memory Manager остаются владельцами своих решений.
- Пустой graph proposal и пустой список memory candidates являются допустимыми
  явными no-op. Отсутствие решения или disposition не является no-op.
- Receipt хранится как ignored operational state в
  `.orchestrator/tasks/finalization/<TASK-ID>.json`; Task Registry сохраняет
  только его digest и changed-paths digest.

## Telemetry

- Входы: числовые runtime counters и identifiers без prompt/tool/evidence payload.
- Выходы: project-local JSONL events и агрегированный CLI summary.
- Не владеет: Task Registry status, Task Context, review verdict и постоянная память.

## Workflow Engine

- Входы: declarative workflow, capability registry и current workflow state.
- Выходы: следующий допустимый step, gate или terminal result.
- Не владеет: domain logic skills.

## Project Onboarding

- Входы: путь к каноническому onboarding skill, target root, repository evidence и versioned answers.
- Выходы до approval: структурированные вопросы либо полный preview с `plan_hash`, target fingerprint, validation steps и rollback manifest.
- Выходы после approval: `completed`, `rolled_back` или `rollback_failed` и bounded report.
- Владеет: `.orchestrator/config.json`, managed Project Context blocks, onboarding session/report/backups, ограниченными platform bootstrap и Git ignore blocks.
- Не владеет: пользовательским текстом вне ownership-маркеров, platform UI, загрузкой core, глобальной Python-средой и ослаблением immutable policies.
- Core используется на месте как Git submodule или скопированный пакет; относительный `core_path` предпочтителен, внешний абсолютный путь требует явного ответа.
- Platform profile объявляет instruction target, repository skill projection, interaction и approval adapters; platform-name branching в Core запрещён.
- Apply допускается только для неизменившегося fingerprint и утверждённого `plan_hash`; `ERROR` или `CRITICAL` после записи запускает заранее разрешённый проверяемый rollback.

## Skills

- Входы: данные и capabilities, явно объявленные конкретным skill contract.
- Выходы: структурированный результат, evidence или запрос следующего допустимого workflow step.
- Не владеет: orchestration state, Task Registry и platform-specific tool lifecycle.
- Coordinator skill может маршрутизировать атомарные skills, но не дублирует их domain logic.
- Канонический source находится в `skills/system`, `skills/bundled` или `skills/optional`; project-owned source находится в `.orchestrator/project-skills`.
- System и bundled skills входят в default projection; optional skills включаются только явным project selection после approval.
- Поставляемый source неизменяем; project-owned adaptation получает новый уникальный ID.
- Installer публикует projection атомарно, а Health Check проверяет selection, коллизии и drift.

## Memory and Knowledge

- Входы: proposal, project-relative provenance и source digest; для instruction
  и non-authoritative source — approval, привязанный к proposal/source hashes.
- Выходы: tracked canonical entries/events/approvals, ontology/nodes/edges и
  воспроизводимые derived indexes.
- Target project владеет canonical stores; Core владеет только runtime,
  схемами, immutable Core ontology и policy.
- Effective state исключает disabled, superseded, stale и secret-like records.
- Retrieval выполняет deterministic lexical selection и bounded graph traversal
  без embeddings или внешней базы данных.
- Не превращает observation в instruction автоматически и не использует graph
  как второй источник истины.
- Task finalization автоматически продвигает только authoritative
  observation/decision/lesson proposals. Instruction и non-authoritative source
  требуют hash-bound approval; отсутствие решения возвращает `waiting_user`.
- Session Reporter выполняется один раз после остановки execution/backlog loop.
  Его candidates остаются proposals и не меняют уже установленный task status.

`knowledge-curator` дополнительно владеет read-only source inventory, onboarding
`knowledge_graph` proposal, provenance/ontology validation, canonical graph merge
и deterministic index rebuild. `project-onboarding` владеет только target
bootstrap, preview, approval, apply и rollback boundary.
