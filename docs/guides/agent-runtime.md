# Работа агента через явный Graph Runtime

**Статус:** runnable guide реализованного Python API TASK-0028, 2026-09-17. Это process primitive, не установленный agent skill и не MCP transport.

## Выбор пути

Используйте `AgentGraphRuntime` — единственный поддерживаемый runtime. Callback GraphRuntime/PreparationWorkflow удалены в TASK-0034; [инструкция миграции](workflow-runtime.md). Не передавайте один run_id между разными экземплярами/runtime и не переключайте путь скрыто после ошибки.

Нужен корневой исходный пакет `orchestrator` и уже установленный Task Manager (корневой facade импортирует существующие компоненты). В текущем репозитории пример работает из корня в `.venv`. Никаких Graphify зависимостей или настроек хоста для него не требуется.

## Полный пример вопроса и результата

```python
from orchestrator import AgentGraphRuntime, Graph, Node, NodeResult, WaitState

graph = Graph("agent-example", 1, "analysis", {
    "analysis": Node("analysis", "request/v1", "analysis/v1",
                     ("needs_input", "success"),
                     {"needs_input": "analysis", "success": "succeeded"}),
})
runtime = AgentGraphRuntime()
run = runtime.create_run(graph, {"request": "Уточнить режим"}, max_results=4)
assert runtime.available_actions(run.run_id)["actions"] == ["submit_result", "cancel"]

# Агент определил недостающую информацию. Runtime только сохраняет ожидание.
run = runtime.submit_result(run.run_id, NodeResult(
    "analysis", "needs_input",
    wait=WaitState("WAIT-MODE-1", "analysis", "user_input", question="Какой режим?"),
), expected_revision=run.revision)
assert run.state == "waiting_input"

# После реального ответа пользователя агент явно регистрирует его.
run = runtime.resume_wait(run.run_id, expected_revision=run.revision,
                          wait_id="WAIT-MODE-1", node_id="analysis", answer="Локальный")
assert run.current_node == "analysis" and run.resumed_wait["answer"] == "Локальный"

# Агент выполняет анализ, затем передаёт результат. Callback не вызывается.
run = runtime.submit_result(run.run_id, NodeResult(
    "analysis", "success", data={"mode": run.resumed_wait["answer"]},
), expected_revision=run.revision)
assert run.state == "succeeded" and run.revision == 4
assert [event["action"] for event in run.history] == ["submit_result", "resume_wait", "submit_result"]
```

Строка ответа в примере демонстрационная. В реальной работе нельзя выдавать выдуманный ответ за user decision; runtime не проводит аутентификацию автора. NodeResult outcome агент выбирает по evidence, а target ограничен transitions.

## Привязка к задаче

Перед create прочитайте карточку Task Manager публичным API. Передайте task_ref=id и task_definition_version=definition_version. Перед каждым submit/resume/cancel перечитайте карточку и передайте её текущую definition_version и revision из inspect_run. task.version используется отдельно для мутаций Task Manager.

Если definition изменилось, runtime вернёт stale_definition: новая подготовка/новый run, а не echo старой версии ради обхода. Runtime не проверяет базу самостоятельно. Lifecycle задачи остаётся отдельным: подготовка реально создаёт artifacts, plan/review/package и вызывает существующий mark_ready; исполнение требует claim. Сам process success не меняет задачу. Связывание подготовки реализовано в [AgentPreparation](agent-preparation.md), а preflight/claim и work units — в [AgentExecution](agent-execution.md). Полные execution gates остаются следующим срезом.

## Отказ и возобновление

После run_revision_conflict перечитайте процесс и history; не повторяйте старый result для другого узла или с новой revision вслепую. После ошибки проверки state не изменился, поэтому можно исправить malformed result без повторного исполнения уже сделанного tool effect.

Для blocked подайте WaitState с kind=blocker и конкретной reason; после фактического устранения причины вызовите resume_wait с resolution, без answer. Для needs_input используйте answer, не resolution. Каждый новый вопрос получает новый wait_id даже при повторном входе в тот же узел.

При exhausted budget submit_result отсутствует в actions. Не сбрасывайте счётчики: диагностируйте причины, отмените текущий run при необходимости и явно подготовьте дальнейшую работу. Cancel требует актуальные revision/definition и reason, не откатывает изменения и не отменяет Task Manager карточку.

## Ограничения

Состояние только в памяти текущего Python-процесса. Закрытие процесса теряет history и waits; SQLite задачи не восстанавливает их. MCP/CLI нового runtime, durable checkpoints, artifact publication/sync, workspaces и permission enforcement не входят в этот API. Модель JSON-совместима, но import/export сохранённых runs ещё не реализованы.

Подробности: [контракт](../architecture/agent-runtime-contract.md), [отчёт среза](../reports/2026-09-17-agent-runtime-v1.md), [подтверждённый дизайн миграции](../plans/2026-09-17-agent-centric-graphify-migration-design.md).
