# Phase 11 — Security Review Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Ввести обязательный security gate для чувствительных изменений до user review.

**Architecture:** Security Reviewer объединяет threat-focused анализ с доступными deterministic scanners. Immutable policy определяет триггеры и запрещает локальное отключение gate.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `skills/security-reviewer/SKILL.md`
- Create: `config/policies/security.yaml`
- Create: `references/security/review-checklist.md`
- Create: `tests/scenarios/test_security_review.py`

## Dependencies

- Фаза 10.

## Acceptance Criteria

- Security-sensitive diff всегда маршрутизируется в gate.
- Critical/high finding блокирует передачу пользователю.
- Logs и reports не сохраняют credentials.

## Testing Strategy

- `python -m unittest tests.scenarios.test_security_review -v` проходит.
- Seeded vulnerable fixtures обнаруживаются, безопасные controls не дают blocking finding.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Policy bypass через override; откат — fail closed при конфликте policy.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `skills/security-reviewer/SKILL.md`
- Create: `references/security/review-checklist.md`
- Test: `tests/scenarios/test_security_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 10.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Security-sensitive diff всегда маршрутизируется в gate.

**Tests:**

- `python -m unittest tests.scenarios.test_security_review -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Security-sensitive diff всегда маршрутизируется в gate.».
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_security_review -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Security-sensitive diff всегда маршрутизируется в gate.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Реализация и интеграция

**Files:**

- Create: `config/policies/security.yaml`
- Create: `tests/scenarios/test_security_review.py`
- Test: `tests/scenarios/test_security_review.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фаза 10.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Critical/high finding блокирует передачу пользователю.

**Tests:**

- Seeded vulnerable fixtures обнаруживаются, безопасные controls не дают blocking finding.

- [ ] **Step 1:** Добавить проверку для условия «Critical/high finding блокирует передачу пользователю.».
- [ ] **Step 2:** Запустить `Seeded vulnerable fixtures обнаруживаются, безопасные controls не дают blocking finding.` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать реализация и интеграция в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Critical/high finding блокирует передачу пользователю.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.
