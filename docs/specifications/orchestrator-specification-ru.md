# Универсальный AI Orchestrator

## Архитектурная спецификация и roadmap

**Версия:** 0.4
**Статус:** нормативная архитектурная спецификация
**Язык:** русский

## 1. Назначение

AI Orchestrator — переносимое, конфигурируемое ядро для управления задачами разработки, навыками, workflow, проверками качества, документацией, памятью и знаниями. Оно поставляется отдельным Git-репозиторием и подключается к целевым проектам без жёсткой привязки к технологии или агентной платформе.

Поддерживаются два режима:

- **Managed mode** — Git submodule с контролируемыми обновлениями ядра.
- **Standalone mode** — независимая копия, которую проект развивает отдельно.

## 2. Основные принципы

1. Ядро не знает конкретный проект.
2. Проектная специфика задаётся профилями, контекстом и overrides.
3. Навыки имеют одну основную ответственность и явные контракты; coordinator-навык может компоновать другие навыки, не дублируя их ответственность.
4. Workflow собираются из навыков и approval gates.
5. Task Manager остаётся лёгким автоматом состояний.
6. Для маленьких задач используется сокращённый workflow.
7. Автономность ограничивается лимитами и точками остановки.
8. Самоулучшение выполняется только через предложения и явное одобрение пользователя.
9. Любая новая capability должна иметь документацию и тестовый сценарий.
10. Security policies нельзя незаметно отменить локальным override.

### 2.1. Нормативность и источники истины

- Этот документ является источником истины для архитектурных границ, общей последовательности lifecycle и roadmap продукта.
- `task-layer-specification-ru.md` является источником истины для Task Context, Task Registry, статусов, переходов и Task Manager CLI.
- Если формулировки расходятся, для Task Layer действует более узкая спецификация; расхождение должно быть устранено в обоих документах до релиза.
- Термины «обязан», «запрещён» и «единственный источник истины» задают нормативные требования. Примеры и целевые команды не считаются реализованными возможностями, пока соответствующая фаза не завершена.

## 3. Архитектурные слои

### 3.1. Core

Загружает конфигурацию, профили, реестры и политики; выбирает workflow; контролирует обязательные проверки и формирует итог сессии.

### 3.2. Task Layer

Состоит из четырёх независимых частей:

- **Task Creator** — coordinator workflow, который классифицирует запрос, вызывает специализированные навыки и создаёт Task Context.
- **Task Context** — хранит версионируемое определение задачи и дополняемый Execution Record.
- **Task Manager** — управляет очередью, операционным статусом и ссылкой на Task Context.
- **Task Execution Workflow** — выполняет задачу и проводит проверки.

Детальный контракт находится в `task-layer-specification-ru.md`.

### 3.3. Workflow Engine

Исполняет декларативные сценарии, обрабатывает переходы, повторы, ошибки, fallback и пользовательские approval gates.

### 3.4. Skills

Базовый набор. `task-creator` является coordinator-навыком Task Creation Workflow; остальные элементы предоставляют атомарные операции или проверки:

- task-manager;
- task-creator;
- task-analyzer;
- task-classifier;
- task-specification-writer;
- plan-writer;
- plan-reviewer;
- task-context-validator;
- implementation-runner;
- test-designer;
- test-runner;
- task-reviewer;
- code-reviewer;
- security-reviewer;
- documentation-manager;
- session-reporter;
- memory-manager;
- knowledge-curator;
- orchestrator-health-check;
- orchestrator-auditor;
- improvement-designer.

Каталог `skills/` является каноническим source переносимых навыков. Platform-каталоги, включая `.codex/skills/`, являются устанавливаемыми проекциями: installer создаёт или обновляет их из `skills/`, а Health Check обнаруживает drift. Ручное редактирование platform-копий после появления канонического source запрещено.

Skill entrypoint содержит только назначение, routing, обязательные invariants и компактный output contract. Подробные процедуры и platform/technology-specific знания загружаются через references только после классификации задачи; независимый reviewer запускается только при явной границе риска или необходимости изоляции.

### 3.5. Registries

