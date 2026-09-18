# Миграция с callback GraphRuntime

**Статус:** действующая инструкция миграции TASK-0034, 2026-09-18. Старые GraphRuntime и `orchestrator.workflow_runtime` удалены; прежние callback-примеры больше не поддерживаются. Alias на агентский класс отсутствует.

Используйте [AgentGraphRuntime](agent-runtime.md) для процесса, [AgentPreparation](agent-preparation.md) для подготовки задачи и [AgentExecution](agent-execution.md) для исполнения после ready/preflight/claim.

| Прежний вызов | Агентский путь |
| --- | --- |
| GraphRuntime.create_run | AgentGraphRuntime.create_run; task-bound run также требует task_definition_version |
| step(run_id, executor) | Агент читает available_actions, выполняет работу и вызывает submit_result с expected_revision/definition |
| resume(run_id, answer, executor) | resume_wait с точными версиями/wait_id/node_id и answer; затем отдельная работа и submit_result |
| resume_blocked(..., answer=...) | resume_wait с resolution без answer, после фактического устранения причины |
| cancel(run_id, reason) | cancel с expected_revision/definition; reason сохраняется в history |
| PreparationWorkflow с adapters | AgentPreparation с явными semantic envelopes; adapters/step отсутствуют |

Graph, Node, NodeResult, WaitState, WorkflowRun, RuntimeError и validate_node_result остаются публичными из `orchestrator`; внутренние импорты переводятся на `orchestrator.runtime_contracts`. Общая модель WorkflowRun не исполняет callbacks и не хранит второй снимок процесса.

Новое blocked требует явного blocker WaitState и конкретной reason; runtime не синтезирует причину. Данные agent API должны быть JSON без NaN/Infinity, cycles, tuples и преобразования ключей. Учитывайте вопросы и итоговые outputs в max_results/node_limits: resume не сбрасывает исчерпанный бюджет. Принятый response хранится в resumed_wait и history; rejected result его не стирает.

После конфликта перечитайте процесс и карточку задачи, сопоставьте history и эффекты, затем решите, безопасен ли новый action. Success процесса не означает completed задачи. Cancel не останавливает сторонний tool, не откатывает файлы и не отменяет карточку Task Manager. Межсессионного восстановления нет.

Проверки: `python -m unittest tests.test_runtime_contracts tests.test_agent_runtime tests.test_agent_preparation`. [Отчёт удаления](../reports/2026-09-18-task-0034-callback-removal.md).
