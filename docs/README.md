# Orchestrator — проектные материалы

Здесь собраны архитектурные материалы нового графового оркестратора. Большинство импортированных документов пока не подтверждают наличие работающего ядра. Статус каждого документа показывает, является ли он черновиком, принятым проектным решением или действующим контрактом. Реализованные срезы описаны в [контракте настройки проекта](architecture/onboarding.md), [интеграционной границе Task Manager Service](architecture/task-manager.md), [контракте Graph Runtime](architecture/graph-runtime-contract.md), [контракте Artifact Repository](architecture/state-and-storage.md), [гайде Workflow Runtime](guides/workflow-runtime.md), а также в [инструкции настройки](guides/onboarding.md), [инструкции просмотра задач](guides/tasks.md) и [гайде Artifact Repository](guides/artifact-repository.md). Они поставляются отдельными пакетами: [Onboarding](../packages/onboarding/README.md) и [Task Manager Service](../packages/task-manager/README.md). Core Graph Runtime v1 и Artifact Repository v1 реализованы в корневом исходном пакете; связывание подготовки описано ниже. Полный устанавливаемый пакет ядра, интеграция исполнения, persistence runtime и многосессионная координация остаются будущими этапами.

Минимальный [контракт подготовки](architecture/preparation-workflow.md) и [guide](guides/preparation-workflow.md) описывают реализованное в TASK-0015 связывание до `ready`; задача принята пользователем и завершена (version 18). Это не Executor Loop: callbacks предоставляет caller, общей транзакции и cross-session recovery нет.

## Содержание

Согласован принцип графа для одного агента в реальном времени и паузы в той же сессии; действующие детали закреплены в `docs/architecture/`. Core runtime реализует один in-memory запуск с `step`, `resume`, `resume_blocked` и `cancel`. Возможная [будущая функция координации нескольких запусков](architecture/runtime-coordination.md) вынесена отдельно и сейчас не реализуется.

Единая [граница состояния и хранения](architecture/state-and-storage.md) фиксирует SQLite как источник истины задач, Artifact Repository как владельца payload и отделяет документы от состояния запуска в памяти. Core runtime v1, repository v1 и минимальное связывание подготовки реализованы; интеграция исполнения остаётся поэтапной работой.

Действующий контракт Graph, Node, Artifact, WorkflowRun и результата узла закреплён в [контракте Graph Runtime v1](architecture/graph-runtime-contract.md) в рамках TASK-0002; его core-реализация и пользовательская проверка выполнены в TASK-0003–TASK-0004.

- [`graph/`](graph/README.md) — импортированные материалы о маршрутизации запросов, управлении задачами, готовности к исполнению, цикле исполнителя и интеграции с трекерами;
- [`development/`](development/README.md) — импортированные материалы о контексте, анализе, планировании, реализации, проверках, тестах и документации;
- `context-knowledge/` — проект карты знаний и результаты её аудита.
- [Request Router → Task Creator](guides/request-flow.md) — реализованный первый входной срез без автоматического запуска Graph Runtime.
- [Workflow Runtime v1](guides/workflow-runtime.md) — запуск, pause/resume, блокировка и границы интеграции.
- [Инструкция первого запуска](guides/onboarding.md) — wizard-порядок для вопросов, настройки, установки и проверки Task Manager.

Актуальный снимок реализованного состояния для агента находится в [project-status.md](project-status.md). Эти импортированные проектные материалы пока написаны на английском. При внедрении их решения переводятся и актуализируются в русскоязычных действующих документах и гайдах. Прежний продукт сохранён в [`obsolete/`](../obsolete/README.md). Перед реализацией смотри [план миграции](roadmap.md) и [backlog с зависимостями](plans/2026-09-16-orchestrator-roadmap-backlog-design.md); выполненные работы фиксируются в [журнале](worklog.md).
