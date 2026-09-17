# TASK-0026: MCP stdio-адаптер Task Manager

**Статус:** реализация первого среза завершена; TASK-0026 ожидает пользовательской приёмки.

## Что реализовано

- Добавлен модуль `orchestrator_task_manager.task_mcp` и команда `orchestrator-task-manager-mcp --project <root>`.
- Реализован построчный UTF-8 JSON-RPC stdio lifecycle: `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`.
- Адаптер публикует 35 структурированных инструментов: чтение, создание, подготовка, claim/lease, блокеры, решения, приёмка, завершение, архивация, export/backup/restore и диагностика.
- Все вызовы делегируются публичному `TaskManagerService`; прямого SQL, отдельного хранилища и копии guards нет.
- `expected_version` обязателен для мутаций; `operation_id` доступен только поддерживаемым API-методам; конфликт версии не повторяется автоматически.
- `TaskError` возвращается как `structuredContent.error` с `isError: true`; неожиданный сбой не закрывает stdio-сессию.
- `project_root` фиксируется при запуске. Пути MCP export/backup/restore после `resolve` обязаны оставаться внутри этого корня.
- Существующий CLI и Python API не изменены по контракту; внешних зависимостей не добавлено.

## Архитектурное решение

Один пакет кода используется всеми проектами, но MCP-клиент запускает отдельный процесс на каждый проект. Каждый процесс работает только с собственной `.orchestrator/state/tasks.sqlite3`. Общий мульти-проектный daemon, HTTP, кэш и пакетные мутации в первый срез не входят.

Подробная схема и подключение: [архитектурный план](../plans/2026-09-17-task-manager-mcp-adapter-design.md). Инструкция пользователя поставляется вместе с wheel в [usage.md](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md).

## Проверки

- `python -m unittest discover -s packages/task-manager/tests -v`: 65/65.
- `python -m unittest discover -s tests -v`: 5/5.
- MCP subprocess-тесты проверяют initialize/catalog, полный lifecycle create → preparation → ready → claim → acceptance → completed → archive, структурированные ошибки, stale version, Unicode, restart, два project root и запрет выхода файлового пути.
- Wheel изолирован с Python `-S` без ядра: `WHEEL_MCP_ISOLATION_OK`.
- Финальный wheel `orchestrator_task_manager-0.1.0-py3-none-any.whl`, SHA-256: `61207d40469b648462696b704ff25727a27a6fa8c9a1a6cb6bad5a80e7884405`.
- Команда после editable install: `orchestrator-task-manager-mcp --help` успешна.
- `orchestrator-tasks --project . validate`: `ok: true`, нарушений нет.
- `git diff --check`: ошибок whitespace нет; остаются только предупреждения Git о нормализации LF/CRLF.

Benchmark на временном проекте, 100 последовательных тёплых вызовов `task_get`:

| Измерение | Результат |
| --- | ---: |
| initialize startup | 124.702 ms |
| `task_get` p50 | 0.350 ms |
| `task_get` p95 | 0.551 ms |

Значения относятся к текущему Windows-окружению и не являются обещанием задержки любого MCP-хоста или полного агентского сценария.

## Ограничения перед приёмкой

Проверен протокольный subprocess-клиент, а не конкретный GUI-хост Codex. Нужна отдельная проверка подключения в целевом MCP-клиенте и пользовательская приёмка TASK-0026. CLI остаётся fallback.
