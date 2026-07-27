- можно ли выполнять команды;
- доступна ли долговременная память;
- есть ли ограничения длины контекста;
- есть ли интерактивный пользователь;
- можно ли создавать коммиты;
- можно ли открывать pull request;
- какие форматы инструкций поддерживаются платформой.

### 5.7. Layer 7 — Technology Profiles

Технологический профиль описывает, как работать с определённым стеком.

Примеры:

- Python;
- TypeScript;
- ABAP;
- ABAP RAP;
- Java;
- .NET;
- смешанный профиль Python + frontend;
- монорепозиторий.

Технологический профиль содержит:

- типичную структуру каталогов;
- правила поиска исходного кода;
- команды сборки;
- команды тестирования;
- статические анализаторы;
- security tools;
- правила code review;
- правила именования;
- требования к документации;
- типичные риски;
- доступные MCP-инструменты;
- способы чтения виртуальных ресурсов;
- технологические skills overrides.

### 5.8. Layer 8 — Project Context

Проектный контекст описывает конкретный целевой проект.

Содержит:

- назначение проекта;
- архитектуру;
- структуру модулей;
- бизнес-правила;
- ключевые доменные термины;
- неймспейсы;
- правила именования;
- соглашения;
- ADR;
- ограничения;
- команды проекта;
- правила релиза;
- критичные области;
- ссылки на внутреннюю документацию;
- описание тестового окружения;
- правила безопасности;
- активные интеграции.

### 5.9. Layer 9 — Project Overrides

Overrides позволяют изменить поведение ядра без редактирования универсального репозитория.

Overrides могут:

- отключить навык;
- заменить шаблон;
- изменить обязательность review;
- изменить классификацию задачи;
- добавить проектное правило;
- переопределить команду тестов;
- заменить шаг workflow;
- добавить локальный policy;
- указать платформенный fallback.

### 5.10. Layer 10 — Memory and Knowledge

Слой накопления опыта и структурированных знаний.

Содержит:

- session reports;
- observations;
- decisions;
- lessons learned;
- project memory;
- orchestrator memory;
- knowledge graph;
- improvement proposals;
- историю принятых и отклонённых предложений.

---

## 6. Предлагаемая структура репозитория

```text
universal-orchestrator/
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── ROADMAP.md
├── LICENSE
├── VERSION
│
├── docs/
│   ├── vision.md
│   ├── architecture.md
│   ├── concepts.md
│   ├── lifecycle.md
│   ├── configuration.md
│   ├── deployment-modes.md
│   ├── security-model.md
│   ├── testing-strategy.md
│   ├── specifications/
│   │   └── task-layer.md
│   ├── contribution-guide.md
│   └── adr/
│       ├── README.md
│       └── ADR-0001-core-profile-separation.md
│
├── orchestrator/
│   ├── identity.md
│   ├── principles.md
│   ├── instructions.md
│   ├── routing.md
│   ├── lifecycle.md
│   ├── state-machine.md
│   ├── approval-gates.md
│   └── error-handling.md
│
├── config/
│   ├── orchestrator.defaults.yaml
│   ├── task-classification.yaml
│   ├── quality-gates.yaml
│   ├── autonomy.yaml
│   ├── memory.yaml
│   └── schemas/
│       ├── orchestrator.schema.json
│       ├── task-registry.schema.json
│       ├── task-manager-config.schema.json
│       ├── task-creation-config.schema.json
│       ├── task-context-contract.schema.json
│       ├── workflow.schema.json
│       ├── skill.schema.json
│       ├── platform-profile.schema.json
│       ├── technology-profile.schema.json
│       ├── project-context.schema.json
│       └── health-check-report.schema.json
│
├── registries/
│   ├── skills.yaml
│   ├── workflows.yaml
│   ├── capabilities.yaml
│   ├── platform-profiles.yaml
│   ├── technology-profiles.yaml
│   ├── templates.yaml
│   └── policies.yaml
│
├── capabilities/
│   ├── task-creation/
│   │   └── capability.md
│   ├── task-management/
│   │   └── capability.md
│   ├── planning/
│   │   └── capability.md
│   ├── task-execution/
│   │   └── capability.md
│   ├── implementation/
│   │   └── capability.md
│   ├── quality-assurance/
│   │   └── capability.md
│   ├── security/
│   │   └── capability.md
│   ├── documentation/
│   │   └── capability.md
│   ├── knowledge-management/
│   │   └── capability.md
│   ├── diagnostics/
│   │   └── capability.md
│   └── self-improvement/
│       └── capability.md
│
├── skills/
│   ├── task-manager/
│   │   ├── SKILL.md
│   │   ├── contract.yaml
│   │   ├── examples/
│   │   └── tests/
│   ├── task-creator/
│   ├── task-analyzer/
│   ├── task-classifier/
│   ├── task-specification-writer/
│   ├── plan-writer/
│   ├── plan-reviewer/
│   ├── task-context-validator/
│   ├── implementation-runner/
│   ├── test-designer/
│   ├── test-runner/
│   ├── task-reviewer/
│   ├── code-reviewer/
│   ├── security-reviewer/
│   ├── documentation-manager/
│   ├── knowledge-curator/
│   ├── memory-manager/
│   ├── session-reporter/
│   ├── orchestrator-health-check/
│   │   ├── SKILL.md
│   │   ├── health_check.py
│   │   ├── checks/
│   │   └── tests/
│   ├── orchestrator-auditor/
│   └── improvement-designer/
│
├── workflows/
│   ├── task-create.yaml
│   ├── task-create-quick.yaml
│   ├── task-create-standard.yaml
│   ├── task-create-deep.yaml
│   ├── task-small.yaml
│   ├── task-standard.yaml
│   ├── task-complex.yaml
│   ├── task-critical.yaml
│   ├── backlog-loop.yaml
│   ├── project-onboarding.yaml
│   ├── session-close.yaml
│   ├── orchestrator-health-check.yaml
│   ├── orchestrator-audit.yaml
│   └── improvement-implementation.yaml
│
├── profiles/
│   ├── platforms/
│   │   ├── codex/
│   │   │   ├── profile.yaml
│   │   │   ├── instructions.md
│   │   │   └── adapters.md
│   │   ├── github-copilot/
│   │   ├── claude-code/
│   │   ├── antigravity/
│   │   └── generic-local-agent/
│   │
│   └── technologies/
│       ├── python/
│       │   ├── profile.yaml
│       │   ├── review-rules.md
│       │   ├── testing.md
│       │   ├── security.md
│       │   └── skills-overrides/
│       ├── typescript/
│       ├── abap/
│       ├── abap-rap/
│       └── generic/
│
├── templates/
│   ├── project/
│   │   ├── project-context.template.yaml
│   │   ├── project-architecture.template.md
│   │   ├── project-conventions.template.md
│   │   ├── project-security.template.md
│   │   └── project-overrides.template.yaml
│   ├── tasks/
│   │   ├── task-context.contract.md
│   │   ├── task-context.quick.md
│   │   ├── task-context.standard.md
│   │   └── task-context.deep.md
│   ├── reports/
│   │   ├── session-report.template.md
│   │   ├── task-result.template.md
│   │   ├── health-check-report.template.md
│   │   ├── audit-report.template.md
│   │   └── improvement-proposal.template.md
│   └── knowledge/
│       ├── decision.template.md
│       ├── observation.template.md
│       ├── lesson.template.md
│       └── knowledge-node.template.yaml
│
├── memory/
│   ├── README.md
│   ├── orchestrator/
│   │   ├── observations/
│   │   ├── lessons/
│   │   ├── decisions/
│   │   └── proposals/
│   └── schemas/
│       ├── observation.schema.json
│       ├── decision.schema.json
│       └── lesson.schema.json
│
├── knowledge/
│   ├── README.md
│   ├── ontology.yaml
│   ├── graph/
│   ├── indexes/
│   └── schemas/
│       ├── node.schema.json
│       └── edge.schema.json
│
├── tests/
│   ├── unit/
│   ├── contracts/
│   ├── scenarios/
│   ├── regression/
│   ├── fixtures/
│   └── sandbox-projects/
│       ├── python-small/
│       ├── typescript-small/
│       └── abap-simulated/
│
├── examples/
│   ├── managed-mode/
│   ├── standalone-mode/
│   ├── python-project/
│   └── abap-project/
│
└── releases/
    ├── README.md
    └── phase-00/
        ├── scope.md
        ├── acceptance.md
        ├── validation.md
        └── release-notes.md
```

