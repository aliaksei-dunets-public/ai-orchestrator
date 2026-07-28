# Phase 09 — Task Review Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Проверять реализацию против scope и критериев Task Context независимо от автора.

**Architecture:** Reviewer получает baseline, diff и test evidence без persuasive narrative. Результат содержит blocking findings, advisory findings и coverage matrix.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/task-reviewer/SKILL.md`
- Create: `templates/task-review-result.json`
- Create: `config/schemas/review-result.schema.json`
- Create: `tests/scenarios/test_task_review.py`

## Dependencies

- Фазы 7–8.

## Acceptance Criteria

- Каждый criterion имеет статус satisfied/failed/unverified.
- Scope creep отмечается blocking finding.
- Review result валиден по общей schema.

## Testing Strategy

- `python -m unittest tests.scenarios.test_task_review -v` проходит.
- Golden fixtures покрывают pass, missing evidence и scope creep.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Reviewer наследует bias implementer; откат — сократить handoff до raw artifacts и baseline.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/task-reviewer/SKILL.md`
- Create: `config/schemas/review-result.schema.json`
- Test: `tests/scenarios/test_task_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 7–8.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждый criterion имеет статус satisfied/failed/unverified.

**Tests:**

- `python -m unittest tests.scenarios.test_task_review -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Каждый criterion имеет статус satisfied/failed/unverified.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_task_review -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждый criterion имеет статус satisfied/failed/unverified.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `templates/task-review-result.json`
- Create: `tests/scenarios/test_task_review.py`
- Test: `tests/scenarios/test_task_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 7–8.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Scope creep отмечается blocking finding.

**Tests:**

- Golden fixtures покрывают pass, missing evidence и scope creep.

- [ ] **Step 1:** Добавить проверку для условия «Scope creep отмечается blocking finding.».
- [ ] **Step 2:** Запустить `Golden fixtures покрывают pass, missing evidence и scope creep.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Scope creep отмечается blocking finding.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
