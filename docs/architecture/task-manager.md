# Task Manager Service в архитектуре Orchestrator

Общая [граница состояния и хранения](state-and-storage.md) определяет владельцев данных и заменяет файловые модели импортированных материалов.

**Статус:** действующая интеграционная граница, 2026-09-14. Полный [контракт сервиса](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md), [инструкция](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) и [пример skill](../../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) поставляются внутри самостоятельного пакета.

Импортированные предложения о файловом каноническом хранилище в [архитектуре](../graph/03-task-manager-service-architecture.md) и [кандидатном API](../graph/04-task-manager-service-contract.md) этим контрактом заменены. Импортированные документы не подтверждают реализацию.

Orchestrator потребляет `orchestrator-task-manager` через публичный Python API. Task Manager владеет состоянием задачи и событиями SQLite в `.orchestrator/state/`; Graph Runtime будет отдельно владеть состоянием запусков, а задача хранит лишь ссылки на них. Онбординг в пакете `orchestrator-onboarding` создаёт версионируемые `.orchestrator/project.json` и `.orchestrator/project-context.md`, но не устанавливает и не запускает Task Manager. Внешние трекеры не являются источником истины.

Пакет уже позволяет вручную создавать, просматривать и защищённо менять задачи. Первый входной срез Task Creator реализован в корневом пакете `orchestrator` и использует этот публичный API; core Graph Runtime реализован отдельно как in-memory runtime одной сессии. Artifact Repository v1 — независимый файловый владелец payload и SHA-256; Task Manager хранит только ссылки и метаданные, не импортирует и не вызывает репозиторий. [Preparation Workflow](preparation-workflow.md) связывает подготовку до `ready` через публичный API при явном запуске caller-ом. Executor Loop, автоматический claim и исполнение не реализованы. Настройка проекта или создание задачи сами по себе не запускают граф и не выполняют работу.