Реестры skills, workflows, capabilities, platform profiles, technology profiles, templates и policies являются единым каталогом доступных компонентов.

### 3.6. Platform Profiles

Описывают возможности среды выполнения: shell, Git, MCP, virtual URI, sub-agents, параллельность, память, интерактивность, commits и pull requests.

Порядок целевой поддержки: OpenAI Codex как базовая среда, затем Google Antigravity, GitHub Copilot VS Code и Claude VS Code. Каждый новый adapter добавляется только после прохождения общего capability contract предыдущей платформой.

Каждый platform profile обязан объявлять maturity `stable` или `experimental` и раздельные результаты общего contract matrix и native smoke run. Статус `stable` разрешён только при `passed` для обеих проверок и наличии evidence; evidence native smoke фиксирует host/version, ОС или runtime, дату, запущенную проверку и результат. Прохождение contract matrix в другой среде не заменяет native smoke в vendor host: такой profile остаётся `experimental`, но может участвовать в общей матрице переносимости.

### 3.7. Technology Profiles

Описывают способ работы со стеком: структуру каталогов, build/test commands, review rules, security tools, документацию и технологические overrides.

Примеры: Python, TypeScript, ABAP, ABAP RAP, Java, .NET и composite profiles.

### 3.8. Project Context

Содержит назначение проекта, архитектуру, модули, бизнес-правила, неймспейсы, conventions, ADR, команды, критичные зоны, security constraints и внутреннюю документацию.

### 3.9. Project Overrides

Позволяют локально включать и отключать навыки, заменять шаблоны и шаги workflow, изменять quality gates и задавать platform fallback, не редактируя ядро.

### 3.10. Memory and Knowledge

Содержит session reports, observations, decisions, lessons, project memory, knowledge graph и improvement proposals.

## 4. Иерархия конфигурации

Порядок загрузки:

1. core defaults;
2. core policies;
3. platform profile;
4. technology profiles;
5. project context;
6. project overrides;
7. task-specific instructions;
8. пользовательские инструкции текущей сессии.

Каждый следующий слой имеет приоритет над предыдущим только в пределах разрешённых настроек. Immutable security policies имеют безусловный приоритет и не могут быть ослаблены ни project override, ни task-specific, ни пользовательской инструкцией.

## 5. Структура репозитория

```text
ai-orchestrator/
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── ROADMAP.md
├── docs/
│   ├── architecture/
│   ├── adr/
│   └── specifications/
├── orchestrator/
├── config/
│   └── schemas/
├── registries/
├── capabilities/
├── skills/
├── workflows/
├── profiles/
│   ├── platforms/
│   └── technologies/
├── templates/
├── memory/
├── knowledge/
├── tests/
│   ├── unit/
│   ├── contracts/
│   ├── scenarios/
│   ├── regression/
│   └── sandbox-projects/
├── examples/
└── releases/
```

Локальный operational state целевого проекта находится в `.orchestrator/` и не является частью переносимого core. Task Registry, временные и lock-файлы исключаются из Git; Task Context, планы, код, тесты и документация остаются версионируемыми.

## 6. Project Onboarding

Onboarding знакомит оркестратор с целевым проектом без изменения ядра:

1. определяет платформу и инструменты;
2. распознаёт технологический стек;
3. изучает структуру, код и документацию;
4. находит build/test commands, conventions, ADR и security constraints;
5. предлагает technology profiles;
6. создаёт project context и начальный knowledge graph;
7. показывает diff пользователю;
8. активирует профиль после подтверждения.

Повторный onboarding обновляет только изменившиеся части и сохраняет ручные правки.

## 7. Orchestrator Health Check

Health Check — ранняя детерминированная диагностика установленного оркестратора.

Проверяет:

- обязательные файлы и каталоги;
- соответствие конфигурации схемам;
- ссылки в registries;
- совместимость platform и technology profiles;
- наличие project context;
- доступность инструментов и MCP;
- целостность Task Registry;
- отсутствие нескольких задач, занимающих слот выполнения согласно Task Layer;
- версии схем и неизвестные параметры.

Уровни: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

Команды целевой реализации:

