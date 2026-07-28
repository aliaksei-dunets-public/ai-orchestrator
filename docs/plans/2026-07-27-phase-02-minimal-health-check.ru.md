# Phase 02 — Минимальный Health Check Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Реализовать детерминированную диагностику структуры, schemas, registries и Task Layer.

**Architecture:** Набор чистых checks возвращает типизированные findings, CLI только агрегирует и форматирует text/JSON. Strict mode повышает warnings до ненулевого exit code без автопочинки.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification.md` 0.4 и `docs/specifications/task-layer-specification.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `orchestrator/health.py`
- Create: `orchestrator/cli.py`
- Create: `tests/unit/test_health.py`
- Create: `tests/scenarios/test_health_cli.py`

## Dependencies

- Фаза 1 и контракты T0.

## Acceptance Criteria

- Text и JSON содержат одинаковые findings.
- `--strict` имеет документированный exit-code contract.
- Повреждённый registry диагностируется без traceback.

## Testing Strategy

- `python -m unittest tests.unit.test_health tests.scenarios.test_health_cli -v` проходит.
- `python -m orchestrator health --json` возвращает валидный JSON.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Расхождение text/JSON; откат — сохранить read-only checks и отключить нестабильный formatter.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `orchestrator/health.py`
- Create: `tests/unit/test_health.py`
- Test: `tests/unit/test_health.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 1 и контракты T0.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Text и JSON содержат одинаковые findings.

**Tests:**

- `python -m unittest tests.unit.test_health tests.scenarios.test_health_cli -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Text и JSON содержат одинаковые findings.».
- [ ] **Step 2:** Запустить `python -m unittest tests.unit.test_health tests.scenarios.test_health_cli -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Text и JSON содержат одинаковые findings.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `orchestrator/cli.py`
- Create: `tests/scenarios/test_health_cli.py`
- Test: `tests/unit/test_health.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 1 и контракты T0.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- `--strict` имеет документированный exit-code contract.

**Tests:**

- `python -m orchestrator health --json` возвращает валидный JSON.

- [ ] **Step 1:** Добавить проверку для условия «`--strict` имеет документированный exit-code contract.».
- [ ] **Step 2:** Запустить `python -m orchestrator health --json` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «`--strict` имеет документированный exit-code contract.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
