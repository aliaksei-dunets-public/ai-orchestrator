# План проверки Workflow Runtime v1

**Статус:** одобрен для TASK-0004; документ фиксирует границы проверки, 2026-09-17.

## Объём проверки

Проверяется уже реализованный `orchestrator.workflow_runtime` для одного in-memory запуска в одной real-time сессии:

- создание и инспекция запуска;
- последовательный `step` и terminal outcomes;
- `needs_input`/`resume` с проверкой `wait_id` и `node_id`;
- `blocked`/`resume_blocked`, отмена и структурированные ошибки;
- глубокая изоляция входов, снимков и результатов;
- валидация Graph/Node/Artifact contract.

## Документационные результаты

- [пользовательский guide runtime](../guides/workflow-runtime.md);
- [действующий контракт](../architecture/graph-runtime-contract.md);
- [архитектура запуска](../architecture/workflow-run.md);
- [пауза и возобновление](../architecture/workflow-pause-resume.md).

## Граница Task Manager

TASK-0004 не добавляет интеграционный адаптер и не меняет Task Manager. Runtime хранит текущее состояние в памяти; Task Manager остаётся владельцем задачи и получает только ссылку `run_ref` через публичный API. Автоматическое связывание, Executor Loop, checkpoints и восстановление между сессиями относятся к следующим этапам.

## Проверки

Результаты команд и число тестов фиксируются в отчёте TASK-0004 и `docs/worklog.md` после выполнения.