```bash
orchestrator health
orchestrator health --json
orchestrator health --strict
orchestrator health --scope tasks
```

Health Check сообщает о проблемах; автоматическое исправление допускается только для безопасных, детерминированных операций.

### 7.1. Execution Telemetry

Execution runtime может писать числовые события в локальный JSONL sink `.orchestrator/telemetry/events.jsonl`. Telemetry содержит duration, attempts, retries, tool calls, agent handoffs и provider-reported token usage, но не сохраняет prompts, tool output или evidence payload. Файл является operational state, исключается из Git и не заменяет Task Context или Execution Record.

Команды:

```bash
orchestrator telemetry
orchestrator telemetry --json
orchestrator telemetry --path <events.jsonl>
```

Отсутствующие provider counters остаются неизвестными и не подменяются оценками. Ошибка telemetry sink отражается в execution result, но не отменяет успешно сохранённый checkpoint.

## 8. Orchestrator Audit

Audit — глубокий смысловой анализ, отличный от Health Check. Он ищет противоречия инструкций, дублирование навыков, недостижимые workflow, устаревшую документацию, архитектурный drift, недостаток тестов и повторяющиеся проблемы из Session Reports.

Audit ничего не меняет автоматически. Его результат — evidence-based improvement proposals.

## 9. Жизненный цикл задачи

```text
User request
→ Task Creation Workflow
→ Task Context validation
→ Task Manager registration
→ Claim task
→ Task Context freshness validation
→ Implementation
→ Tests
→ Task Review when required by mode/risk
→ Code Review when required by mode/risk
→ Security Review
→ User Review when required
→ Documentation
→ Memory and Knowledge
→ Commit
→ Done
→ Session Report (на уровне сессии)
```

Freshness validation, implementation, tests и Security Review обязательны во всех маршрутах. Quick low/medium-risk task использует детерминированный security fast path и не запускает semantic Task/Code Review; finding, sensitive change или high/critical risk повышает глубину проверки. Standard включает Task Review и Code Review, а deep/high-risk — независимый review. Approval и documentation steps добавляются только при соответствующем impact.

Security Review выполняется до передачи изменений пользователю. Статус `done` устанавливается Task Manager только по команде execution workflow после завершения всех выбранных обязательных gates; Task Manager не интерпретирует их содержание. Session Report формируется после остановки execution/backlog loop и не является условием перехода отдельной задачи в `done`.

## 10. Память и знания

- **Session Report** фиксирует выполненную работу, проблемы, решения и рекомендации.
- **Project Memory** хранит подтверждённые наблюдения, решения и уроки между сессиями.
- **Knowledge Graph** содержит структурированные сущности и связи с источниками и историей supersede.
- **Orchestrator Memory** относится только к развитию самого оркестратора.

Наблюдение не становится постоянной инструкцией автоматически.

## 11. Тестовая стратегия

Уровни тестирования:

1. unit tests навыков и CLI;
2. contract tests схем и registries;
3. scenario tests полного workflow;
4. regression tests для каждой найденной ошибки;
5. sandbox projects для разных стеков;
6. cross-platform acceptance tests;
7. dogfooding на реальных проектах.

Repository-wide retrieval по умолчанию работает только с каноническими sources и исключает `releases/`, поскольку release artifacts дублируют проверенные snapshots. Release validation всегда указывает release path явно.

## 12. Roadmap

### Фаза 0 — Архитектурная основа

Зафиксировать концепцию, границы, слои, ADR и roadmap.

### Фаза 1 — Каркас репозитория

Создать `AGENTS.md`, каталоги, registries, schemas, placeholder skills и workflows.

### Фаза 2 — Минимальный Health Check

Проверка структуры, конфигурации, registries и Task Layer; JSON и strict mode.

### Фаза 3 — Session Reporter

Формировать отчёт каждой сессии и источник будущего аудита.

### Фаза 4 — Минимальный Task Manager

JSON Task Registry, статусы, переходы, CLI, `claim-next` и crash-safe записи для одного writer. Межпроцессная блокировка не входит в первую версию.

### Фаза 5 — Quick Task Creator

