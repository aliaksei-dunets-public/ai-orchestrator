# Phase 06 — Standard и Deep Task Creator Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Добавить анализ проекта, brainstorming, подробное planning, Plan Review и Context Validation.

**Architecture:** Task Creator координирует отдельные provider-навыки и сохраняет evidence в Task Context. Deep mode ставит approval gate до регистрации выбранного подхода.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/task-analyzer/SKILL.md`
- Create: `skills/plan-writer/SKILL.md`
- Create: `skills/plan-reviewer/SKILL.md`
- Create: `skills/task-context-validator/SKILL.md`
- Create: `workflows/task-creation-standard.yaml`
- Create: `tests/scenarios/test_standard_task_creation.py`

## Dependencies

- Фаза 5.

## Acceptance Criteria

- Standard context покрывает все нормативные разделы.
- Review возвращает дефектный plan writer до approval.
- Deep task нельзя зарегистрировать без явного approval evidence.

## Testing Strategy

- `python -m unittest tests.scenarios.test_standard_task_creation -v` проходит.
- Contract fixtures покрывают quick/standard/deep и invalid open questions.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Coordinator дублирует providers; откат — оставить orchestration, а domain logic вернуть атомарным skills.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/task-analyzer/SKILL.md`
- Create: `skills/plan-reviewer/SKILL.md`
- Create: `workflows/task-creation-standard.yaml`
- Test: `tests/scenarios/test_standard_task_creation.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 5.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Standard context покрывает все нормативные разделы.

**Tests:**

- `python -m unittest tests.scenarios.test_standard_task_creation -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Standard context покрывает все нормативные разделы.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_standard_task_creation -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Standard context покрывает все нормативные разделы.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/plan-writer/SKILL.md`
- Create: `skills/task-context-validator/SKILL.md`
- Create: `tests/scenarios/test_standard_task_creation.py`
- Test: `tests/scenarios/test_standard_task_creation.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 5.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Review возвращает дефектный plan writer до approval.

**Tests:**

- Contract fixtures покрывают quick/standard/deep и invalid open questions.

- [ ] **Step 1:** Добавить проверку для условия «Review возвращает дефектный plan writer до approval.».
- [ ] **Step 2:** Запустить `Contract fixtures покрывают quick/standard/deep и invalid open questions.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Review возвращает дефектный plan writer до approval.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
