# Универсальный AI Orchestrator

## Архитектурная спецификация и roadmap

**Версия:** 0.3  
**Статус:** начальная спецификация продукта  
**Язык:** русский

## 1. Назначение

AI Orchestrator — переносимое, конфигурируемое ядро для управления задачами разработки, навыками, workflow, проверками качества, документацией, памятью и знаниями. Оно поставляется отдельным Git-репозиторием и подключается к целевым проектам без жёсткой привязки к технологии или агентной платформе.

Поддерживаются два режима:

- **Managed mode** — Git submodule с контролируемыми обновлениями ядра.
- **Standalone mode** — независимая копия, которую проект развивает отдельно.

## 2. Основные принципы

1. Ядро не знает конкретный проект.
2. Проектная специфика задаётся профилями, контекстом и overrides.
3. Навыки атомарны и имеют явные контракты.
4. Workflow собираются из навыков и approval gates.
5. Task Manager остаётся лёгким автоматом состояний.
6. Для маленьких задач используется сокращённый workflow.
7. Автономность ограничивается лимитами и точками остановки.
8. Самоулучшение выполняется только через предложения и явное одобрение пользователя.
9. Любая новая capability должна иметь документацию и тестовый сценарий.
10. Security policies нельзя незаметно отменить локальным override.

## 3. Архитектурные слои

### 3.1. Core

Загружает конфигурацию, профили, реестры и политики; выбирает workflow; контролирует обязательные проверки и формирует итог сессии.

### 3.2. Task Layer

Состоит из четырёх независимых частей:

- **Task Creator** — анализирует запрос и создаёт Task Context.
- **Task Context** — хранит постановку, анализ, критерии, план и результат.
- **Task Manager** — управляет очередью и внешними статусами.
- **Task Execution Workflow** — выполняет задачу и проводит проверки.

Детальный контракт находится в `task-layer-specification-ru.md`.

### 3.3. Workflow Engine

Исполняет декларативные сценарии, обрабатывает переходы, повторы, ошибки, fallback и пользовательские approval gates.

### 3.4. Skills

Базовый набор:

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

### 3.5. Registries

Реестры skills, workflows, capabilities, platform profiles, technology profiles, templates и policies являются единым каталогом доступных компонентов.

### 3.6. Platform Profiles

Описывают возможности среды выполнения: shell, Git, MCP, virtual URI, sub-agents, параллельность, память, интерактивность, commits и pull requests.

Примеры: OpenAI Codex, GitHub Copilot, Claude Code, Antigravity, локальный и CI-агент.

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

Более локальный слой уточняет общий, но immutable security policies имеют приоритет над локальными настройками.

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
- отсутствие нескольких активных задач;
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
→ Implementation
→ Tests
→ Task Review
→ Code Review
→ Security Review
→ User Review when required
→ Documentation
→ Memory and Knowledge
→ Commit
→ Done
→ Session Report
```

Security Review выполняется до передачи изменений пользователю.

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

JSON Task Registry, статусы, переходы, CLI, `claim-next` и атомарные записи.

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

Адаптация к нескольким агентным платформам и fallback-механизмам.

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

Пилоты на разных стеках, платформах, managed и standalone mode.

### Фаза 23 — Stable Release 1.0

Стабильные контракты, migration guide, compatibility policy и полный acceptance suite.

## 13. Definition of Done фазы

Фаза завершена, когда:

- scope реализован;
- документация и registries обновлены;
- schemas валидны;
- Health Check не содержит `ERROR` и `CRITICAL`;
- добавлены unit, scenario и regression tests;
- демонстрационный сценарий выполнен;
- session report и release notes сформированы;
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
