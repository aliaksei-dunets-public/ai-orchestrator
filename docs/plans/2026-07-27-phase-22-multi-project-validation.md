# Phase 22 — Multi-Project Validation Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Подтвердить переносимость на Codex, Google Antigravity, GitHub Copilot VS Code и Claude VS Code, двух стеках и в managed/standalone modes.

**Architecture:** Матрица sandbox projects запускает одинаковый acceptance suite с platform/technology adapters. Результаты сохраняют версии среды и известные отклонения.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `tests/acceptance/matrix.json`
- Create: `tests/acceptance/run_matrix.py`
- Create: `tests/sandbox-projects/abap-rap-minimal/README.md`
- Create: `docs/validation/multi-project-report.md`

## Dependencies

- Фазы 14–21.

## Acceptance Criteria

- Все 16 комбинаций «4 платформы × 2 стека × 2 режима установки» имеют результат.
- Managed update не меняет project-owned files.
- Standalone copy работает без исходного core repository.

## Testing Strategy

- `python tests/acceptance/run_matrix.py --strict` завершается с кодом 0.
- Повторный onboarding и task lifecycle выполняются на платформах в порядке Antigravity → GitHub Copilot → Claude после Codex baseline.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Ложная переносимость из-за одинаковой среды; откат — пометить профиль experimental до независимого запуска.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `tests/acceptance/matrix.json`
- Create: `tests/sandbox-projects/abap-rap-minimal/README.md`
- Test: `tests/acceptance/matrix.json`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 14–21.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Все 16 обязательных комбинаций завершаются успешно; unsupported или blocked cell считается незавершённой фазой.

**Tests:**

- `python tests/acceptance/run_matrix.py --strict` завершается с кодом 0.

- [ ] **Step 1:** Добавить matrix entries для Codex, Antigravity, GitHub Copilot и Claude с Python/ABAP и managed/standalone.
- [ ] **Step 2:** Запустить `python tests/acceptance/run_matrix.py --strict` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что все 16 matrix cells имеют evidence.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `tests/acceptance/run_matrix.py`
- Create: `docs/validation/multi-project-report.md`
- Test: `tests/acceptance/matrix.json`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 14–21.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Managed update не меняет project-owned files.

**Tests:**

- `python tests/acceptance/run_matrix.py --platform-order codex,google-antigravity,github-copilot-vscode,claude-vscode --strict` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Managed update не меняет project-owned files.».
- [ ] **Step 2:** Запустить `python tests/acceptance/run_matrix.py --platform-order codex,google-antigravity,github-copilot-vscode,claude-vscode --strict` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Managed update не меняет project-owned files.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
