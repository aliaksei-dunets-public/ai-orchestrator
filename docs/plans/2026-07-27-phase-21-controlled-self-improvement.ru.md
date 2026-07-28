# Phase 21 — Controlled Self-Improvement Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Проводить улучшение core только как обычную утверждённую задачу с rollback.

**Architecture:** Improvement Designer превращает audit finding в draft Task Context, связывает regression test и approval. Никакой компонент не получает прямого self-write пути.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/improvement-designer/SKILL.md`
- Create: `workflows/improvement-proposal.yaml`
- Create: `config/policies/self-improvement.yaml`
- Create: `tests/scenarios/test_self_improvement.py`

## Dependencies

- Фазы 12, 20.

## Acceptance Criteria

- Proposal не изменяет repository.
- Approval относится к точному diff/revision.
- Rollback instructions и regression test обязательны до merge.

## Testing Strategy

- `python -m unittest tests.scenarios.test_self_improvement -v` проходит.
- Negative scenario подтверждает запрет self-write без Task Manager и approval.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Обход approval через локальный override; откат — immutable deny policy и fail closed.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/improvement-designer/SKILL.md`
- Create: `config/policies/self-improvement.yaml`
- Test: `tests/scenarios/test_self_improvement.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 12, 20.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Proposal не изменяет repository.

**Tests:**

- `python -m unittest tests.scenarios.test_self_improvement -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Proposal не изменяет repository.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_self_improvement -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Proposal не изменяет repository.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `workflows/improvement-proposal.yaml`
- Create: `tests/scenarios/test_self_improvement.py`
- Test: `tests/scenarios/test_self_improvement.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 12, 20.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Approval относится к точному diff/revision.

**Tests:**

- Negative scenario подтверждает запрет self-write без Task Manager и approval.

- [ ] **Step 1:** Добавить проверку для условия «Approval относится к точному diff/revision.».
- [ ] **Step 2:** Запустить `Negative scenario подтверждает запрет self-write без Task Manager и approval.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Approval относится к точному diff/revision.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
