# Общие контракты графа и процесса

**Статус:** действующий структурный контракт, актуализирован в TASK-0034, 2026-09-18. Callback GraphRuntime удалён; единственный runtime — [AgentGraphRuntime](agent-runtime-contract.md).

Модели и validator находятся в [runtime_contracts.py](../../orchestrator/runtime_contracts.py), публично доступны из `orchestrator`. Модуль не исполняет узлы, не хранит запуски и не содержит executor callbacks.

## Graph и Node

`Graph(graph_id, version, entry_node, nodes)` требует непустой ID, положительную целочисленную version (не bool), существующий entry_node и непустой mapping уникальных Node. `Graph.from_dict` принимает nodes как mapping или список и отклоняет дубликаты, неправильные элементы и неизвестные targets. Nodes и transitions неизменяемы и отделены от входных контейнеров. AgentGraphRuntime дополнительно запрещает node_id `succeeded`, `failed`, `cancelled`, чтобы targets не были неоднозначными.

`Node(node_id, input_contract, output_contract, outcomes, transitions, required_outputs=())` требует непустые строки контрактов и ID, уникальные непустые outcomes и переход для каждого outcome. Target — существующий узел либо терминальное состояние. `required_outputs` перечисляет обязательные ключи data/artifacts. Ссылки input/output_contract не являются встроенным реестром JSON-схем; семантику проверяет владелец контракта.

Обычный исход выбирает target из transitions. `needs_input` и `blocked` имеют специальную семантику: сохраняют текущий узел, хотя формальная запись transitions обязательна. Цель такой записи не запускает отдельный ask/escalation узел. После resume агент подаёт новый обычный result. `retryable_failure`, если объявлен, — обычный исход с явным переходом; автоматических retry policy/backoff нет. Безопасность повторения эффектов проверяет caller; число принятых результатов ограничивают runtime budgets.

## NodeResult и Artifact

`NodeResult(node_id, outcome, artifacts={}, data={}, error=None, wait=None)` описывает результат текущего узла. Публичный `validate_node_result(node, result)` проверяет тип, совпадение node_id, объявленный outcome, mappings data/artifacts, required_outputs и минимальную форму ссылок на артефакты. Ошибки возвращаются как `RuntimeError` с code/details/as_dict; semantic truth и фактический payload не проверяются общим validator.

Каждый artifact имеет непустой строковый ключ, mapping с `ref`, `contract`, `role`, 64 hex `sha256`, а также `value` либо непустой `uri`. Version repository не обязательна в минимальной runtime-ссылке, но профильные facade используют immutable metadata `ref + role + version`. [ArtifactRepository](../guides/artifact-repository.md) проверяет существование, размер и SHA-256 тела. Формально валидная ссылка не является доказательством результата работы или разрешением на ready/commit.

## WaitState

`WaitState(wait_id, node_id, kind, question=None, reason=None, answer=None)` требует непустой wait_id/node_id; kind — user_input или blocker. Общая модель проверяет тип question/reason; runtime дополнительно требует непустой question для needs_input и reason для blocked, отсутствие заранее заданного answer, соответствие текущему узлу и уникальность wait_id внутри run.

Ответ принимается только отдельным `resume_wait` с точными revision/definition/wait_id/node_id. User_input требует явный JSON answer, blocker — непустую resolution без answer. Resume сохраняет ответ и историю, не выполняет узел и не расходует result budget. [Протокол паузы](workflow-pause-resume.md).

## WorkflowRun

Общая dataclass содержит run_id, nullable task_ref, graph_ref/version, phase, state, current_node, inputs, results, wait и last_result. `to_dict` отделяет изменяемые данные от владельца. Это базовая модель снимка, не второй runtime. [AgentWorkflowRun](agent-runtime-contract.md) добавляет revision, definition binding, limits/counters, history и resumed_wait; именно AgentGraphRuntime владеет процессом.

Task Manager владеет задачей, её версиями, claim и lifecycle; runtime — только запуском в памяти. Preparation публикует immutable plan/review/package и вызывает реальные ready guards, execution требует claim. Persistence, checkpoints, multiprocess coordination и общая транзакция с tasks/files не реализованы.

## Проверки и миграция

[Общие contracts tests](../../tests/test_runtime_contracts.py), [agent runtime tests](../../tests/test_agent_runtime.py), [guide](../guides/agent-runtime.md), [миграция callback API](../guides/workflow-runtime.md).
