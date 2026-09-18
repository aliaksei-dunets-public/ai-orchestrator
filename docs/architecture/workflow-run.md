# Workflow Run: процесс агентской работы

**Статус:** действующая архитектура, актуализирована в TASK-0034, 2026-09-18. Callback GraphRuntime удалён; runtime процесса — AgentGraphRuntime.

Orchestrator Agent читает объявленный Workflow Graph и доступные actions, выполняет работу средствами хоста и явно подаёт структурированный результат. Runtime проверяет node/outcome/output/wait/revision/definition и выбирает target исключительно из графа. Runtime не вызывает исполнителей, не выбирает качество semantic result и не содержит фонового executor loop.

На каждый run есть один canonical владелец в памяти. [Общие модели](graph-runtime-contract.md) отделены в runtime_contracts; [AgentWorkflowRun](agent-runtime-contract.md) добавляет историю, process revision, definition binding и budgets. Публичные snapshots изолированы; rejected action не меняет процесс. RLock защищает локальный compare/check/publish, но не внешний tool или multiprocess lease.

Обычный принятый result продвигает current_node или завершает процесс. Needs_input/blocked оставляют текущий узел и запрещают submit до отдельного resume_wait. Resume сохраняет response и history, не исполняет узел; после него агент подаёт новый result. Cancel фиксирует reason, прекращает принятие дальнейших actions, но не откатывает уже выполненные эффекты и не останавливает сторонний tool.

Task Manager хранит задачу/lifecycle/claim и ссылки, ArtifactRepository — immutable payload. [AgentPreparation](agent-preparation.md) связывает results с готовностью до ready без claim. [AgentExecution](agent-execution.md) проверяет утверждённый package и исходный baseline до claim и принимает work-unit results. Process succeeded не означает task completed: пользовательская приёмка отдельная.

Состояние run/history/response и sync cursor только в памяти. Checkpoints, persisted journal, exactly-once внешних эффектов, автоматическое восстановление и сквозные full execution gates не реализованы. [Будущая координация](runtime-coordination.md) не является текущей возможностью.

Проверки: [общие contracts](../../tests/test_runtime_contracts.py), [runtime](../../tests/test_agent_runtime.py), [preparation](../../tests/test_agent_preparation.py), [execution](../../tests/test_agent_execution.py). Запуск: [runtime guide](../guides/agent-runtime.md), [миграция старого API](../guides/workflow-runtime.md).
