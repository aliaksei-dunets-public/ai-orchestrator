# Phase 13 — Documentation Manager Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Определять и выполнять необходимые обновления документации как часть completion gate.

**Architecture:** Manager строит impact list из diff и registries, обновляет только канонические документы и проверяет ссылки. Неприменимость документации фиксируется evidence.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/documentation-manager/SKILL.md`
- Create: `orchestrator/documentation.py`
- Create: `config/documentation-map.json`
- Create: `tests/unit/test_documentation.py`

## Dependencies

- Фазы 7–12.

## Acceptance Criteria

- Public contract change указывает обязательный документ.
- Broken links блокируют completion.
- Generated и hand-written docs имеют явных владельцев.

## Testing Strategy

- `python -m unittest tests.unit.test_documentation -v` проходит.
- Scenario меняет CLI contract и ожидает update specification + migration note.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Автообновление искажает нормативный текст; откат — сохранять proposal diff до применения.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/documentation-manager/SKILL.md`
- Create: `config/documentation-map.json`
- Test: `tests/unit/test_documentation.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 7–12.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Public contract change указывает обязательный документ.

**Tests:**

- `python -m unittest tests.unit.test_documentation -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Public contract change указывает обязательный документ.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_documentation -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Public contract change указывает обязательный документ.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `orchestrator/documentation.py`
- Create: `tests/unit/test_documentation.py`
- Test: `tests/unit/test_documentation.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 7–12.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Broken links блокируют completion.

**Tests:**

- Scenario меняет CLI contract и ожидает update specification + migration note.

- [ ] **Step 1:** Добавить проверку для условия «Broken links блокируют completion.».
- [ ] **Step 2:** Запустить `Scenario меняет CLI contract и ожидает update specification + migration note.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Broken links блокируют completion.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
