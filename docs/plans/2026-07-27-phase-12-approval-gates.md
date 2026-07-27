# Phase 12 — User Review and Approval Gates Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Формализовать решения пользователя и доказательства approval без смешения со статусами workflow.

**Architecture:** Gate описывается декларативно и возвращает approved/rejected/waiting. Task Manager хранит waiting_user, а Task Context — вопрос, варианты и evidence ответа.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/approvals.py`
- Create: `config/schemas/approval.schema.json`
- Create: `templates/approval-request.md`
- Create: `tests/unit/test_approvals.py`

## Dependencies

- Фазы 6 и 11.

## Acceptance Criteria

- Gate имеет точный вопрос, последствия и безопасный default.
- Approval привязан к revision baseline.
- Изменение scope инвалидирует старое approval.

## Testing Strategy

- `python -m unittest tests.unit.test_approvals -v` проходит.
- Scenario проверяет approve, reject, stale approval и timeout.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Повторное использование устаревшего approval; откат — инвалидировать evidence при любой смене revision.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/approvals.py`
- Create: `templates/approval-request.md`
- Test: `tests/unit/test_approvals.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 6 и 11.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Gate имеет точный вопрос, последствия и безопасный default.

**Tests:**

- `python -m unittest tests.unit.test_approvals -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Gate имеет точный вопрос, последствия и безопасный default.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_approvals -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Gate имеет точный вопрос, последствия и безопасный default.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `config/schemas/approval.schema.json`
- Create: `tests/unit/test_approvals.py`
- Test: `tests/unit/test_approvals.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 6 и 11.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Approval привязан к revision baseline.

**Tests:**

- Scenario проверяет approve, reject, stale approval и timeout.

- [ ] **Step 1:** Добавить проверку для условия «Approval привязан к revision baseline.».
- [ ] **Step 2:** Запустить `Scenario проверяет approve, reject, stale approval и timeout.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Approval привязан к revision baseline.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
