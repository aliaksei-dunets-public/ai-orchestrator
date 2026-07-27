# Phase 20 — Orchestrator Audit Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Находить смысловые противоречия, drift, дублирование и пробелы тестов без автоматических изменений.

**Architecture:** Audit объединяет deterministic inventory с model-led analysis, сохраняет evidence pointers и выдаёт improvement proposals. Findings дедуплицируются по стабильному fingerprint.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/orchestrator-auditor/SKILL.md`
- Create: `orchestrator/audit.py`
- Create: `config/schemas/audit-report.schema.json`
- Create: `tests/scenarios/test_audit.py`

## Dependencies

- Фазы 2–3, 17–19.

## Acceptance Criteria

- Каждый finding содержит evidence и severity.
- Audit никогда не применяет proposal.
- Повторный audit без изменений не дублирует findings.

## Testing Strategy

- `python -m unittest tests.scenarios.test_audit -v` проходит.
- Seeded fixtures обнаруживают contradiction, dead workflow и missing test.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Недоказуемые рекомендации; откат — исключить findings без source pointers.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/orchestrator-auditor/SKILL.md`
- Create: `config/schemas/audit-report.schema.json`
- Test: `tests/scenarios/test_audit.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 2–3, 17–19.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Каждый finding содержит evidence и severity.

**Tests:**

- `python -m unittest tests.scenarios.test_audit -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Каждый finding содержит evidence и severity.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_audit -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Каждый finding содержит evidence и severity.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `orchestrator/audit.py`
- Create: `tests/scenarios/test_audit.py`
- Test: `tests/scenarios/test_audit.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 2–3, 17–19.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Audit никогда не применяет proposal.

**Tests:**

- Seeded fixtures обнаруживают contradiction, dead workflow и missing test.

- [ ] **Step 1:** Добавить проверку для условия «Audit никогда не применяет proposal.».
- [ ] **Step 2:** Запустить `Seeded fixtures обнаруживают contradiction, dead workflow и missing test.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Audit никогда не применяет proposal.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
