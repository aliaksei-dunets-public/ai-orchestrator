# Phase 05 — Quick Task Creator Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Создавать минимальный валидный draft и план для очевидных низкорисковых изменений.

**Architecture:** Coordinator собирает обязательные quick-поля, делегирует проверку контрактному validator и не регистрирует draft напрямую. `skills/task-creator` становится каноническим source, а `.codex/skills/task-creator` создаётся installer как проверяемая platform-проекция.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/task-creator/SKILL.md`
- Create: `skills/task-creator/references/task-context-contract.md`
- Create: `skills/task-creator/scripts/validate_task_context.py`
- Create: `orchestrator/skill_installer.py`
- Create: `tests/contracts/test_task_context.py`
- Create: `tests/contracts/test_skill_installation.py`

## Dependencies

- Фаза 4.

## Acceptance Criteria

- Quick draft без фиктивного ID проходит validation.
- Критический открытый вопрос блокирует регистрацию.
- План содержит scope, acceptance criteria и конкретные tests.
- Codex-копия воспроизводимо устанавливается из `skills/task-creator`, а drift обнаруживается.

## Testing Strategy

- `python -m unittest tests.contracts.test_task_context -v` проходит.
- `python -m unittest tests.contracts.test_skill_installation -v` проверяет install, повторный install и drift.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Quick будет скрывать риск; откат — автоматически повышать mode до standard при неоднозначности.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/task-creator/SKILL.md`
- Create: `skills/task-creator/scripts/validate_task_context.py`
- Test: `tests/contracts/test_task_context.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 4.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Quick draft без фиктивного ID проходит validation.

**Tests:**

- `python -m unittest tests.contracts.test_task_context -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Quick draft без фиктивного ID проходит validation.».
- [ ] **Step 2:** Запустить `python -m unittest tests.contracts.test_task_context -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Quick draft без фиктивного ID проходит validation.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `skills/task-creator/references/task-context-contract.md`
- Create: `orchestrator/skill_installer.py`
- Create: `tests/contracts/test_skill_installation.py`
- Test: `tests/contracts/test_skill_installation.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 4.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Установка из `skills/task-creator` создаёт эквивалентную `.codex`-копию и обнаруживает ручной drift.

**Tests:**

- `python -m unittest tests.contracts.test_skill_installation -v` проходит.

- [ ] **Step 1:** Добавить fixtures канонического skill, установленной Codex-копии и намеренного drift.
- [ ] **Step 2:** Запустить `python -m unittest tests.contracts.test_skill_installation -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что install идемпотентен, а drift диагностируется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
