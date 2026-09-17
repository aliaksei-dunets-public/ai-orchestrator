# Дизайн минимального in-memory Workflow Runtime v1

**Статус:** реализация TASK-0003; документ фиксирует первый исполняемый срез, 2026-09-17.

## Цель и границы

Runtime выполняет один неизменяемый граф для одного агента в одной real-time сессии. Он хранит состояние запуска только в памяти, последовательно исполняет текущий узел через переданный адаптер и проверяет структурированный `NodeResult` до выбора перехода.

В срез не входят SQLite runtime, checkpoints, восстановление после перезапуска, несколько исполнителей, фоновые workers, автоматические повторы и Executor Loop. Task Manager остаётся владельцем задачи; runtime не изменяет SQLite и не дублирует его guards.

## API и модель

Публичный модуль `orchestrator.workflow_runtime` предоставляет `GraphRuntime`, `RuntimeError`, `Graph`, `Node`, `WorkflowRun`, `NodeResult` и `WaitState`. Основные операции:

```text
create_run(graph, inputs, task_ref=None) -> WorkflowRun
inspect_run(run_id) -> WorkflowRun
step(run_id, executor) -> NodeResult | WaitState
resume(run_id, answer, executor, wait_id=None, node_id=None) -> NodeResult | WaitState
resume_blocked(run_id, executor, wait_id=None, node_id=None, answer=None) -> NodeResult | WaitState
cancel(run_id, reason) -> WorkflowRun
```

`executor(node, inputs, run)` возвращает `NodeResult` или структурированную ошибку. Для `needs_input` runtime сохраняет `WaitState`, переводит запуск в `waiting_input` и не выбирает следующий узел. `resume` проверяет `wait_id` и `node_id`, передаёт ответ тому же узлу и продолжает обычную валидацию результата.

## Проверки и ошибки

При создании проверяются уникальность узлов, существующий entry node, версии и переходы. При шаге проверяются текущий узел, `node_id`, допустимый `outcome`, объект `data`, минимальная структурная форма каждого артефакта, обязательные поля ожидания и наличие перехода. Семантические схемы `input_contract`/`output_contract` остаются контрактами вызывающей стороны до появления Artifact Repository. Ошибки имеют коды `run_not_found`, `invalid_state`, `node_mismatch`, `unknown_outcome`, `contract_violation`, `stale_wait`, `blocked` и `execution_failure`.

Все переходы состояния выполняются транзакционно в памяти: executor получает копию запуска, а `step`, `resume` и `resume_blocked` публикуют результат только после полной валидации. Невалидный результат не уничтожает актуальное ожидание и допускает безопасный повтор.

Переход в `succeeded`, `failed` или `cancelled` завершает запуск. Отмена не откатывает внешние побочные эффекты. Один вызов `step` выполняет максимум один узел; следующий узел будет обработан отдельным вызовом.

## Тестирование

Добавляются предметные тесты на граф и переходы, один узел за шаг, terminal outcomes, `needs_input`/resume, атомарный повтор после невалидного resume, `resume_blocked`, stale wait, неизвестные outcomes, node mismatch, дубликаты и malformed nodes, структурированные артефакты, cancel и глубокую изоляцию входов/результатов. Existing request-flow, Task Manager и onboarding tests должны продолжить проходить.
