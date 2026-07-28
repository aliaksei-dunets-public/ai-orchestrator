# Phase 03 — Session Reporter Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Формировать компактный, безопасный и пригодный для аудита отчёт каждой сессии.

**Architecture:** Reporter принимает структурированный session result и рендерит Markdown по стабильному шаблону. Секреты редактируются до записи, а пустые секции опускаются.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/session_report.py`
- Create: `templates/session-report.md`
- Create: `skills/session-reporter/SKILL.md`
- Create: `tests/unit/test_session_report.py`

## Dependencies

- Фазы 1–2.

## Acceptance Criteria

- Отчёт содержит changes, validation, decisions, risks и next actions.
- Известные формы credentials редактируются.
- Повторный рендер одинакового input детерминирован.

## Testing Strategy

- `python -m unittest tests.unit.test_session_report -v` проходит.
- Golden-file scenario сравнивает полный отчёт без timestamps.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Утечка секретов; откат — запретить persistence отчёта при ошибке redaction.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/session_report.py`
- Create: `skills/session-reporter/SKILL.md`
- Test: `tests/unit/test_session_report.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 1–2.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Отчёт содержит changes, validation, decisions, risks и next actions.

**Tests:**

- `python -m unittest tests.unit.test_session_report -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Отчёт содержит changes, validation, decisions, risks и next actions.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_session_report -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Отчёт содержит changes, validation, decisions, risks и next actions.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `templates/session-report.md`
- Create: `tests/unit/test_session_report.py`
- Test: `tests/unit/test_session_report.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 1–2.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Известные формы credentials редактируются.

**Tests:**

- Golden-file scenario сравнивает полный отчёт без timestamps.

- [ ] **Step 1:** Добавить проверку для условия «Известные формы credentials редактируются.».
- [ ] **Step 2:** Запустить `Golden-file scenario сравнивает полный отчёт без timestamps.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Известные формы credentials редактируются.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
