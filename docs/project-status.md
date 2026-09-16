# Текущее состояние Orchestrator

**Статус:** действующий снимок фактически реализованного состояния для агента.

**Дата:** 2026-09-16.

Этот документ обновляется после каждого завершённого этапа. Он фиксирует только подтверждённые кодом, тестами и командами возможности; планы остаются в `docs/plans/`, порядок работ — в `docs/roadmap.md`, история изменений — в `docs/worklog.md`.

## Репозиторий

- Активный проект называется `Orchestrator`.
- Старый продукт, релизы и старое состояние находятся в `obsolete/` как неизменяемый справочный архив.
- Новый графовый подход и действующие контракты находятся в `docs/`.
- Полного графового runtime пока нет.

## Пакет Onboarding

Каталог: `packages/onboarding/`. Дистрибутив `orchestrator-onboarding`, импорт `orchestrator_onboarding`, команда `orchestrator-onboarding`.

Онбординг поддерживает безопасные `preview`/`apply` для внешнего проекта и self-hosting. Self-hosting текущего репозитория проверен 2026-09-15: созданы `.orchestrator/project.json` и `.orchestrator/project-context.md`, повторный preview показал 0 изменений. План содержит точный diff и SHA-256; `apply` требует подтверждённый хеш, повторно проверяет состояние, защищает пользовательские файлы и восстанавливает записанные файлы при обычной ошибке. Проверяются пути, UTF-8, символические ссылки, конфликты и наличие Task Manager skill в подключённом ядре. Прямой запуск исходного файла сохранён.

Онбординг создаёт `.orchestrator/project.json`, `.orchestrator/project-context.md`, управляемый блок `AGENTS.md` и правило `.orchestrator/state/` в `.gitignore`. Одноразовая инструкция первого запуска уже реализована и ведёт агента через полный стартовый сценарий: осмотр проекта, вопросы, preview/apply с подтверждением хеша, отдельное подтверждение установки Task Manager и финальную проверку. После завершения постоянным проектным skill остаётся только Task Manager; пакет не устанавливает зависимости молча и не запускает граф.

Подробнее: [контракт](architecture/onboarding.md), [гайд](guides/onboarding.md), [README пакета](../packages/onboarding/README.md).

## Task Manager Service

Каталог: `packages/task-manager/`. Дистрибутив `orchestrator-task-manager`, импорт `orchestrator_task_manager`; внешних зависимостей нет, ядро Orchestrator не импортируется. Для текущего self-hosted проекта пакет установлен в `.venv` в editable-режиме и проверен через CLI.

Каноническое состояние — `.orchestrator/state/tasks.sqlite3`. SQLite хранит снимок задачи, события, операции идемпотентности, tombstone удалённых задач и счётчик ID; схема развивается через встроенный реестр миграций с текущей версией `5`. Каждая мутация требует `expected_version`, выполняется транзакционно и создаёт событие; повторяемые операции принимают `operation_id`, события содержат контекст происхождения.

Поддерживаются создание, чтение, SQL-фильтрация и cursor-поиск, история, экспорт JSON, backup/restore SQLite, обратимая архивация, retention в три календарных месяца и физическое удаление с tombstone, типы задач `implementation`, `analysis`, `investigation`, `incident`, `exploration`, статусы подготовки/исполнения/ожидания/блокировки, plan и SHA-256 guard перед `ready`, claim/lease, блокеры, решения пользователя, ссылки на запуски, приёмка, завершение, отмена и усиленная read-only диагностика `validate`. Каноническое определение задачи находится в карточке Task Manager; отдельная specification не обязательна.

CLI:

```powershell
orchestrator-tasks --project . create ...
orchestrator-tasks --project . list
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks resources
```

Панель запускается `orchestrator-tasks-web --project . --port 8765`, слушает только `127.0.0.1` и работает только на чтение.

В пакет входят полный [контракт](../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md), [гайд](../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) и [пример skill](../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md). Проектный skill `.agents/skills/orchestrator-task-manager/SKILL.md` указывает на этот пример.

## Правила для агента


- Источник истины о задаче — публичный Task Manager API, не Git и не SQLite напрямую.
- Перед мутацией перечитай задачу и передай текущую `version` как `expected_version`.
- При конфликте версии перечитай задачу; не повторяй изменение вслепую.
- `ready` требует каноническую карточку задачи, актуальный `plan.md`, review, Execution Package и отсутствия блокеров; отдельная specification не обязательна. `active` достигается только через claim.
- Состояние запуска принадлежит Graph Runtime; Task Manager хранит только ссылки.
- После мутации проверь карточку, историю и при необходимости `validate`.

## Пока отсутствует

Подтверждена упрощённая архитектура [Workflow Run](architecture/workflow-run.md): один агент работает в реальном времени, runtime хранит текущий процесс в памяти, [вопрос пользователю](architecture/workflow-pause-resume.md) приостанавливает граф в той же сессии. Возможность поддержки нескольких сессий, контрольных точек и автоматического восстановления описана отдельно как [будущая функция](architecture/runtime-coordination.md) и сейчас не реализуется. Существующий task-claim остаётся требованием `ready → active`, а переход от устаревшего ожидания исполнения к подготовке ещё требует согласования API.

Первый срез согласования границы хранения завершён: [состояние и хранение](architecture/state-and-storage.md). Устаревшие файловые модели отмечены в исходных материалах. Кандидат минимальных контрактов Graph, Node, Artifact, WorkflowRun и API runtime подготовлен в [контракте Graph Runtime v1](architecture/graph-runtime-contract.md) и ожидает пользовательской приёмки в TASK-0002; это пока не реализованная возможность.

Graph Runtime, Executor Loop, Artifact Repository, полноценные графовые переходы и синхронизация с внешними трекерами. Реализован только первый входной срез Request Router → Task Creator; полного устанавливаемого пакета всего ядра также пока нет. Последовательный backlog TASK-0002–TASK-0022 и его зависимости описаны в [backlog развития v1](plans/2026-09-16-orchestrator-roadmap-backlog-design.md); задачи TASK-0002–TASK-0004 и TASK-0014–TASK-0022 имеют статус `created`, при этом TASK-0018 помечена как будущая необязательная интеграция и не блокирует локальный v1.

## Проверки

```powershell
python -m unittest discover -s packages/onboarding/tests -v
python -m unittest discover -s packages/task-manager/tests -v
```

Последний результат: корневой Orchestrator — 5 тестов; Onboarding — 15 тестов, 14 прошли и 1 пропущен из-за ограничения Windows на symlink; Task Manager — 31 тест прошёл. `orchestrator-tasks --project . validate` вернул `ok: true`. Оба пакета собираются в отдельные wheel; Task Manager проверен изолированно без ядра.
