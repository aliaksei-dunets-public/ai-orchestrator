# Phase 18 — Knowledge Graph Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Представить сущности и связи проекта с provenance, conflict и supersede semantics.

**Architecture:** Graph хранится в переносимых JSONL nodes/edges и строит производные indexes. Canonical truth остаётся в исходных документах, graph — навигационный слой.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/knowledge.py`
- Create: `skills/knowledge-curator/SKILL.md`
- Create: `config/schemas/knowledge-node.schema.json`
- Create: `config/schemas/knowledge-edge.schema.json`

## Dependencies

- Фаза 17.

## Acceptance Criteria

- Node/edge ссылается на существующий source.
- Conflict не перезаписывает обе версии молча.
- Indexes полностью воспроизводятся из canonical JSONL.

## Testing Strategy

- `python -m unittest tests.unit.test_knowledge -v` проходит.
- Rebuild scenario сравнивает graph indexes byte-for-byte.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Graph становится вторым источником истины; откат — удалить indexes и перестроить из source records.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/knowledge.py`
- Create: `config/schemas/knowledge-node.schema.json`
- Test: `tests/scenarios/test_phase_18.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 17.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Node/edge ссылается на существующий source.

**Tests:**

- `python -m unittest tests.unit.test_knowledge -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Node/edge ссылается на существующий source.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_knowledge -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Node/edge ссылается на существующий source.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/knowledge-curator/SKILL.md`
- Create: `config/schemas/knowledge-edge.schema.json`
- Test: `tests/scenarios/test_phase_18.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 17.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Conflict не перезаписывает обе версии молча.

**Tests:**

- Rebuild scenario сравнивает graph indexes byte-for-byte.

- [ ] **Step 1:** Добавить проверку для условия «Conflict не перезаписывает обе версии молча.».
- [ ] **Step 2:** Запустить `Rebuild scenario сравнивает graph indexes byte-for-byte.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Conflict не перезаписывает обе версии молча.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
