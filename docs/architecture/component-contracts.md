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

- Входы: валидированный Task Context или допустимая status transition.
- Выходы: локальный Task Registry result, ссылка `contexts/<TASK-ID>.md` на Task Context и canonical checkpoint path `checkpoints/<TASK-ID>.checkpoint.lock`.
- Владеет: вычислением безопасных путей Task Context/checkpoint и удалением checkpoint после перехода в `done`; `cancelled` checkpoint сохраняет.
- Не владеет: planning, implementation, reviews, commits и documentation.

## Task Execution Workflow

- Входы: claimed Task Context, capabilities и limits.
- Выходы: Execution Record, bounded test/review evidence, optional numeric telemetry и запрос status transition.
- Не владеет: правила переходов Task Manager.

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
