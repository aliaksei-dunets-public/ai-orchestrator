# Пользовательский гайд Workflow Runtime v1

**Статус:** действующий guide минимального in-memory runtime, 2026-09-17.

## Назначение

`GraphRuntime` выполняет один неизменяемый граф для одного агента в одной real-time сессии. Он принимает результат текущего узла, проверяет его и выбирает переход из объявления графа. Runtime не запускает модель самостоятельно и не является планировщиком фоновых workers.

## Минимальный запуск

```python
from orchestrator import Graph, GraphRuntime, Node, NodeResult

graph = Graph(
    graph_id="demo-v1",
    version=1,
    entry_node="collect",
    nodes={
        "collect": Node(
            "collect", "request/v1", "result/v1",
            ("success",), {"success": "succeeded"},
        ),
    },
)

runtime = GraphRuntime()
run = runtime.create_run(graph, {"request": "Собери данные"})
result = runtime.step(
    run.run_id,
    lambda node, inputs, current: NodeResult(
        node.node_id, "success", data={"answer": "готово"}
    ),
)

assert result.outcome == "success"
assert runtime.inspect_run(run.run_id).state == "succeeded"
```

Один вызов `step` выполняет не более одного узла. Следующий узел обрабатывается следующим вызовом. `inspect_run` возвращает независимый снимок и не даёт внешнему коду изменить внутреннее состояние запуска.

## Пауза и продолжение

Узел может вернуть `WaitState` или `NodeResult(outcome="needs_input", wait=...)`. Runtime сохранит вопрос и переведёт запуск в `waiting_input`:

```python
from orchestrator import NodeResult, WaitState

wait = runtime.step(
    run.run_id,
    lambda node, inputs, current: NodeResult(
        node.node_id,
        "needs_input",
        wait=WaitState("WAIT-1", node.node_id, "user_input", question="Продолжить?"),
    ),
)

result = runtime.resume(
    run.run_id,
    {"confirmed": True},
    lambda node, inputs, current: NodeResult(
        node.node_id, "success", data={"answer": current.wait.answer}
    ),
    wait_id=wait.wait_id,
    node_id=wait.node_id,
)
```

Невалидный результат не уничтожает актуальное ожидание: после исправления executor можно безопасно вызвать повторно. Ответ с устаревшим `wait_id` или чужим `node_id` отклоняется структурированной ошибкой.

## Блокировка и отмена

`outcome="blocked"` останавливает запуск и сохраняет `WaitState(kind="blocker")`. После устранения внешней причины тот же узел продолжается через `resume_blocked(run_id, executor, wait_id=..., node_id=...)`. Простые `step` и `resume` заблокированный запуск не обходят.

`cancel(run_id, reason)` переводит незавершённый запуск в `cancelled`. Уже выполненные внешние побочные эффекты он не откатывает.

## Состояние и границы

- состояние запуска хранится только в памяти текущего `GraphRuntime`;
- Graph Runtime не создаёт SQLite, не пишет Task Manager и не содержит Executor Loop;
- `task_ref` — ссылка на задачу, а не копия её состояния;
- Task Manager изменяется только через публичный `TaskManagerService`/MCP/CLI с актуальной `expected_version`;
- [Preparation Workflow](preparation-workflow.md) отдельно связывает `run_ref` и статусы подготовки; claim и исполнение не входят в этот адаптер;
- многосессионность, checkpoints и автоматическое восстановление относятся к будущим этапам; Artifact Repository v1 уже доступен как независимый слой хранения и пока не связан с runtime автоматически.

## Проверка

Предметные тесты находятся в `tests/test_workflow_runtime.py`. Полный запуск проекта дополнительно включает тесты Task Manager и Onboarding. Отчёт результатов: [TASK-0004](../reports/2026-09-17-workflow-runtime-verification.md).
