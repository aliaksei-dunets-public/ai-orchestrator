# Текущее состояние Orchestrator

**Статус:** действующий снимок фактически реализованного состояния для агента.

**Дата:** 2026-09-17.

Этот документ обновляется после каждого завершённого этапа. Он фиксирует только подтверждённые кодом, тестами и командами возможности; планы остаются в `docs/plans/`, порядок работ — в `docs/roadmap.md`, история изменений — в `docs/worklog.md`.

## Репозиторий

- Активный проект называется `Orchestrator`.
- Старый продукт, релизы и старое состояние находятся в `obsolete/` как неизменяемый справочный архив.
- Новый графовый подход и действующие контракты находятся в `docs/`.
- Полного графового runtime пока нет.

## Пакет Onboarding

Каталог: `packages/onboarding/`. Дистрибутив `orchestrator-onboarding`, импорт `orchestrator_onboarding`, команда `orchestrator-onboarding`.

Онбординг поддерживает безопасные `preview`/`apply` для внешнего проекта и self-hosting. Self-hosting текущего репозитория проверен 2026-09-15: созданы `.orchestrator/project.json` и `.orchestrator/project-context.md`, повторный preview показал 0 изменений. План содержит точный diff и SHA-256; `apply` требует подтверждённый хеш, повторно проверяет состояние, защищает пользовательские файлы и восстанавливает записанные файлы при обычной ошибке. Проверяются пути, UTF-8, символические ссылки, конфликты и наличие Task Manager skill в подключённом ядре. Прямой запуск исходного файла сохранён.

Онбординг создаёт `.orchestrator/project.json`, `.orchestrator/project-context.md`, управляемый блок `AGENTS.md` и правило `.orchestrator/state/` в `.gitignore`. Одноразовая инструкция первого запуска уже реализована и ведёт агента через полный стартовый сценарий: осмотр проекта, вопросы, preview/apply с подтверждением хеша, отдельное подтверждение установки Task Manager и финальную проверку. Для установленного Task Manager добавлены явные `check-task-manager` (реальный MCP handshake и read-only health check) и `mcp-config` (локальный host-neutral конфиг с выбранным Python, без записи глобальных настроек). После завершения постоянным проектным skill остаётся Task Manager; пакет не устанавливает зависимости молча и не запускает граф.

Подробнее: [контракт](architecture/onboarding.md), [гайд](guides/onboarding.md), [README пакета](../packages/onboarding/README.md).

## Task Manager Service

Каталог: `packages/task-manager/`. Дистрибутив `orchestrator-task-manager`, импорт `orchestrator_task_manager`; внешних зависимостей нет, ядро Orchestrator не импортируется. Для текущего self-hosted проекта пакет установлен в `.venv` в editable-режиме и проверен через CLI.

Каноническое состояние — `.orchestrator/state/tasks.sqlite3`. SQLite хранит снимок задачи, события, операции идемпотентности, tombstone удалённых задач и счётчик ID; схема развивается через встроенный реестр миграций с текущей версией `5`. Каждая мутация требует `expected_version`, выполняется транзакционно и создаёт событие; повторяемые операции принимают `operation_id`, события содержат контекст происхождения.

Поддерживаются создание, чтение, SQL-фильтрация и cursor-поиск, история, экспорт JSON, backup/restore SQLite, обратимая архивация, retention в три календарных месяца и физическое удаление с tombstone, типы задач `implementation`, `analysis`, `investigation`, `incident`, `exploration`, статусы подготовки/исполнения/ожидания/блокировки, plan и SHA-256 guard перед `ready`, claim/lease, блокеры, решения пользователя, ссылки на запуски, приёмка, завершение, отмена и усиленная read-only диагностика `validate`. Каноническое определение задачи находится в карточке Task Manager; отдельная specification не обязательна.

Дополнительный срез TASK-0023 реализует атомарный `accept_task`, SQL `summary`, структурный фильтр архива до LIMIT, единый транзакционный снимок export/validate, UTC для injected clock и файловые ошибки TaskError. SHA-256 потоковый; чтение документа проверяет именно возвращаемые байты. Restore мигрирует временную копию и создаёт консистентную safety copy, требует остановки других процессов/мутаций. Измерения и границы нагрузки опубликованы в [отчёте](reports/2026-09-16-task-manager-hardening.md).

TASK-0024 разделяет реализацию на contracts, migrations, repository, service, storage_transfer и diagnostics; task_manager сохраняет прежние импорты. Сервис не выполняет SQL и не вызывает приватные методы репозитория. Экспорт и диагностика используют read-only транзакцию, схема остаётся версии 5. [Архитектура пакета](../packages/task-manager/src/orchestrator_task_manager/resources/docs/architecture.md) входит в wheel; [отчёт разделения](reports/2026-09-17-task-manager-modularization.md) содержит проверки совместимости и парные замеры.

CLI:

```powershell
orchestrator-tasks --project . create ...
orchestrator-tasks --project . list
orchestrator-tasks --project . summary
orchestrator-tasks --project . list --format table
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks resources
orchestrator-tasks api
```

Панель запускается `orchestrator-tasks-web --project . --port 8765`, слушает только `127.0.0.1` и работает только на чтение.

