# Phase 24 — Skill Distribution Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Разделить библиотеку на system, bundled и optional skills, устанавливать базовый набор по умолчанию, а optional — только после approval, и поддержать независимые project-owned skills.

**Architecture:** Один release содержит core и полную библиотеку. Registry задаёт категорию каждого навыка; installer атомарно строит platform projection из system, bundled, выбранных optional и project-owned sources. Согласованный дизайн: [2026-07-28-skill-distribution-design.md](2026-07-28-skill-distribution-design.md).

**Tech Stack:** Python 3.11+, Python standard library, Markdown, JSON/JSON Schema, YAML profiles и `unittest`.

## Global Constraints

- Соблюдать нормативные спецификации и сначала обновить их новым контрактом.
- Не ослаблять immutable security policies и не разрешать отключение system skills.
- Не добавлять удалённый registry, независимые package versions, dependency solver, inheritance, overlay или automatic rebase.
- Сохранять skill IDs, workflow references и upstream provenance.
- Не редактировать сгенерированные platform-проекции вручную.
- Не перезаписывать project-owned sources или unrelated user changes.

## Deliverables

- Обновлённые спецификации и component contracts.
- Registry со значением `distribution` для каждого skill entry.
- Канонические каталоги `skills/system/`, `skills/bundled/` и `skills/optional/`.
- Schema и loader для `.orchestrator/skills.json`.
- Атомарная выборочная синхронизация platform projection.
- Поддержка `.orchestrator/project-skills/<id>/`.
- Read-only рекомендации optional skills из technology profiles.
- Health, contract, scenario и release evidence.

## Dependencies

- Phase 23 — Stable Release 1.0.
- Token-efficiency optimization change-set.
- [Согласованный дизайн распределения навыков](2026-07-28-skill-distribution-design.md).

## Acceptance Criteria

- Чистая установка содержит все и только system + bundled skills.
- `python-code-review` и `optimizer` отсутствуют до явного выбора.
- Выбранный optional skill и валидный project-owned skill устанавливаются детерминированно.
- Recommendation не меняет selection или projection без approval.
- System skill нельзя исключить локальной конфигурацией.
- Конфликт ID, неизвестный optional ID и отсутствующий `SKILL.md` отклоняются.
- Ошибка синхронизации сохраняет предыдущую рабочую проекцию.
- Workspace и release artifact дают одинаковый selection result.
- Health Check не содержит `ERROR`/`CRITICAL`, Audit — blocking findings.

## Testing Strategy

- Contract tests фиксируют registry, selection и technology-profile schemas.
- Unit tests покрывают выбор категорий, project-owned discovery, коллизии и rollback.
- Scenario test проходит onboarding recommendation → approval → projection.
- Regression suite доказывает сохранение workflow IDs и существующих контрактов.
- Workspace/release matrices и manifest verification завершают acceptance.

## Risks and Rollback

- Массовое перемещение skill paths может оставить устаревшие ссылки; rollback — вернуть плоские paths, сохранив `distribution`.
- Неполная атомарность может повредить текущую проекцию; rollback — не публиковать staging-каталог до полной проверки.
- Неверная классификация может удалить обязательный provider; rollback — временно перевести его в bundled и повторить contract review.
- Release migration может затронуть project-owned state; rollback — восстановить предыдущий release artifact, не меняя `.orchestrator/skills.json` и `.orchestrator/project-skills/`.

## Implementation Tasks

### Task 1: Нормативные контракты и schemas

**Files:**

