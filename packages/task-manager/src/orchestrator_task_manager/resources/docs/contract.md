# Task Manager Service: действующий контракт

**Статус:** реализованный первый срез, 2026-09-15. Этот документ поставляется внутри пакета `orchestrator-task-manager` и не требует документов ядра Orchestrator.

## Ответственность и данные

`TaskManagerService` — детерминированный владелец состояния задачи. Он не анализирует требования, не выбирает узел графа, не выполняет код и не редактирует проект. Состояние запуска принадлежит внешнему Graph Runtime; задача содержит лишь `run_ref`. Внешний трекер может быть проекцией, но не источником истины.

Каноническое состояние хранится в `<project_root>/.orchestrator/state/tasks.sqlite3`. Эта база локальна и не должна попадать в Git. Создание проекта или онбординг для работы сервиса не обязательны: нужен существующий каталог `project_root`. План реализации размещается в `.orchestrator/tasks/TASK-xxxx/plan.md`. Сервис не создаёт этот файл, но при привязке и переходе в `ready` проверяет его путь и SHA-256. Старые `specification.md` могут оставаться в исторических карточках, но не являются обязательным артефактом.

SQLite хранит снимки в `tasks`, события в `events`, операции идемпотентности в `operations`, tombstone удалённых задач в `purged_tasks` и счётчик ID в `meta`; текущая версия схемы — `PRAGMA user_version=5`. События также содержат nullable-метаданные `actor_ref`, `source`, `correlation_id`, `run_ref`. Схема создаётся через упорядоченный реестр миграций; будущие версии добавляются отдельными переходами, а неподдерживаемая версия отклоняется до записи. ID имеет вид `TASK-0001`, версия задачи начинается с 1. Каждая мутация требует `expected_version` и в одной транзакции `BEGIN IMMEDIATE` обновляет снимок и добавляет одно событие. Необязательный `operation_id` возвращает сохранённый результат повторной операции без нового события; другой отпечаток с тем же ID даёт `operation_conflict`. При конфликте версии возвращается `TaskError(code="task_version_conflict", details={"expected": ..., "actual": ...})`; автоматического слияния нет. Исходный запрос в снимке не изменяется. Прямые SQL-записи не входят в публичный API.

Снимок содержит название, тип, исходный запрос, цель, критерии приёмки, ограничения, версию определения, статус, ссылки на артефакты и запуски, lease, блокеры, решения пользователя, внешние ссылки и временные метки. Поддерживаемые типы: `implementation`, `analysis`, `investigation`, `incident`, `exploration`. История чата и содержимое документов в снимок не копируются.

## Статусы и защитные условия

Основной путь: `created → preparing → ready → active → awaiting_acceptance → completed`. Дополнительные статусы: `awaiting_input`, `blocked`, `cancelled`; `completed` и `cancelled` конечны. Подготовка начинается с `run_ref`; перед `ready` активная ссылка на запуск должна быть закрыта. Для `ready` нужны карточка задачи, одобренный `plan`, `plan_review` и `execution_package`, привязанные к одной версии плана, подготовленная ревизия источника и отсутствие открытых блокирующих факторов. Изменение определения или плана после `ready` аннулирует пакет и возвращает задачу к подготовке.

`ready → active` возможен только через атомарный `claim_task` с lease. Продление, освобождение и восстановление истёкшего claim сохраняются в истории. При активной ссылке на запуск автоматическое восстановление claim запрещено. Состояния ожидания пользователя и блокировки не снимаются простым освобождением claim; для возобновления нужны решение или разрешение блокера и повторная проверка готовности.

Архивация доступна только для `completed` и `cancelled`, не меняет их status и скрывает задачу из обычного списка. `unarchive_task` обратимо снимает архивный признак. `purge_task` физически удаляет snapshot и события только для архивированной задачи со статусом `cancelled` после трёх календарных месяцев с terminal-события; операция сохраняет минимальный tombstone и не освобождает ID для повторного использования.

Переход к `awaiting_acceptance` требует артефакт `readiness` с `metadata.status="ready"`, `acceptance_package` и закрытый запуск. Завершение по умолчанию требует решение пользователя `acceptance=approved` для текущей `candidate_revision` и отсутствие открытых блокеров. Сервис проверяет факт регистрации свидетельств, но не делает вывод о качестве реализации. Отключение обязательной пользовательской приёмки доступно только явным параметром `acceptance_required=False` при создании сервиса.

## Публичный API

Импорт: `from orchestrator_task_manager import TaskManagerService, TaskError`. Конструктор принимает `Path` корня проекта и необязательные `clock`, `acceptance_required`. Возвращаемые задачи и события — словари Python; их изменяемость в памяти не заменяет вызов сервисного метода.

| Группа | Методы |
| --- | --- |
| Создание и чтение | `create_task`, `get_task`, `list_tasks`, `get_history`, `get_document`, `get_claim`, `list_executable_tasks`, `health_check` |
| Хранение | `archive_task`, `unarchive_task`, `purge_task` |
| Перенос состояния | `export_state`, `backup`, `restore` |
| Подготовка | `start_preparation`, `refine_task_definition`, `update_metadata`, `attach_artifact`, `attach_execution_package`, `mark_ready` |
| Исполнение и пауза | `claim_task`, `renew_claim`, `release_claim`, `recover_expired_claim`, `link_workflow_run`, `add_blocker`, `resolve_blocker`, `transition_status` |
| Приёмка и интеграции | `record_user_decision`, `mark_awaiting_acceptance`, `complete_task`, `cancel_task`, `register_external_link` |

`create_task` требует `title`, `task_type`, `objective`, `original_request`, непустой список `acceptance_criteria`; ключевые мутации принимают `operation_id` и `event_context`. Для остальных мутаций первым аргументам после `self` обычно соответствуют `task_id` и текущая `expected_version`; дополнительные именованные параметры смотрите в сигнатуре метода. Роли артефактов ограничены набором в `task_manager.py`; для `plan` нужен путь внутри каталога задачи и SHA-256. `get_document` сохраняет чтение `plan` и legacy `specification` с повторной проверкой хеша. `list_tasks` по умолчанию скрывает архив, а `include_archived=True` возвращает его; фильтры и cursor-пагинация сохраняются. `health_check` выполняет диагностику, но ничего не исправляет. `export_state` включает архивные задачи и tombstone удалённых, `backup` — консистентную копию SQLite, а `restore` проверяет копию до атомарной замены и сохраняет `.pre-restore`.

Исключение `TaskError` содержит `code`, сообщение и `details`; `as_dict()` готовит машинный ответ. Основные коды: `validation_failed`, `task_not_found`, `task_purged`, `invalid_transition`, `guard_failed`, `retention_not_elapsed`, `task_not_ready`, `task_version_conflict`, `operation_conflict`, `claim_conflict`, `claim_expired`, `repository_failure`. После конфликта версии заново прочитайте задачу и решите, применимо ли исходное намерение; не повторяйте мутацию автоматически.

## Пределы среза

Пакет не включает Task Creator, Artifact Repository, Graph Runtime, Executor Loop и синхронизацию с внешним трекером. Версионируемый реестр миграций схемы SQLite, операции backup/export/restore и retention-политика архивации входят в текущий срез. CLI предоставляет lifecycle хранения, создание, чтение и перенос состояния, а не все защищённые переходы. Конкурентный claim защищён транзакцией, но восстановление внешней работы после аварии требует отдельной интеграционной проверки. Практические команды и пример Python API — в [инструкции](usage.md).