---

## 7. Назначение ключевых файлов

### 7.1. `README.md`

Краткая точка входа:

- что такое оркестратор;
- какие задачи решает;
- как подключить;
- как выбрать managed или standalone mode;
- как выполнить onboarding проекта;
- как запустить первую задачу;
- где находится roadmap.

### 7.2. `AGENTS.md`

Главный машиночитаемый и человекочитаемый манифест поведения оркестратора.

Он должен содержать:

- роль оркестратора;
- порядок загрузки инструкций;
- иерархию конфигурации;
- список основных capabilities;
- ссылки на registry;
- общие правила безопасности;
- правила остановки;
- правила пользовательского approval;
- правила работы с памятью;
- запрет на автоматическое самоизменение;
- порядок выбора workflow;
- порядок закрытия сессии.

`AGENTS.md` не должен содержать детальную реализацию каждого навыка. Он должен ссылаться на отдельные `SKILL.md`, workflow и policies.

### 7.3. `ROADMAP.md`

Центральный план развития продукта.

Для каждой фазы:

- цель;
- scope;
- deliverables;
- зависимости;
- out of scope;
- критерии готовности;
- тестирование;
- демонстрационный сценарий;
- риски;
- migration notes.

### 7.4. `registries/skills.yaml`

Содержит список навыков:

```yaml
skills:
  - id: task-manager
    version: 0.1.0
    status: planned
    capability: task-management
    entrypoint: skills/task-manager/SKILL.md
    contract: skills/task-manager/contract.yaml
    enabled_by_default: true

  - id: code-reviewer
    version: 0.0.0
    status: placeholder
    capability: quality-assurance
    entrypoint: skills/code-reviewer/SKILL.md
    enabled_by_default: false
```

Допустимые статусы:

- placeholder;
- planned;
- experimental;
- active;
- deprecated;
- disabled.

### 7.5. `skills/<skill>/SKILL.md`

Каждый навык описывается по единому контракту:

1. Назначение.
2. Ответственность.
3. Когда использовать.
4. Когда не использовать.
5. Входные данные.
6. Выходные данные.
7. Предусловия.
8. Алгоритм.
9. Критерии успеха.
10. Ошибки и fallback.
11. Взаимодействие с другими навыками.
12. Платформенные ограничения.
13. Технологические overrides.
14. Примеры.
15. Тестовые сценарии.

### 7.6. `workflows/*.yaml`

Workflow задаются декларативно и делятся минимум на два семейства:

- создание задачи;
- выполнение зарегистрированной задачи.

