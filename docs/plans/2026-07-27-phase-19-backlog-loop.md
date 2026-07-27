# Phase 19 — Backlog Loop Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Последовательно обрабатывать ограниченное число задач с commit-per-task и stop conditions.

**Architecture:** Loop вызывает claim и execution как black boxes, считает task/time/step budgets и останавливается на waiting_user, blocked или error. Tracked Task Context и implementation changes фиксируются до `complete`, после чего меняется только исключённый из Git registry.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/backlog.py`
- Create: `workflows/backlog-loop.yaml`
- Create: `tests/scenarios/test_backlog_loop.py`
- Modify: `config/defaults.yaml`

## Dependencies

- Фазы 3–13 и 17.

## Acceptance Criteria

- Ни один limit нельзя отключить неявно.
- Waiting/blocked немедленно останавливает loop.
- Каждая done task имеет отдельный implementation commit evidence.
- Переход `complete` после commit не создаёт tracked changes.

## Testing Strategy

- `python -m unittest tests.scenarios.test_backlog_loop -v` проходит.
- Scenario matrix покрывает empty, limit, waiting, blocked, failure и successful two-task run.
- Scenario проверяет чистый `git status --porcelain` после `commit → complete`, кроме явно создаваемого session report.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Бесконечный loop или неверная следующая задача; откат — hard maximum и fail closed при invalid registry.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/backlog.py`
- Create: `tests/scenarios/test_backlog_loop.py`
- Test: `tests/scenarios/test_backlog_loop.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 3–13 и 17.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Ни один limit нельзя отключить неявно.

**Tests:**

- `python -m unittest tests.scenarios.test_backlog_loop -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Ни один limit нельзя отключить неявно.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_backlog_loop -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Ни один limit нельзя отключить неявно.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `workflows/backlog-loop.yaml`
- Modify: `config/defaults.yaml`
- Test: `tests/scenarios/test_backlog_loop.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 3–13 и 17.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Waiting/blocked немедленно останавливает loop.

**Tests:**

- Scenario matrix покрывает empty, limit, waiting, blocked, failure и successful two-task run.

- [ ] **Step 1:** Добавить проверку для условия «Waiting/blocked немедленно останавливает loop.».
- [ ] **Step 2:** Запустить `Scenario matrix покрывает empty, limit, waiting, blocked, failure и successful two-task run.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Waiting/blocked немедленно останавливает loop.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
