# TASK-0033 — Configurable KnowledgeRefreshNode v1

**Статус:** реализация завершена и принята пользователем; TASK-0033 находится в `completed v30`. TASK-0020 не изменялась.

## Реализовано

- Добавлен `KnowledgeRefreshPolicy` с режимами `auto`, `incremental`, `full` и authorization `required`/`automatic`.
- Добавлен reusable `KnowledgeRefreshNode` с контрактом `knowledge-refresh-node/v1` и graph definition для всех исходов: `not_required`, `success`, `degraded`, `stale`, `failed`, `fallback_required`, `awaiting_confirmation`.
- `authorization=required` для full создаёт Graph Runtime `WaitState`; trusted `authorization=automatic` допускает full только в явной конфигурации конкретной ноды.
- `auto`/`incremental` вызывают `refresh_incremental(allow_full_fallback=False)`. При отсутствии безопасного baseline возвращается `fallback_required`; full автоматически не запускается.
- `AgentExecution.precommit_gate()` сохранён как совместимый wrapper над node и принимает optional request/decision.
- Старый `refresh_incremental()` по умолчанию сохраняет TASK-0020 compatibility с диагностируемым legacy full fallback.

## Границы

Task Manager, SQLite, Graphify provider ownership, semantic backends, Git hooks и Project Knowledge Graph topology не менялись. Full refresh не запускается молча. Физический Git commit выполняет внешний агент только при `commit_allowed=true`.

## Проверки

- Root suite: 164 теста, 162 passed, 2 Windows skip.
- KnowledgeRefreshNode/Knowledge Service/AgentExecution targeted suite: 69 тестов, 68 passed, 1 Windows skip.
- `compileall -q orchestrator` и `git diff --check` выполняются после финальной документации.

## Acceptance

Candidate revision и acceptance package прикреплены через публичный Task Manager API. Пользовательская приёмка зарегистрирована атомарным `accept_task` для текущей candidate revision; активных claim/run нет, `health_check=[]`.

Решение приёмки: `user-acceptance/TASK-0033/2026-09-18`.
