# Phase 01 — Каркас репозитория Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Создать минимальный устанавливаемый каркас с реестрами, схемами и discoverable-навыками.

**Architecture:** Python-пакет содержит runtime, а declarative assets живут в config, registries, skills и workflows. Все ссылки проверяет contract suite.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `pyproject.toml`
- Create: `AGENTS.md`
- Create: `orchestrator/__init__.py`
- Create: `registries/skills.json`
- Create: `registries/workflows.json`
- Create: `config/schemas/registry.schema.json`

## Dependencies

- Фаза 0.

## Acceptance Criteria

- Пакет устанавливается в editable mode.
- Каждая запись registry указывает на существующий артефакт.
- Workspace-инструкции описывают безопасный workflow разработки.

## Testing Strategy

- `python -m unittest discover -s tests/contracts -p 'test_registry*.py' -v` проходит.
- `python -m pip install -e .` и `python -c "import orchestrator"` завершаются с кодом 0.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Пустые placeholders создадут ложную готовность; откат — удалить только scaffold без данных проекта.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `pyproject.toml`
- Create: `orchestrator/__init__.py`
- Create: `registries/workflows.json`
- Test: `tests/scenarios/test_phase_01.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 0.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Пакет устанавливается в editable mode.

**Tests:**

- `python -m unittest discover -s tests/contracts -p 'test_registry*.py' -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Пакет устанавливается в editable mode.».
- [ ] **Step 2:** Запустить `python -m unittest discover -s tests/contracts -p 'test_registry*.py' -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Пакет устанавливается в editable mode.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `AGENTS.md`
- Create: `registries/skills.json`
- Create: `config/schemas/registry.schema.json`
- Test: `tests/scenarios/test_phase_01.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 0.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждая запись registry указывает на существующий артефакт.

**Tests:**

- `python -m pip install -e .` и `python -c "import orchestrator"` завершаются с кодом 0.

- [ ] **Step 1:** Добавить проверку для условия «Каждая запись registry указывает на существующий артефакт.».
- [ ] **Step 2:** Запустить `python -m pip install -e .` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждая запись registry указывает на существующий артефакт.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
