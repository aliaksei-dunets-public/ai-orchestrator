# Материалы `docs/development/`

С 2026-09-17 направление пересмотрено по [решению об Orchestrator Agent](01-agent-centric-orchestrator-architecture.md) и [Graphify](01-graphify-integration-ai-orchestrator.md). Русские актуальные границы: [агент-центричная оркестрация](../architecture/agent-centric-orchestration.md) и [Project Knowledge Service](../architecture/project-knowledge-service.md). Старые subgraph/controller схемы ниже — исходники предметных invariants, не команды для разработки нового Python orchestration engine. Task Manager с SQLite не меняется; task.yaml/TaskML и обязательная specification не возвращаются. [Оценка и карта миграции](../reports/2026-09-17-agent-centric-graphify-assessment.md).

Каталог содержит импортированные англоязычные спецификации подграфов разработки: контекст, анализ, спецификацию, планирование, ревью, реализацию, тестирование и документацию.

Эти документы — проектные исходники, а не реализованные модули. Их контракты становятся действующими только после переноса в русскоязычные документы `docs/architecture/` или `docs/guides/`, реализации и тестирования.

Для подготовки TASK-0015 действуют минимальный [контракт Preparation Workflow](../architecture/preparation-workflow.md) и [guide](../guides/preparation-workflow.md): Context → Analysis → Planning → Review → Package → Ready. Карточка Task Manager заменяет обязательную specification.md; approval связан с plan SHA-256/definition version, не запускает Implementation напрямую. Полные импортированные схемы и PKM/LLM стратегии не реализованы автоматически: смысловые адаптеры предоставляет caller.

Текущие ограничения v1:

- состояние задач принадлежит SQLite Task Manager;
- состояние текущего запуска принадлежит in-memory Graph Runtime;
- используется одна real-time сессия агента;
- фоновый Executor Loop, несколько workers и межсессионное восстановление пока не реализуются.

Ссылки на файловое состояние задач, `task.yaml`, `events.jsonl` и фоновые циклы в отдельных спецификациях следует считать историческими или будущими вариантами. Перед реализацией сверяйся с [текущим статусом проекта](../project-status.md), [roadmap](../roadmap.md) и [границей состояния](../architecture/state-and-storage.md).