CLI покрывает защищённые операции подготовки/исполнения, blocker/decision и приёмку. JSON по умолчанию и коды выхода сохранены; ошибки разбора аргументов также JSON. `--expected-version` фиксирует прочитанную версию, без флага CLI читает текущую. Для повтора с operation-id требуется первоначальная версия. Таблица поддерживается для list/show/summary; `api` показывает сигнатуры, не создавая базу.

В пакет входят полный [контракт](../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md), [гайд](../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) и [пример skill](../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md). Проектный skill `.agents/skills/orchestrator-task-manager/SKILL.md` указывает на этот пример. Skill выбирает MCP stdio для внешнего агента, прямой `TaskManagerService` для in-process Python-оркестратора и CLI как fallback.

## Правила для агента

TASK-0025 исправляет обнаруженную аудитом ошибку CLI export: общий реестр переноса сопоставляет export с export_state. Экспорт, JSON-ошибки назначения и CLI backup/restore покрыты новыми регрессиями; [отчёт исправления](reports/2026-09-17-task-manager-cli-export-fix.md). Публичная карточка TASK-0025 завершена с пользовательской приёмкой. TASK-0026 реализует MCP stdio-адаптер: один общий пакет, отдельный экземпляр на проект, фиксированный root, 35 структурированных инструментов и ограничение файловых путей. Полный сценарный аудит исправил schema validation, lifecycle JSON-RPC, формат structuredContent, direct API validation, operation fingerprint и blocker diagnostics. TASK-0026 завершена с явной пользовательской приёмкой; [дизайн](plans/2026-09-17-task-manager-mcp-adapter-design.md), [исходный отчёт](reports/2026-09-17-task-manager-mcp-adapter.md), [интеграционный отчёт](reports/2026-09-17-task-manager-onboarding-mcp-hardening.md), [полный аудит и исправления](reports/2026-09-17-task-manager-full-audit-fixes.md).


- Источник истины о задаче — публичный Task Manager API, не Git и не SQLite напрямую.
- Перед мутацией перечитай задачу и передай текущую `version` как `expected_version`.
- При конфликте версии перечитай задачу; не повторяй изменение вслепую.
- `ready` требует каноническую карточку задачи, актуальный `plan.md`, review, Execution Package и отсутствия блокеров; отдельная specification не обязательна. `active` достигается только через claim.
- Состояние запуска принадлежит Graph Runtime; Task Manager хранит только ссылки.
- После мутации проверь карточку, историю и при необходимости `validate`.

## Пока отсутствует

Подтверждена упрощённая архитектура [Workflow Run](architecture/workflow-run.md): `GraphRuntime` выполняет один узел за шаг, хранит текущий процесс в памяти, атомарно публикует валидные результаты, через `WaitState` приостанавливает граф на вопросе пользователю и позволяет явно повторить заблокированный узел через `resume_blocked`. TASK-0003 принята и завершена по публичной карточке Task Manager (version 22). Возможность поддержки нескольких сессий, контрольных точек и автоматического восстановления описана отдельно как [будущая функция](architecture/runtime-coordination.md) и сейчас не реализуется. Существующий task-claim остаётся требованием `ready → active`, а интеграционный адаптер Task Manager ещё требует отдельного этапа.

Первый срез согласования границы хранения завершён: [состояние и хранение](architecture/state-and-storage.md). Устаревшие файловые модели отмечены в исходных материалах. Действующие контракты Graph, Node, Artifact, WorkflowRun и API runtime закреплены в [контракте Graph Runtime v1](architecture/graph-runtime-contract.md), core реализация находится в `orchestrator.workflow_runtime`; после независимого аудита TASK-0003 исправлена и завершена, а TASK-0004 продолжает интеграционную проверку и подготовку полного пользовательского гайда.

Executor Loop, Artifact Repository, полноценная интеграция графа с Task Manager и синхронизация с внешними трекерами пока отсутствуют. Реализованы core in-memory Graph Runtime и первый входной срез Request Router → Task Creator; полного устанавливаемого пакета всего ядра также пока нет. Последовательный backlog TASK-0002–TASK-0022 и его зависимости описаны в [backlog развития v1](plans/2026-09-16-orchestrator-roadmap-backlog-design.md); TASK-0002 завершена, TASK-0003 подготовлена и находится в `awaiting_acceptance`, TASK-0004 и TASK-0014–TASK-0022 имеют статус `created`, при этом TASK-0018 помечена как будущая необязательная интеграция и не блокирует локальный v1. TASK-0023 завершена по публичной карточке (version 18, отдельное событие приёмки); TASK-0024 — согласованное внутреннее разделение пакета, awaiting_acceptance без пользовательской приёмки.

## Проверки

```powershell
python -m unittest discover -s packages/onboarding/tests -v
python -m unittest discover -s packages/task-manager/tests -v
```

Последний результат: корневой Orchestrator — 15 тестов, включая 10 сценариев Graph Runtime; Onboarding — 19 тестов, 18 прошли и 1 пропущен из-за ограничения Windows на symlink; Task Manager — 73 теста прошли. `orchestrator-tasks --project . validate` должен возвращать `ok: true`; последний live validate после исправлений TASK-0003 успешен. MCP benchmark: p50 0.350 ms, p95 0.551 ms; startup initialize — 124.702 ms. Подробности runtime — в отчёте TASK-0003.
