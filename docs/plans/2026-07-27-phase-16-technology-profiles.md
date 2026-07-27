# Phase 16 — Technology Profiles Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Добавить Python и ABAP/RAP profiles с командами, review и documentation rules.

**Architecture:** Technology profile описывает detection, directories, build/test/security commands и overrides. Composite resolver объединяет profiles детерминированно и выявляет конфликт.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `profiles/technologies/python.yaml`
- Create: `profiles/technologies/abap-rap.yaml`
- Create: `config/schemas/technology-profile.schema.json`
- Create: `orchestrator/technologies.py`

## Dependencies

- Фаза 15.

## Acceptance Criteria

- Detection объясняет evidence и confidence.
- Composite merge имеет стабильный precedence.
- Неизвестная команда не исполняется автоматически.

## Testing Strategy

- `python -m unittest tests.contracts.test_technology_profiles -v` проходит.
- Sandbox Python и ABAP fixtures выбирают ожидаемые profiles.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Опасная команда из project data; откат — требовать allowlist/approval для неизвестных tools.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `profiles/technologies/python.yaml`
- Create: `config/schemas/technology-profile.schema.json`
- Test: `tests/scenarios/test_phase_16.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 15.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Detection объясняет evidence и confidence.

**Tests:**

- `python -m unittest tests.contracts.test_technology_profiles -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Detection объясняет evidence и confidence.».
- [ ] **Step 2:** Запустить `python -m unittest tests.contracts.test_technology_profiles -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Detection объясняет evidence и confidence.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `profiles/technologies/abap-rap.yaml`
- Create: `orchestrator/technologies.py`
- Test: `tests/scenarios/test_phase_16.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 15.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Composite merge имеет стабильный precedence.

**Tests:**

- Sandbox Python и ABAP fixtures выбирают ожидаемые profiles.

- [ ] **Step 1:** Добавить проверку для условия «Composite merge имеет стабильный precedence.».
- [ ] **Step 2:** Запустить `Sandbox Python и ABAP fixtures выбирают ожидаемые profiles.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Composite merge имеет стабильный precedence.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
