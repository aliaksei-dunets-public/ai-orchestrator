# Phase 04 — Минимальный Task Manager Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Реализовать T0–T3: schema, read-only команды, регистрацию, переходы и безопасный claim.

**Architecture:** Task Registry остаётся единственным локальным operational state и не хранится в Git. Первая версия допускает один изменяющий process; каждая запись публикуется crash-safe через временный файл, flush/fsync и `os.replace`.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/task_manager.py`
- Create: `orchestrator/task_cli.py`
- Create: `config/schemas/task-registry.schema.json`
- Create: `templates/task-context.md`
- Create: `tests/unit/test_task_manager.py`
- Create: `tests/scenarios/test_task_cli.py`
- Modify: `.gitignore`

## Dependencies

- Фазы 0–2; Task Layer T0.

## Acceptance Criteria

- Команды и exit codes соответствуют Task Layer 0.3.
- Последовательные `claim-next` не нарушают правило одной активной задачи.
- Crash registration обнаруживается validate как recoverable inconsistency.
- `tasks.json`, `*.tmp` и `*.lock` исключены из Git, а Task Context остаётся tracked.

## Testing Strategy

- `python -m unittest tests.unit.test_task_manager tests.scenarios.test_task_cli -v` проходит.
- `git check-ignore .orchestrator/tasks/tasks.json .orchestrator/tasks/probe.tmp .orchestrator/tasks/probe.lock` подтверждает локальный operational state.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Одновременный запуск writers может потерять update и находится вне контракта; откат при сбое — восстановить последний валидный файл и orphan context по диагностике `validate`.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/task_manager.py`
- Create: `config/schemas/task-registry.schema.json`
- Create: `tests/unit/test_task_manager.py`
- Test: `tests/unit/test_task_manager.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 0–2; Task Layer T0.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Команды и exit codes соответствуют Task Layer 0.3.

**Tests:**

- `python -m unittest tests.unit.test_task_manager tests.scenarios.test_task_cli -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Команды и exit codes соответствуют Task Layer 0.3.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_task_manager tests.scenarios.test_task_cli -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Команды и exit codes соответствуют Task Layer 0.3.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `orchestrator/task_cli.py`
- Create: `templates/task-context.md`
- Create: `tests/scenarios/test_task_cli.py`
- Modify: `.gitignore`
- Test: `tests/unit/test_task_manager.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 0–2; Task Layer T0.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Последовательный `claim-next` блокирует вторую активную задачу, а registry остаётся незатреканным.

**Tests:**

- `python -m unittest tests.scenarios.test_task_cli.TaskCliScenarioTests.test_single_writer_claim_and_gitignore -v` проходит.

- [ ] **Step 1:** Добавить проверку последовательного claim и `git check-ignore` для operational-файлов.
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_task_cli.TaskCliScenarioTests.test_single_writer_claim_and_gitignore -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что single-writer и Git-boundary соблюдаются.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
