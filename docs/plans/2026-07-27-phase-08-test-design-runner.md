# Phase 08 — Test Design and Runner Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Проектировать и запускать релевантные focused, contract, scenario и regression checks.

**Architecture:** Test Designer строит validation matrix из acceptance criteria, а Runner исполняет команды через platform adapter. Evidence хранит команду, exit code и краткий результат.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/test-designer/SKILL.md`
- Create: `skills/test-runner/SKILL.md`
- Create: `orchestrator/testing.py`
- Create: `tests/unit/test_testing.py`

## Dependencies

- Фаза 7.

## Acceptance Criteria

- Каждый acceptance criterion связан минимум с одной проверкой.
- Timeout и недоступный tool возвращают blocked evidence.
- Регрессионный тест обязателен только для исправленной ошибки.

## Testing Strategy

- `python -m unittest tests.unit.test_testing -v` проходит.
- Scenario с failing/passing/timeout командами сохраняет корректные результаты.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Ложный pass из-за неполного набора; откат — блокировать gate при criterion без evidence.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/test-designer/SKILL.md`
- Create: `orchestrator/testing.py`
- Test: `tests/unit/test_testing.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 7.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждый acceptance criterion связан минимум с одной проверкой.

**Tests:**

- `python -m unittest tests.unit.test_testing -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Каждый acceptance criterion связан минимум с одной проверкой.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_testing -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждый acceptance criterion связан минимум с одной проверкой.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/test-runner/SKILL.md`
- Create: `tests/unit/test_testing.py`
- Test: `tests/unit/test_testing.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 7.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Timeout и недоступный tool возвращают blocked evidence.

**Tests:**

- Scenario с failing/passing/timeout командами сохраняет корректные результаты.

- [ ] **Step 1:** Добавить проверку для условия «Timeout и недоступный tool возвращают blocked evidence.».
- [ ] **Step 2:** Запустить `Scenario с failing/passing/timeout командами сохраняет корректные результаты.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Timeout и недоступный tool возвращают blocked evidence.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
