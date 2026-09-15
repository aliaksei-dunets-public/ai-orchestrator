# Текущее состояние Orchestrator

**Статус:** действующий снимок фактически реализованного состояния для агента.

**Дата:** 2026-09-15.

Этот документ обновляется после каждого завершённого этапа. Он фиксирует только подтверждённые кодом, тестами и командами возможности; планы остаются в `docs/plans/`, порядок работ — в `docs/roadmap.md`, история изменений — в `docs/worklog.md`.

## Репозиторий

- Активный проект называется `Orchestrator`.
- Старый продукт, релизы и старое состояние находятся в `obsolete/` как неизменяемый справочный архив.
- Новый графовый подход и действующие контракты находятся в `docs/`.
- Полного графового runtime пока нет.

## Пакет Onboarding

Каталог: `packages/onboarding/`. Дистрибутив `orchestrator-onboarding`, импорт `orchestrator_onboarding`, команда `orchestrator-onboarding`.

Онбординг поддерживает безопасные `preview`/`apply` для внешнего проекта и self-hosting. План содержит точный diff и SHA-256; `apply` требует подтверждённый хеш, повторно проверяет состояние, защищает пользовательские файлы и восстанавливает записанные файлы при обычной ошибке. Проверяются пути, UTF-8, символические ссылки, конфликты и наличие Task Manager skill в подключённом ядре. Прямой запуск исходного файла сохранён.

Онбординг создаёт `.orchestrator/project.json`, `.orchestrator/project-context.md`, управляемый блок `AGENTS.md` и правило `.orchestrator/state/` в `.gitignore`. Он не устанавливает Task Manager и не запускает граф.

Подробнее: [контракт](architecture/onboarding.md), [гайд](guides/onboarding.md), [README пакета](../packages/onboarding/README.md).

## Task Manager Service

Каталог: `packages/task-manager/`. Дистрибутив `orchestrator-task-manager`, импорт `orchestrator_task_manager`; внешних зависимостей нет, ядро Orchestrator не импортируется.

Каноническое состояние — `.orchestrator/state/tasks.sqlite3`. SQLite хранит снимок задачи, события, версии и счётчик ID. Каждая мутация требует `expected_version`, выполняется транзакционно и создаёт событие.

Поддерживаются создание, чтение, поиск, история, типы задач `implementation`, `analysis`, `investigation`, `incident`, `exploration`, статусы подготовки/исполнения/ожидания/блокировки, артефакты и SHA-256 guard перед `ready`, claim/lease, блокеры, решения пользователя, ссылки на запуски, приёмка, завершение, отмена и диагностика `validate`.

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
- `ready` требует актуальных документов, review, Execution Package и отсутствия блокеров; `active` достигается только через claim.
- Состояние запуска принадлежит Graph Runtime; Task Manager хранит только ссылки.
- После мутации проверь карточку, историю и при необходимости `validate`.

## Пока отсутствует

Подтверждена упрощённая архитектура [Workflow Run](architecture/workflow-run.md): один агент работает в реальном времени, runtime хранит текущий процесс в памяти, [вопрос пользователю](architecture/workflow-pause-resume.md) приостанавливает граф в той же сессии. Возможность поддержки нескольких сессий, контрольных точек и автоматического восстановления описана отдельно как [будущая функция](architecture/runtime-coordination.md) и сейчас не реализуется. Код Task Manager не менялся; существующий task-claim остаётся требованием `ready → active`, а переход от устаревшего ожидания исполнения к подготовке ещё требует согласования API.

Первый срез согласования контрактов завершён: [состояние и хранение](architecture/state-and-storage.md). Устаревшие файловые модели отмечены в исходных материалах. Это архитектурное решение, а не новая реализованная возможность. Минимальные схемы графа, узла, артефакта и точный API runtime ещё предстоит определить.

Graph Runtime, Executor Loop, Artifact Repository, полноценные графовые переходы, миграции SQLite, backup/export, восстановление и синхронизация с внешними трекерами. Реализован только первый входной срез Request Router → Task Creator; полного устанавливаемого пакета всего ядра также пока нет.

## Проверки

```powershell
python -m unittest discover -s packages/onboarding/tests -v
python -m unittest discover -s packages/task-manager/tests -v
```

Последний результат: Onboarding — 12 тестов, 11 прошли и 1 пропущен из-за ограничения Windows на symlink; Task Manager — 18 тестов прошли. Оба пакета собираются в отдельные wheel; Task Manager проверен изолированно без ядра.
