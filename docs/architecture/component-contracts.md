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
- Выходы: локальный Task Registry result и ссылка на Task Context.
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

## Skills

- Входы: данные и capabilities, явно объявленные конкретным skill contract.
- Выходы: структурированный результат, evidence или запрос следующего допустимого workflow step.
- Не владеет: orchestration state, Task Registry и platform-specific tool lifecycle.
- Coordinator skill может маршрутизировать атомарные skills, но не дублирует их domain logic.
- Канонический source находится в `skills/`; platform projection проверяется на drift.

## Memory and Knowledge

- Входы: подтверждённые observations, decisions, lessons и provenance.
- Выходы: versioned records и navigation indexes.
- Не превращает observation в instruction автоматически.
