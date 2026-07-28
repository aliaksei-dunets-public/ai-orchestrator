# Phase 14 — Project Onboarding Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Создавать project context и профиль на основе evidence без изменения core.

**Architecture:** Onboarding adapters собирают facts, классификатор предлагает profiles, а пользователь утверждает diff. Ручные секции маркируются и сохраняются при повторном запуске.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/onboarding.py`
- Create: `skills/project-onboarding/SKILL.md`
- Create: `templates/project-context.md`
- Create: `tests/sandbox-projects/python-minimal/README.md`

## Dependencies

- Фазы 1–3 и 12–13.

## Acceptance Criteria

- Dry-run показывает полный diff.
- Повторный onboarding идемпотентен и сохраняет manual blocks.
- Секреты и большие generated trees исключаются.

## Testing Strategy

- `python -m unittest tests.scenarios.test_onboarding -v` проходит.
- Sandbox run дважды даёт пустой второй diff.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Стирание ручных правок; откат — отказ от записи при конфликте ownership markers.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/onboarding.py`
- Create: `templates/project-context.md`
- Test: `tests/sandbox-projects/python-minimal/README.md`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 1–3 и 12–13.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Dry-run показывает полный diff.

**Tests:**

- `python -m unittest tests.scenarios.test_onboarding -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Dry-run показывает полный diff.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_onboarding -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Dry-run показывает полный diff.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/project-onboarding/SKILL.md`
- Create: `tests/sandbox-projects/python-minimal/README.md`
- Test: `tests/sandbox-projects/python-minimal/README.md`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 1–3 и 12–13.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Повторный onboarding идемпотентен и сохраняет manual blocks.

**Tests:**

- Sandbox run дважды даёт пустой второй diff.

- [ ] **Step 1:** Добавить проверку для условия «Повторный onboarding идемпотентен и сохраняет manual blocks.».
- [ ] **Step 2:** Запустить `Sandbox run дважды даёт пустой второй diff.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Повторный onboarding идемпотентен и сохраняет manual blocks.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
