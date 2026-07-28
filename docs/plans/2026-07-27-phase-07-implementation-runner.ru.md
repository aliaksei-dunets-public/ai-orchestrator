# Phase 07 — Implementation Runner Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Последовательно выполнять утверждённый план с freshness gate, лимитами и evidence.

**Architecture:** Runner интерпретирует tasks плана, вызывает platform adapter и записывает только дельты Execution Record. Он останавливается на scope change, approval need или исчерпании лимита.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/execution.py`
- Create: `skills/implementation-runner/SKILL.md`
- Create: `workflows/task-execution.yaml`
- Create: `tests/scenarios/test_implementation_runner.py`

## Dependencies

- Фазы 4 и 6.

## Acceptance Criteria

- Runner не начинает stale context.
- Каждый выполненный шаг имеет evidence и bounded retry.
- Scope change переводит задачу в waiting_user, а не исправляет baseline.

## Testing Strategy

- `python -m unittest tests.scenarios.test_implementation_runner -v` проходит.
- Sandbox scenario проверяет restart после прерванного шага.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Повтор side effect после restart; откат — остановить runner и возобновить только с последнего подтверждённого checkpoint.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/execution.py`
- Create: `workflows/task-execution.yaml`
- Test: `tests/scenarios/test_implementation_runner.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 4 и 6.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Runner не начинает stale context.

**Tests:**

- `python -m unittest tests.scenarios.test_implementation_runner -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Runner не начинает stale context.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_implementation_runner -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Runner не начинает stale context.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/implementation-runner/SKILL.md`
- Create: `tests/scenarios/test_implementation_runner.py`
- Test: `tests/scenarios/test_implementation_runner.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 4 и 6.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждый выполненный шаг имеет evidence и bounded retry.

**Tests:**

- Sandbox scenario проверяет restart после прерванного шага.

- [ ] **Step 1:** Добавить проверку для условия «Каждый выполненный шаг имеет evidence и bounded retry.».
- [ ] **Step 2:** Запустить `Sandbox scenario проверяет restart после прерванного шага.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждый выполненный шаг имеет evidence и bounded retry.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