Создание простой задачи с кратким Task Context и планом.

### Фаза 6 — Standard Task Creator и Plan Review

Анализ bugs/features, brainstorming, спецификация, подробный план и его review.

### Фаза 7 — Implementation Runner

Последовательное исполнение утверждённого плана.

### Фаза 8 — Test Design and Runner

Создание и запуск релевантных тестов, фиксация результатов.

### Фаза 9 — Task Review

Проверка реализации против критериев приёмки.

### Фаза 10 — Code Review

Проверка корректности, качества и сопровождаемости кода.

### Фаза 11 — Security Review

Проверка угроз и регрессий безопасности до user review.

### Фаза 12 — User Review and Approval Gates

Формализовать обязательные пользовательские решения.

### Фаза 13 — Documentation Manager

Определение и выполнение необходимых обновлений документации.

### Фаза 14 — Project Onboarding

Автоматическое формирование project context и начальных знаний.

### Фаза 15 — Platform Profiles

Последовательная адаптация и общий capability contract для Codex, Google Antigravity, GitHub Copilot VS Code и Claude VS Code.

### Фаза 16 — Technology Profiles

Минимум Python и ABAP/ABAP RAP, затем composite profiles.

### Фаза 17 — Project Memory

Долговременные observations, decisions и lessons с защитой секретов.

### Фаза 18 — Knowledge Graph

Ontology, nodes, edges, indexes и conflict/supersede rules.

### Фаза 19 — Backlog Loop

Конечная управляемая обработка нескольких задач, commit per task и stop conditions.

### Фаза 20 — Orchestrator Audit

Анализ отчётов, pattern detection и приоритизация системных проблем.

### Фаза 21 — Controlled Self-Improvement

Improvement proposals, approval workflow, regression tests и rollback.

### Фаза 22 — Multi-Project Validation

Пилоты на Codex, Google Antigravity, GitHub Copilot VS Code и Claude VS Code, минимум двух стеках, а также в managed и standalone mode.

### Фаза 23 — Stable Release 1.0

Стабильные контракты, migration guide, compatibility policy и полный acceptance suite.

### 12.1. Соответствие roadmap Task Layer

Roadmap этого документа является каноническим. Этапы `T0–T9` из Task Layer уточняют его и не образуют вторую независимую очередь:

| Task Layer | Фазы продукта |
| --- | --- |
| T0 — Контракты | 0–1 |
| T1–T3 — Task Manager | 2 и 4 |
| T4 — Quick Task Creator | 5 |
| T5–T6 — Standard/Deep Creator и проверки | 6 |
| T7 — Execution Integration | 7–13 |
| T8 — Backlog Loop | 19 |
| T9 — Platform Validation | 15–16 и 22 |

Планы реализации создаются отдельно для фаз `0–23`; один план может ссылаться на несколько этапов Task Layer, но не должен дублировать их как самостоятельный backlog.

## 13. Definition of Done фазы

Фаза завершена, когда применимые к её scope условия выполнены:

- scope реализован;
- документация и registries обновлены;
- schemas валидны;
- после появления Health Check он не содержит `ERROR` и `CRITICAL`;
- добавлены релевантные unit, contract и scenario tests, а regression test добавлен для каждой исправленной ошибки;
- для исполняемой capability выполнен демонстрационный сценарий;
- после появления Session Reporter сформирован session report, а для выпуска — release notes;
- ограничения и следующий backlog зафиксированы.

## 14. Первый практический релиз 0.1.0

Минимальный релиз включает:

- каркас репозитория;
- `AGENTS.md`;
- registries и schemas;
- placeholder skills/workflows;
- минимальный Health Check;
- Session Reporter;
- JSON Task Registry и Task Manager CLI;
- Quick Task Creator;
- один small execution workflow;
- sandbox project;
- сквозной scenario test.

## 15. Политика самоулучшения

Оркестратор собирает наблюдения и формирует предложения. Изменение skill, workflow, policy или core выполняется как обычная задача развития с явным approval, тестами, release notes и rollback instructions. Автоматическое изменение собственного ядра запрещено.