- Modify: `docs/specifications/orchestrator-specification-ru.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `config/schemas/registry.schema.json`
- Modify: `config/schemas/technology-profile.schema.json`
- Create: `config/schemas/skill-selection.schema.json`
- Create/Test: `tests/contracts/test_skill_distribution_contract.py`
- Test: `tests/contracts/test_technology_profiles.py`

**Interfaces:**

- Consumes: согласованную модель system, bundled и optional.
- Produces: нормативный registry/selection/profile contract для остальных задач.

**Acceptance:**

- `distribution` обязателен для skill entries и принимает только `system`, `bundled` или `optional`.
- Selection содержит уникальные optional IDs и не управляет system/bundled.
- Technology profile может объявить `recommended_optional_skills`.
- Отрицательные schema cases отклоняются.

**Tests:**

- `python -m unittest tests.contracts.test_skill_distribution_contract -v`
- `python -m unittest tests.contracts.test_technology_profiles -v`

- [ ] **Step 1:** Добавить failing contract cases для отсутствующей/неизвестной distribution, дублирующего selection и некорректной рекомендации.
- [ ] **Step 2:** Запустить focused tests и зафиксировать ожидаемый failure до изменения schemas.
- [ ] **Step 3:** Обновить спецификацию, component contracts и три JSON Schema без расширения scope.
- [ ] **Step 4:** Повторить focused tests и проверить прямое соответствие каждого нормативного требования.
- [ ] **Step 5:** Запустить registry/profile regression tests и сохранить evidence.

### Task 2: Классификация и перемещение canonical skills

**Files:**

- Move: согласованные sources в `skills/system/`, `skills/bundled/`, `skills/optional/`
- Modify: `registries/skills.json`
- Modify: `profiles/technologies/python.yaml`
- Modify: canonical path references в tests и документации
- Test: `tests/contracts/test_skill_installation.py`
- Test: `tests/contracts/test_upstream_skills.py`
- Test: `tests/scenarios/test_audit.py`

**Interfaces:**

- Consumes: distribution schema из Task 1.
- Produces: полную каноническую библиотеку, где каждый skill принадлежит одной категории и сохраняет прежний ID.

**Acceptance:**

- System содержит четыре, bundled — шестнадцать, optional — два согласованных навыка.
- IDs и содержимое навыков не изменены перемещением.
- Workflow references разрешаются по ID.
- Python profile рекомендует `python-code-review`.
- Upstream provenance и documented adaptations сохранены.

**Tests:**

- `python -m unittest tests.contracts.test_skill_installation -v`
- `python -m unittest tests.contracts.test_upstream_skills -v`
- `python -m unittest tests.scenarios.test_audit -v`

- [ ] **Step 1:** Добавить проверки полноты категорий, уникальности ID и разрешения workflow references.
- [ ] **Step 2:** Запустить focused tests и подтвердить failure на текущем плоском registry.
- [ ] **Step 3:** Переместить sources, обновить registry paths, distribution и Python recommendation.
- [ ] **Step 4:** Исправить только canonical path references и повторить focused tests.
- [ ] **Step 5:** Запустить audit/upstream regressions и проверить отсутствие потерянных файлов.

### Task 3: Selection и атомарная синхронизация

**Files:**

- Modify: `orchestrator/skill_installer.py`
- Modify: `orchestrator/health.py`
- Modify/Test: `tests/contracts/test_skill_installation.py`
- Modify/Test: `tests/unit/test_health.py`
- Create/Test: `tests/unit/test_skill_selection.py`

**Interfaces:**

- Consumes: registry, optional selection и `.orchestrator/project-skills/*/SKILL.md`.
- Produces: атомарную platform projection из system + bundled + approved optional + project-owned.

**Acceptance:**

- Отсутствующий selection эквивалентен пустому optional selection.
- Неизвестный/non-optional ID и project-owned collision отклоняются.
- Полная проекция собирается в sibling staging directory и публикуется одной заменой.
- Injected copy failure сохраняет прежнюю проекцию.
- Повторная синхронизация идемпотентна.
- Health проверяет обязательный набор, selection, collisions и итоговый drift.

**Tests:**

- `python -m unittest tests.unit.test_skill_selection -v`
- `python -m unittest tests.contracts.test_skill_installation -v`
- `python -m unittest tests.unit.test_health -v`

- [ ] **Step 1:** Добавить failing tests для default/optional/project-owned selection, collision и injected rollback.
- [ ] **Step 2:** Запустить focused suite и подтвердить ожидаемые failures.
- [ ] **Step 3:** Реализовать loader, selection и staging publication в `skill_installer.py`.
- [ ] **Step 4:** Расширить Health Check и повторить focused suite до полного прохождения.
- [ ] **Step 5:** Запустить affected contract/regression tests и проверить Windows rollback semantics.

### Task 4: Onboarding recommendations и approval boundary

**Files:**

- Modify: `orchestrator/technologies.py`
- Modify: `skills/system/project-onboarding/SKILL.md`
- Modify: `docs/guides/deployment-to-target-project-ru.md`
- Modify/Test: `tests/contracts/test_technology_profiles.py`
- Create/Test: `tests/scenarios/test_optional_skill_onboarding.py`

**Interfaces:**

- Consumes: подтверждённые technology profiles и optional entries registry.
- Produces: read-only recommendation с причиной и skill ID; installation остаётся отдельным approved действием.

**Acceptance:**

- Python sandbox рекомендует `python-code-review`.
- ABAP sandbox не рекомендует отсутствующий пакет.
- `optimizer` доступен для ручного выбора.
- Recommendation не создаёт и не меняет `.orchestrator/skills.json`.
- После явного выбора повторная синхронизация добавляет optional skill.

**Tests:**

- `python -m unittest tests.contracts.test_technology_profiles -v`
- `python -m unittest tests.scenarios.test_optional_skill_onboarding -v`

- [ ] **Step 1:** Добавить failing scenario для recommendation без mutation и последующего approved selection.
- [ ] **Step 2:** Запустить focused tests и подтвердить отсутствие recommendation API.
- [ ] **Step 3:** Реализовать объединение и фильтрацию profile recommendations.
- [ ] **Step 4:** Обновить onboarding skill и deployment guide, затем повторить scenario.
- [ ] **Step 5:** Запустить technology/onboarding regressions и проверить approval boundary.

### Task 5: Release migration и финальная валидация

**Files:**

- Modify: `orchestrator/release.py`, только если новые paths требуют изменения сборки
- Modify/Test: `tests/acceptance/test_release.py`
- Modify: `docs/migrations/1.0.md` или migration note следующего release
- Modify: `CHANGELOG.md`
- Regenerate: platform projections
- Regenerate: release artifact и manifest следующей версии

**Interfaces:**

- Consumes: завершённые Tasks 1–4.
- Produces: воспроизводимый release с полной библиотекой и выборочной target projection.

**Acceptance:**

- Artifact содержит все system, bundled и optional canonical sources.
- Managed и standalone clean install создают одинаковый default skill set.
- Approved optional и project-owned scenarios проходят на release artifact.
- Manifest воспроизводим, checksums корректны, project-owned state сохранён.
- Полная regression suite, обе matrices, Health Check и Audit проходят.

**Tests:**

- `python -m unittest discover -s tests -v`
- `python tests/acceptance/run_matrix.py --strict`
- `python tests/acceptance/run_matrix.py --release <version> --strict`
- `python -m orchestrator health --root . --strict`

- [ ] **Step 1:** Добавить release acceptance cases для default, approved optional и project-owned projections.
- [ ] **Step 2:** Запустить release tests и подтвердить failure старого artifact.
- [ ] **Step 3:** Обновить migration/release assets и регенерировать projections, artifact и manifest.
- [ ] **Step 4:** Запустить полную regression suite и workspace/release matrices.
- [ ] **Step 5:** Запустить Health Check, Audit и manifest verification; зафиксировать completion evidence.
