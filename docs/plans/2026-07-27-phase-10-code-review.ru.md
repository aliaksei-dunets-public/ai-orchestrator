# Phase 10 — Code Review Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Добавить независимую проверку корректности, качества и сопровождаемости изменений.

**Architecture:** Code Reviewer восстанавливает затронутые flows и ранжирует только actionable findings. Platform profile выбирает механизм изоляции reviewer.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/code-reviewer/SKILL.md`
- Create: `references/review/code-quality.md`
- Create: `tests/scenarios/test_code_review.py`
- Modify: `workflows/task-execution.yaml`

## Dependencies

- Фаза 9.

## Acceptance Criteria

- Blocking finding возвращает workflow к implementation.
- Каждый finding содержит файл, evidence, impact и remediation.
- Отсутствие sub-agent имеет явный fallback.

## Testing Strategy

- `python -m unittest tests.scenarios.test_code_review -v` проходит.
- Eval fixtures измеряют false-positive rate на заведомо корректном diff.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Шумные findings замедляют workflow; откат — ограничить blocking только доказуемыми дефектами.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/code-reviewer/SKILL.md`
- Create: `tests/scenarios/test_code_review.py`
- Test: `tests/scenarios/test_code_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 9.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Blocking finding возвращает workflow к implementation.

**Tests:**

- `python -m unittest tests.scenarios.test_code_review -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Blocking finding возвращает workflow к implementation.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_code_review -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Blocking finding возвращает workflow к implementation.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `references/review/code-quality.md`
- Modify: `workflows/task-execution.yaml`
- Test: `tests/scenarios/test_code_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 9.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждый finding содержит файл, evidence, impact и remediation.

**Tests:**

- Eval fixtures измеряют false-positive rate на заведомо корректном diff.

- [ ] **Step 1:** Добавить проверку для условия «Каждый finding содержит файл, evidence, impact и remediation.».
- [ ] **Step 2:** Запустить `Eval fixtures измеряют false-positive rate на заведомо корректном diff.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждый finding содержит файл, evidence, impact и remediation.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
