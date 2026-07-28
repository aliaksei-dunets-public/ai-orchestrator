# Phase 23 — Stable Release 1.0 Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Выпустить 1.0 со стабильными контрактами, migration guide и полным acceptance evidence.

**Architecture:** Release pipeline фиксирует schema/API compatibility, собирает manifest и проверяет install/upgrade/rollback. Изменения контракта после freeze требуют versioned migration.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `CHANGELOG.md`
- Create: `ROADMAP.md`
- Create: `docs/migrations/1.0.md`
- Create: `releases/1.0.0/manifest.json`
- Create: `tests/acceptance/test_release.py`

## Dependencies

- Фазы 0–22.

## Acceptance Criteria

- Clean install и supported upgrade проходят.
- Manifest воспроизводим и содержит checksums.
- Документированы compatibility window, known limitations и rollback.

## Testing Strategy

- `python -m unittest tests.acceptance.test_release -v` проходит.
- `python tests/acceptance/run_matrix.py --release 1.0.0 --strict` проходит на release artifact.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Freeze незрелого контракта; откат — выпуск release candidate без stable tag до закрытия blocking findings.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `CHANGELOG.md`
- Create: `docs/migrations/1.0.md`
- Create: `tests/acceptance/test_release.py`
- Test: `tests/acceptance/test_release.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 0–22.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Clean install и supported upgrade проходят.

**Tests:**

- `python -m unittest tests.acceptance.test_release -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Clean install и supported upgrade проходят.».
- [ ] **Step 2:** Запустить `python -m unittest tests.acceptance.test_release -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Clean install и supported upgrade проходят.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `ROADMAP.md`
- Create: `releases/1.0.0/manifest.json`
- Test: `tests/acceptance/test_release.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 0–22.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Manifest воспроизводим и содержит checksums.

**Tests:**

- `python tests/acceptance/run_matrix.py --release 1.0.0 --strict` проходит на release artifact.

- [ ] **Step 1:** Добавить проверку для условия «Manifest воспроизводим и содержит checksums.».
- [ ] **Step 2:** Запустить `python tests/acceptance/run_matrix.py --release 1.0.0 --strict` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Manifest воспроизводим и содержит checksums.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
