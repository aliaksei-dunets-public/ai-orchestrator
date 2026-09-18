# AgentGraphRuntime v1: явные действия агента

**Статус:** реализованный Python-контракт первого среза TASK-0028, 2026-09-17. In-memory runtime; не MCP-сервер, не durable workflow и не полный Orchestrator Agent.

## Владельцы

`AgentGraphRuntime` хранит отдельные агентские runs и не вызывает executor/classifier/planner/reviewer. Агент читает доступные actions, выполняет работу средствами хоста, выбирает подтверждённый outcome и явно подаёт NodeResult. Объявленный Graph ограничивает переход; произвольного route.target нет.

Legacy `GraphRuntime` и `PreparationWorkflow` сохраняют старые callbacks. Новый runtime не оборачивает `step` и не держит второй canonical снимок legacy run: на каждый run есть один владелец процесса. Graph/Node/NodeResult/WaitState переиспользуются; общий публичный `validate_node_result` выполняет структурную проверку и используется обоими runtime.

Task Manager полностью неизменён. Новый runtime не импортирует его и не меняет task lifecycle, events или SQLite. `phase="execution"` — метка процесса, не разрешение исполнять ещё не ready задачу. Caller отдельно соблюдает ready/claim/acceptance guards через публичный сервис. NodeResult hash проверяется по форме, не по payload repository; это не semantic gate.

## Python API

```text
create_run(graph, inputs, *, task_ref=None, task_definition_version=None,
           run_id=None, phase="request", max_results=100, node_limits=None)
inspect_run(run_id)
available_actions(run_id)
submit_result(run_id, result, *, expected_revision, task_definition_version=None)
resume_wait(run_id, *, expected_revision, wait_id, node_id,
            answer=<не передан>, resolution=None, task_definition_version=None)
cancel(run_id, reason, *, expected_revision, task_definition_version=None)
```

Мутации возвращают изолированный `AgentWorkflowRun`; inspect возвращает копию. `available_actions` — обычный JSON-совместимый словарь. Методы не выполняют внешние effects и не синхронизируют файлы/Task Manager.

## Создание и снимок

Graph соответствует [существующим моделям](graph-runtime-contract.md); новый runtime дополнительно запрещает node_id, совпадающий с терминальным target `succeeded/failed/cancelled`, чтобы переход не был неоднозначным. inputs должен быть JSON-объектом. `phase` — request/preparation/execution. Повтор run_id запрещён.

При task_ref требуется положительный целочисленный task_definition_version, без task_ref версия не передаётся. Bool не считается int. Это закрепление версии определения задачи, не task.version и не source snapshot. Caller должен перед каждой task-bound мутацией прочитать текущую definition_version публичным Task Manager API и передать её: runtime самостоятельно карточку не проверяет. Передача устаревшей версии как будто она текущая не может быть обнаружена generic сервисом.

`AgentWorkflowRun` наследует минимальный WorkflowRun, добавляя:

| Поле | Правило |
| --- | --- |
| revision | 1 при создании, +1 после каждого принятого submit/resume/cancel |
| task_definition_version | Закреплённая версия определения, nullable для запроса без задачи |
| max_results | Положительный общий budget принятых NodeResult, по умолчанию 100 |
| node_limits | Необязательные положительные budgets по существующим node_id |
| result_counts | Число принятых results по узлам, включая needs_input/blocked/failure |
| history | Все принятые submit/resume/cancel с новой revision и данными action, только в памяти |
| resumed_wait | Принятый ответ или resolution для текущего узла; очищается следующим валидным submit/cancel |

Legacy WorkflowRun serialization не получает этих полей. Runtime.results хранит последний result каждого узла, history — все принятые actions нового процесса. Graph/версия неизменны внутри run. Для другой версии workflow нужен новый run.

## Submit и границы проверки

Разрешён только в created/running. expected_revision положителен и равен текущему revision; task_definition_version равна закреплённой. Чужой node_id, не объявленный outcome, неправильные mappings, отсутствующие required_outputs и структурно неправильный artifact отклоняются. Agent API дополнительно требует JSON-представимые значения без NaN/Infinity, cycles, tuples или преобразования нестроковых ключей. Result копируется перед проверкой.

Весь result и counters проверяются до публикации. При обычном outcome target берётся исключительно из graph transitions. Терминальный target завершает процесс и обнуляет current_node. Успех workflow не выставляет задаче completed.

needs_input требует WaitState kind=user_input с непустым question; blocked — kind=blocker с непустым reason. wait принадлежит текущему узлу, не содержит заранее записанного answer; его wait_id не использован раньше в этом run. Эти исходы сохраняют текущий узел и останавливают submit. Все остальные outcomes запрещают wait. Автоматическое угадывание причины blocker отсутствует.

## Resume

Разрешён только для waiting_input/blocked и точных wait_id/node_id/revision/definition. Для user_input caller явно передаёт JSON answer (null допустим), без resolution. Для blocker — непустую resolution, без answer. Runtime не доказывает, что ответ действительно дал пользователь или доступ действительно восстановлен; это обязанность agent/host интеграции.

Принятие ответа — отдельный action: revision растёт, state становится running, узел остаётся прежним, wait очищается, resumed_wait хранит response. Узел не исполняется автоматически, result_counts не увеличиваются. Агент читает response, выполняет работу и подаёт новый result. Ошибка нового result не теряет уже принятый ответ; history сохраняет его и после последующего submit.

## Actions, budgets и отмена

available_actions возвращает revision/state/definition, actions, remaining_results, описание текущего node с contracts/required_outputs/outcomes/transitions и wait. inspect/available_actions доступны всегда. Submit доступен только при активном узле и remaining budget; resume — в ожидании; cancel — в любом нетерминальном состоянии. Терминальный run не имеет actions.

remaining_results — минимум общего и текущего per-node budget. Все accepted results расходуют budget, resume/cancel — нет. На exhausted budget новый result отклоняется без автоматической блокировки/сброса counters; агент отменяет процесс или явно подготавливает дальнейшее решение, не крутит тот же цикл бесконечно. Wait, израсходовавший последний slot, всё ещё может принять ответ, но не следующий result. Budget должен предусматривать и вопросы, и итоговые outputs.

Cancel увеличивает revision, фиксирует reason и очищает waits; сохраняет местоположение отмены в current_node. Отмена процесса не отменяет задачу, не останавливает сторонний tool и не откатывает файлы. Caller должен предварительно убедиться, что исполнитель остановлен; generic runtime исполнителя не запускает.

## Ошибки и атомарность

Коды: contract_violation, run_not_found, run_revision_conflict, stale_definition, invalid_state, node_mismatch, unknown_outcome, stale_wait, result_limit_exceeded. RuntimeError содержит code/details/as_dict. При rejected action revision/state/counters/history/response не меняются. Неверная Python-сигнатура остаётся TypeError.

RLock защищает compare/check/publish и снимки внутри одного процесса; два submit с одинаковой revision дают один accepted и один conflict. Это не lease исполнителя, actor authorization или multiprocess coordination. После неизвестного результата caller сначала inspect/history, затем решает, безопасно ли новое действие; автоматической idempotent retry нет.

История и deep-copy snapshots требуют память, зависящую от payload и числа действий. Budget ограничивает число results, но не размер payload. Persistence/checkpoints, внешние permission guards, semantic review и transaction с artifacts/tasks остаются последующими срезами. Тесты: [Agent Runtime](../../tests/test_agent_runtime.py), использование: [guide](../guides/agent-runtime.md).
