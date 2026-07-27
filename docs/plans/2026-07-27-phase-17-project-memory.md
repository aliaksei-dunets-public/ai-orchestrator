# Phase 17 — Project Memory Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Хранить подтверждённые observations, decisions и lessons с provenance и защитой секретов.

**Architecture:** Append-only entries имеют тип, источник, confidence и supersede link. Curator предлагает promotion из session report, но запись требует policy gate.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/memory.py`
- Create: `skills/memory-manager/SKILL.md`
- Create: `config/schemas/memory-entry.schema.json`
- Create: `tests/unit/test_memory.py`

## Dependencies

- Фазы 3, 11–14.

## Acceptance Criteria

- Каждая запись имеет source и timestamp.
- Наблюдение не становится instruction автоматически.
- Redaction выполняется до persistence.

## Testing Strategy

- `python -m unittest tests.unit.test_memory -v` проходит.
- Scenario покрывает duplicate, supersede, secret rejection и stale source.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Накопление неверных инструкций; откат — disable entry без удаления provenance.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/memory.py`
- Create: `config/schemas/memory-entry.schema.json`
- Test: `tests/unit/test_memory.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 3, 11–14.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждая запись имеет source и timestamp.

**Tests:**

- `python -m unittest tests.unit.test_memory -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Каждая запись имеет source и timestamp.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_memory -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждая запись имеет source и timestamp.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/memory-manager/SKILL.md`
- Create: `tests/unit/test_memory.py`
- Test: `tests/unit/test_memory.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 3, 11–14.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Наблюдение не становится instruction автоматически.

**Tests:**

- Scenario покрывает duplicate, supersede, secret rejection и stale source.

- [ ] **Step 1:** Добавить проверку для условия «Наблюдение не становится instruction автоматически.».
- [ ] **Step 2:** Запустить `Scenario покрывает duplicate, supersede, secret rejection и stale source.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Наблюдение не становится instruction автоматически.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
