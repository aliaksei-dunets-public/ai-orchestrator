# Task Manager Service в архитектуре Orchestrator

**Статус:** действующая интеграционная граница, 2026-09-14. Полный [контракт сервиса](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md), [инструкция](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) и [пример skill](../../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) поставляются внутри самостоятельного пакета.

Импортированные предложения о файловом каноническом хранилище в [архитектуре](../graph/03-task-manager-service-architecture.md) и [кандидатном API](../graph/04-task-manager-service-contract.md) этим контрактом заменены. Импортированные документы не подтверждают реализацию.

Orchestrator потребляет `orchestrator-task-manager` через публичный Python API. Task Manager владеет состоянием задачи и событиями SQLite в `.orchestrator/state/`; Graph Runtime будет отдельно владеть состоянием запусков, а задача хранит лишь ссылки на них. Онбординг в пакете `orchestrator-onboarding` создаёт версионируемые `.orchestrator/project.json` и `.orchestrator/project-context.md`, но не устанавливает и не запускает Task Manager. Внешние трекеры не являются источником истины.

Пакет уже позволяет вручную создавать, просматривать и защищённо менять задачи. Task Creator, Artifact Repository, Graph Runtime и Executor Loop ещё не реализованы. Следовательно, настройка проекта или создание задачи сами по себе не запускают граф и не выполняют работу.
