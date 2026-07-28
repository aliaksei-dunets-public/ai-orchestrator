# Phase 00 — Архитектурная основа Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Зафиксировать проверяемые границы, контракты и решения архитектуры оркестратора.

**Architecture:** Спецификации остаются нормативным слоем, а спорные решения фиксируются ADR. Контракты получают стабильные имена и владельцев до появления кода.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Modify: `docs/specifications/orchestrator-specification.md`
- Modify: `docs/specifications/task-layer-specification.md`
- Create: `docs/adr/0001-core-boundaries.md`
- Create: `docs/architecture/component-contracts.md`

## Dependencies

- Нет; это корень roadmap.

## Acceptance Criteria

- Все слои имеют одну ответственность и явные входы/выходы.
- ADR определяет источники истины и правила эволюции контрактов.
- Проверка ссылок и терминов завершается без ошибок.

## Testing Strategy

- `python -m unittest tests.contracts.test_specifications -v` проверяет заголовки, ссылки и обязательные определения.
- `git diff --check` не сообщает ошибок форматирования.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Раннее закрепление неверной границы; откат — отмена конкретного ADR до появления зависимого runtime-кода.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Modify: `docs/specifications/orchestrator-specification.md`
- Create: `docs/adr/0001-core-boundaries.md`
- Test: `tests/scenarios/test_phase_00.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Нет; это корень roadmap.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Все слои имеют одну ответственность и явные входы/выходы.

**Tests:**

- `python -m unittest tests.contracts.test_specifications -v` проверяет заголовки, ссылки и обязательные определения.

- [ ] **Step 1:** Добавить проверку для условия «Все слои имеют одну ответственность и явные входы/выходы.».
- [ ] **Step 2:** Запустить `python -m unittest tests.contracts.test_specifications -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Все слои имеют одну ответственность и явные входы/выходы.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Modify: `docs/specifications/task-layer-specification.md`
- Create: `docs/architecture/component-contracts.md`
- Test: `tests/scenarios/test_phase_00.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Нет; это корень roadmap.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- ADR определяет источники истины и правила эволюции контрактов.

**Tests:**

- `git diff --check` не сообщает ошибок форматирования.

- [ ] **Step 1:** Добавить проверку для условия «ADR определяет источники истины и правила эволюции контрактов.».
- [ ] **Step 2:** Запустить `git diff --check` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «ADR определяет источники истины и правила эволюции контрактов.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
