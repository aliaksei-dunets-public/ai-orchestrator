# Phase 15 — Platform Profiles Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Адаптировать orchestration к Codex, Google Antigravity, GitHub Copilot VS Code и Claude VS Code через единый capability contract.

**Architecture:** Core запрашивает возможности, а не имя платформы. Profile связывает shell, Git, MCP, review isolation, approvals и fallback с унифицированными adapters.

**Tech Stack:** Python 3.11+, Python standard library for runtime-critical Task Manager paths, Markdown, JSON/JSON Schema, YAML profiles and `unittest`.

## Global Constraints

- Соблюдать `docs/specifications/orchestrator-specification-ru.md` 0.4 и `docs/specifications/task-layer-specification-ru.md` 0.3.
- Не ослаблять immutable security policies и не добавлять неутверждённые внешние runtime dependencies.
- Сохранять backward compatibility ранее завершённых фаз или добавлять явную migration.

## Deliverables

- Create: `profiles/platforms/codex.yaml`
- Create: `profiles/platforms/google-antigravity.yaml`
- Create: `profiles/platforms/github-copilot-vscode.yaml`
- Create: `profiles/platforms/claude-vscode.yaml`
- Create: `config/schemas/platform-profile.schema.json`
- Create: `orchestrator/platforms.py`
- Create: `tests/contracts/test_platform_profiles.py`

## Dependencies

- Фазы 2, 7 и 14.

## Acceptance Criteria

- Core не содержит platform-name branches.
- Недоступная capability выбирает объявленный fallback или blocked.
- Adapters вводятся в порядке Antigravity → GitHub Copilot → Claude после Codex baseline.
- Все четыре profiles проходят одинаковый contract suite до перехода к следующему adapter.

## Testing Strategy

- `python -m unittest tests.contracts.test_platform_profiles -v` проходит.
- `python -m unittest tests.scenarios.test_platform_adapters -v` запускает shell/no-shell, virtual-URI и sub-agent/no-sub-agent cases.
- При исправлении обнаруженного дефекта добавить отдельный regression fixture; иначе зафиксировать неприменимость regression test в review evidence.

## Risks and Rollback

- Сведение к наименьшему общему знаменателю; откат — capability-specific optional extensions под schema.

## Implementation Tasks

### Task 1: Контракт и тестовые fixtures

**Files:**

- Create: `profiles/platforms/codex.yaml`
- Create: `config/schemas/platform-profile.schema.json`
- Create: `tests/contracts/test_platform_profiles.py`
- Test: `tests/contracts/test_platform_profiles.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 2, 7 и 14.).
- Produces: проверяемый результат Task 1, совместимый с deliverables этой фазы.

**Acceptance:**

- Core не содержит platform-name branches.

**Tests:**

- `python -m unittest tests.contracts.test_platform_profiles -v` проходит.

- [ ] **Step 1:** Добавить проверку для условия «Core не содержит platform-name branches.».
- [ ] **Step 2:** Запустить `python -m unittest tests.contracts.test_platform_profiles -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать контракт и тестовые fixtures в перечисленных файлах без расширения scope.
- [ ] **Step 4:** Повторить focused check и убедиться, что условие «Core не содержит platform-name branches.» выполняется.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 2: Google Antigravity adapter

**Files:**

- Create: `profiles/platforms/google-antigravity.yaml`
- Create: `orchestrator/platforms.py`
- Test: `tests/scenarios/test_platform_adapters.py`

**Interfaces:**

- Consumes: нормативные спецификации и deliverables зависимых фаз (Фазы 2, 7 и 14.).
- Produces: проверяемый результат Task 2, совместимый с deliverables этой фазы.

**Acceptance:**

- Google Antigravity проходит capability contract и fallback scenarios.

**Tests:**

- `python -m unittest tests.scenarios.test_platform_adapters.GoogleAntigravityAdapterTests -v` проходит.

- [ ] **Step 1:** Добавить Antigravity fixtures для tools, approvals, shell и fallback.
- [ ] **Step 2:** Запустить `python -m unittest tests.scenarios.test_platform_adapters.GoogleAntigravityAdapterTests -v` и подтвердить ожидаемый failure до реализации.
- [ ] **Step 3:** Реализовать Antigravity profile и adapter без platform-name branches в Core.
- [ ] **Step 4:** Повторить contract и scenario suites до полного pass.
- [ ] **Step 5:** Запустить затронутый regression suite, записать evidence и передать изменение на независимый review.

### Task 3: GitHub Copilot VS Code adapter

**Files:**

- Create: `profiles/platforms/github-copilot-vscode.yaml`
- Modify: `orchestrator/platforms.py`
- Test: `tests/scenarios/test_platform_adapters.py`

**Interfaces:**

- Consumes: утверждённый capability contract и прошедший Antigravity adapter.
- Produces: Copilot VS Code adapter с virtual-URI, editor-context и approval fallback.

**Acceptance:**

- GitHub Copilot VS Code проходит тот же contract без изменения Core interfaces.

**Tests:**

- `python -m unittest tests.scenarios.test_platform_adapters.GitHubCopilotAdapterTests -v` проходит.

- [ ] **Step 1:** Добавить fixtures IDE context, virtual URI и отсутствующего shell.
- [ ] **Step 2:** Запустить focused Copilot suite и подтвердить ожидаемый failure.
- [ ] **Step 3:** Реализовать profile и adapter поверх существующего capability contract.
- [ ] **Step 4:** Запустить contract suite всех трёх готовых платформ.
- [ ] **Step 5:** Зафиксировать platform limitations и передать изменение на review.

### Task 4: Claude VS Code adapter

**Files:**

- Create: `profiles/platforms/claude-vscode.yaml`
- Modify: `orchestrator/platforms.py`
- Test: `tests/scenarios/test_platform_adapters.py`

**Interfaces:**

- Consumes: утверждённый capability contract и прошедшие Antigravity/Copilot adapters.
- Produces: Claude VS Code adapter и итоговую четырёхплатформенную compatibility matrix.

**Acceptance:**

- Claude VS Code проходит общий contract, а результаты Codex, Antigravity, Copilot и Claude сопоставимы.

**Tests:**

- `python -m unittest tests.scenarios.test_platform_adapters.ClaudeAdapterTests -v` проходит.

- [ ] **Step 1:** Добавить Claude fixtures для tool routing, review isolation и approvals.
- [ ] **Step 2:** Запустить focused Claude suite и подтвердить ожидаемый failure.
- [ ] **Step 3:** Реализовать profile и adapter без изменения public capability contract.
- [ ] **Step 4:** Запустить общий suite в порядке Codex → Antigravity → Copilot → Claude.
- [ ] **Step 5:** Обновить compatibility documentation и передать фазу на review.
