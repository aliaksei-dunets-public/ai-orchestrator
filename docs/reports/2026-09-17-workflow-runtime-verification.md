# TASK-0004: проверка и документация Workflow Runtime

**Статус:** проверка завершена, задача подготовлена к приёмке.

## Итог

TASK-0004 подтверждает уже реализованный core Graph Runtime v1 и закрывает документационный разрыв после TASK-0003. Новых runtime-переходов, Task Manager adapter или persistent storage на этом этапе не добавлялось.

## Проверенные возможности

- последовательное выполнение одного узла за вызов и terminal outcomes;
- пауза на `needs_input`, проверка `wait_id`/`node_id` и продолжение через `resume`;
- блокировка, явное продолжение через `resume_blocked` и отмена;
- структурированные contract/execution ошибки;
- глубокая изоляция входов, snapshots и результатов;
- Graph/Node/Artifact contract validation.

Предметное покрытие находится в [tests/test_workflow_runtime.py (исторический файл; миграция)](../guides/workflow-runtime.md), пользовательское описание — в [гайде](../guides/workflow-runtime.md).

## Документация

Добавлен русский guide запуска runtime с минимальным примером, описанием pause/resume и границами интеграции. Актуализированы `docs/README.md`, `docs/project-status.md`, `docs/roadmap.md`, onboarding guide, архитектура хранения, Task Manager boundary и Workflow Run navigation. Убраны устаревшие утверждения о том, что Graph Runtime ещё не реализован.

## Граница Task Manager

Runtime хранит состояние текущего запуска в памяти и не пишет SQLite. Task Manager остаётся владельцем lifecycle задачи; интеграционный адаптер должен использовать только публичный API, актуальную `expected_version` и хранить в задаче только ссылки на запуск. Автоматическое связывание, Executor Loop, Artifact Repository, checkpoints и восстановление между сессиями не входят в TASK-0004.

## Проверки

- корневой Orchestrator: **15/15**;
- Task Manager: **73/73**;
- Onboarding: **19**, из них 18 прошли и 1 ожидаемо пропущен из-за Windows symlink;
- `compileall -q orchestrator tests`: успешно;
- `git diff --check`: успешно, только стандартные предупреждения LF/CRLF;
- `orchestrator-tasks --project . validate`: `ok: true`;
- markdown-ссылки на добавленный guide/report проверены по существованию файлов и `git diff --check`.
