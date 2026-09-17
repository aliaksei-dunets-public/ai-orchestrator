# Использование Task Manager Service

**Статус:** инструкция к реализованному первому срезу. Нужна Python 3.11+; внешних зависимостей у пакета нет.

## Установка и расположение ресурсов

Установите пакет из каталога `packages/task-manager/` командой `python -m pip install .` или `python -m pip install -e .` для разработки. После установки исходный репозиторий не нужен. `orchestrator-tasks resources` возвращает пути к этому гайду, [контракту](contract.md) и [примеру skill](../examples/skills/orchestrator-task-manager/SKILL.md) внутри установленного пакета. Если хотите использовать пример как проектный Codex skill, скопируйте весь каталог `orchestrator-task-manager/` в `.agents/skills/` целевого проекта; не изменяйте чужие файлы в этом каталоге.

Всегда указывайте корень целевого проекта через `--project`, если команда запускается не из него. База создаётся в `<проект>/.orchestrator/state/tasks.sqlite3`; исключите `.orchestrator/state/` из Git. План реализации, если нужен, версионируется в `.orchestrator/tasks/TASK-xxxx/plan.md`; отдельная specification не требуется.

## CLI и панель

```powershell
orchestrator-tasks --project . create --title "Проверить расчёт" --type implementation --objective "Исправить X" --request "Исправь расчёт X" --criterion "X даёт ожидаемый результат"
orchestrator-tasks --project . list --status created
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks --project . export .orchestrator/state/tasks.json
orchestrator-tasks --project . backup .orchestrator/state/tasks.sqlite3.backup
orchestrator-tasks --project . restore .orchestrator/state/tasks.sqlite3.backup
orchestrator-tasks --project . archive TASK-0001 --reason "Завершено"
orchestrator-tasks --project . list --include-archived
orchestrator-tasks --project . purge TASK-0001 --reason "Retention истёк"
orchestrator-tasks resources
orchestrator-tasks-web --project . --port 8765
```

CLI возвращает JSON `{"ok": true, "result": ...}`. Ошибки, включая неправильные аргументы, выводятся JSON на stderr. Коды выхода: 0 — успех, 1 — validate обнаружил нарушения, 2 — ошибка вызова. Для `list` доступны повторяемый `--status`, а также `--type`, `--query`, `--limit` (1..500), `--cursor` и `--include-archived`; `history` поддерживает `--after-sequence`. Для следующей страницы передайте ID последней задачи предыдущей страницы как cursor. Архив фильтруется до LIMIT. Созданная задача остаётся в `created`: подготовка и выполнение автоматически не запускаются.

```powershell
orchestrator-tasks --project . list --format table
orchestrator-tasks summary --project . --format table
orchestrator-tasks --project . summary --status ready
orchestrator-tasks --project . summary --include-archived
orchestrator-tasks --project . show TASK-0001 --format table
orchestrator-tasks api
orchestrator-tasks claim --help
```

JSON сохраняет все поля и предназначен для агента. Table — компактное представление list/show/summary для человека; остальные команды сохраняют JSON. `--project` и `--format` работают до и после команды. `summary.total`, `by_status` и `by_type` учитывают выбранные фильтры и по умолчанию исключают архив; tombstone не входит в total. `archived_total` и `purged_total` показывают глобальные счётчики проекта. `api` возвращает актуальные сигнатуры всех публичных методов без создания базы; параметры CLI доступны в `--help`.

## MCP stdio для агента

Установленный пакет предоставляет команду `orchestrator-task-manager-mcp`. MCP-клиент запускает её как subprocess и обменивается построчными UTF-8 JSON-RPC сообщениями через stdio. Перед обычными вызовами клиент выполняет `initialize`, получает ответ и затем отправляет `notifications/initialized`. До этого уведомления инструменты недоступны; уведомления без `id` не исполняют операции. Сервер публикует инструменты через `tools/list`, вызовы выполняются через `tools/call`.

Запускайте отдельный экземпляр на каждый проект:

```powershell
orchestrator-task-manager-mcp --project C:\Projects\project-a
orchestrator-task-manager-mcp --project C:\Projects\project-b
```

Пакет и код адаптера общие, но каждый процесс получает фиксированный `project_root` и работает только с его `.orchestrator/state/tasks.sqlite3`. Не передавайте другой корень в аргументах инструмента. Пути `source`/`destination` для export, backup и restore также обязаны находиться внутри этого корня; выход за него возвращает `validation_failed`. Логически конфигурация MCP-клиента для одного проекта содержит команду и аргумент проекта:

```json
{
  "task-manager-project-a": {
    "command": "orchestrator-task-manager-mcp",
    "args": ["--project", "C:/Projects/project-a"]
  }
}
```

Доступны структурированные инструменты чтения (`task_get`, `task_list`, `task_summary`, `task_history`, `task_document`, `task_health_check`), создания и подготовки, claim/lease, блокировок и решений, приёмки/завершения/архивации, а также `task_export`, `task_backup` и `task_restore`. Аргументы проверяются строго по `inputSchema` до вызова сервиса: неправильный тип, enum, обязательное или неизвестное поле даёт `validation_failed`. Мутации требуют `task_id` и `expected_version`; `operation_id` передаётся только методам, которые поддерживают идемпотентность. После `task_version_conflict` перечитайте задачу и решите, применимо ли исходное намерение; адаптер не повторяет мутацию сам. Успешный `structuredContent` всегда объект: списки и строки находятся в `value`, объектные результаты — на верхнем уровне; ошибка находится в `error` и сопровождается `isError: true`.

Для Python-оркестратора в том же процессе MCP избыточен: вызывайте `TaskManagerService` напрямую. CLI остаётся резервным способом диагностики и подключения клиентов без MCP.

Для проверки установленного окружения из onboarding используйте `orchestrator-onboarding check-task-manager --target . --python <интерпретатор>`. Команда запускает реальный stdio handshake (`initialize`, `tools/list`, `task_health_check`) и не меняет глобальную конфигурацию MCP. Для надёжного запуска на Windows можно сгенерировать локальный фрагмент конфигурации:

```powershell
orchestrator-onboarding mcp-config --target . --python .\.venv\Scripts\python.exe --output .tmp\task-manager-mcp.json
```

Файл создаётся только по явному вызову, только внутри целевого проекта и не регистрируется автоматически в Codex или другом MCP-хосте. В конфигурации используется выбранный абсолютный Python-интерпретатор и запуск модуля `orchestrator_task_manager.task_mcp`, поэтому наличие команды в глобальном `PATH` не требуется. Для нескольких проектов сгенерируйте отдельную запись с собственным именем и корнем; пакет и код MCP при этом остаются общими.

## Команды защищённых операций

У каждой мутации ниже есть `task_id` и необязательный `--expected-version`. Без флага CLI сам читает текущую версию. При конфликте возвращает ошибку, после которой нужно прочитать show/history и оценить исходное намерение. Для идемпотентного повтора сохраните первоначальную expected_version и одинаковые параметры; `--operation-id` поддерживается командами start, ready, claim, run-link, decision, transition, complete, accept, archive, unarchive, purge и create. Те же команды, кроме purge, поддерживают `--event-context` с JSON-объектом actor_ref/source/correlation_id/run_ref. Остальные команды не обещают идемпотентность: после неопределённого результата сначала проверьте карточку и историю.

| Команда | Обязательные флаги сверх task_id | Дополнительные параметры |
| --- | --- | --- |
| start | --run-ref | operation-id, event-context |
| refine | хотя бы одно изменение | --objective, --problem-statement, повторяемые --criterion, --constraint, --evidence-ref |
| metadata | --title | |
| artifact | --role, --ref | --path, --sha256, --metadata (JSON-объект); для plan нужны путь и хеш |
| execution-package | --ref, --plan-sha256, --prepared-source-revision | --specification-sha256 (legacy) |
| ready | | operation-id, event-context |
| claim | --worker-ref | --lease-seconds (30..86400, по умолчанию 900), operation-id, event-context |
| renew | --claim-ref | --lease-seconds |
| release | --claim-ref, --to, --reason | to: ready/preparing/blocked/awaiting_input, с сохранением guards |
| recover | | требуется истёкший claim и отсутствие активного запуска |
| run-link | --run-ref, --relation | relation: active/finished, operation-id, event-context |
| blocker-add | --type, --summary | повторяемый --evidence-ref, --non-blocking |
| blocker-resolve | --blocker-ref, --resolution | |
| decision | --decision-type, --value | --artifact-ref, --candidate-revision, operation-id, event-context |
| transition | --to, --reason | operation-id, event-context; не заменяет start/ready/claim |
| awaiting-acceptance | | нужны readiness и acceptance_package, закрытый запуск |
| complete | --completion-decision-ref | требуется уже зарегистрированная приёмка; operation-id, event-context |
| accept | --candidate-revision, --completion-decision-ref | атомарная явная приёмка и завершение; --artifact-ref, operation-id, event-context |
| cancel | --reason | нельзя отменять с активным запуском или claim |
| archive/unarchive/purge | --reason | --actor-ref для archive/purge, operation-id; purge требует retention |
| external-link | --tracker, --external-ref | |

`artifact --metadata` должен содержать объект, например `'{"plan_sha256":"...","status":"approved"}'`. При сложном shell-экранировании используйте Python API с обычным словарём. Сервис регистрирует существующие свидетельства; не создавайте фиктивный review, readiness или решение пользователя ради прохождения guard.

Типовые операции (замените ID, ссылки и ревизию фактическими значениями):

```powershell
orchestrator-tasks --project . claim TASK-0001 --worker-ref agent-1 --lease-seconds 900
orchestrator-tasks --project . renew TASK-0001 --claim-ref CLAIM-... --lease-seconds 900
orchestrator-tasks --project . blocker-add TASK-0001 --type missing_access --summary "Нет доступа"
orchestrator-tasks --project . blocker-resolve TASK-0001 --blocker-ref BLOCK-01 --resolution "Доступ получен"
orchestrator-tasks --project . release TASK-0001 --claim-ref CLAIM-... --to blocked --reason "Ожидание доступа"
orchestrator-tasks --project . transition TASK-0001 --to ready --reason "Блокер разрешён"
orchestrator-tasks --project . decision TASK-0001 --decision-type clarification --value "Ответ пользователя"
orchestrator-tasks --project . accept TASK-0001 --candidate-revision commit-123 --completion-decision-ref acceptance/commit-123 --expected-version 17 --operation-id accept-task-1-rev-123
orchestrator-tasks --project . cancel TASK-0001 --reason "Запрос отменён пользователем"
```

Команда accept применяется только после явной приёмки пользователем текущей ревизии в awaiting_acceptance. Успех увеличивает версию на 1 и создаёт одно task_completed-событие с решением. При ошибке не записывает ни приёмку, ни завершение. Повтор команды выше использует прежнюю версию 17 и тот же operation-id; новая ревизия означает новое намерение и новый ID операции.

## Backup, restore и диагностика

`archive` доступна только для completed/cancelled, `unarchive` обратимо возвращает задачу в список, а `purge` удаляет архивную завершённую или отменённую задачу после трёх календарных месяцев с terminal-события и сохраняет tombstone. `export` вызывает публичный `export_state` и создаёт согласованный JSON-снимок задач, событий и tombstone, не изменяя карточки и историю. Попытка экспорта поверх рабочей SQLite отклоняется как `validation_failed`; файловая ошибка возвращается как `repository_failure` в JSON на stderr с кодом выхода 2. `backup` вызывает одноимённый метод и создаёт консистентную SQLite-копию; `restore` также вызывает одноимённый метод. Перед restore остановите веб-панель через Ctrl+C и другие процессы/мутации Task Manager. Restore проверяет структуру и integrity, мигрирует временную копию, сохраняет прежнюю рабочую БД как `.pre-restore` через SQLite backup, затем заменяет рабочий файл. Исходная копия остаётся неизменной. На Windows открытый файл может вызвать repository_failure; закройте использующие его процессы и повторите команду. При неудаче замены текущая БД сохраняется, а details.safety_copy указывает копию только этой попытки. Перенос состояния не является протоколом координации работающих клиентов.

`validate` возвращает `result: []` без проблем. Она читает единый снимок и сообщает повреждённые карточки, последовательности событий и устаревшие ready-документы; исправлений не делает. После мутаций проверяйте show и history, при сомнениях — validate. Список и summary не заменяют проверку готовности.

При restore из самого `.pre-restore` новый снимок рабочей базы сохраняется с уникальным суффиксом; точный путь указан в результате safety_copy. Исходный backup остаётся неизменным.

Панель открывается по `http://127.0.0.1:8765/`, показывает список, поиск, фильтр, карточку, историю, блокеры, решения и привязанные документы. Она слушает только `127.0.0.1` и не имеет HTTP-команд изменения задач. Остановите сервер `Ctrl+C`; не публикуйте его через прокси, поскольку пользовательской аутентификации нет.

## Python API и версии

Разделение реализации не меняет работу агента: используйте публичный импорт из пакета. Старый `orchestrator_task_manager.task_manager` также сохраняет импорт классов. Схема базы остаётся версии 5; обновление пакета не требует ручного переноса данных. Внутренние границы для разработчиков описаны в [архитектуре](architecture.md).

```python
from pathlib import Path
from orchestrator_task_manager import TaskError, TaskManagerService

service = TaskManagerService(Path("/путь/к/проекту"))
task = service.create_task(
    title="Проверить расчёт",
    task_type="implementation",
    objective="Исправить сценарий X",
    original_request="Исправь расчёт X",
    acceptance_criteria=["Сценарий X даёт ожидаемый результат"],
)
task = service.add_blocker(
    task["id"], task["version"],
    blocker_type="missing_access", summary="Нет доступа к тестовому окружению",
)
print(task["status"], service.get_history(task["id"])[-1]["type"])
```

Для каждого последующего изменения сначала возьмите актуальную `version` через `get_task`, затем вызовите специализированный метод с `expected_version`. При `task_version_conflict` заново прочитайте задачу и оцените намерение; слепой повтор может изменить уже другую версию. Защищённые переходы описаны в [контракте](contract.md). Не записывайте статус или события напрямую в SQLite и не прикрепляйте фиктивные артефакты или решения пользователя ради прохождения guard.

Обязательные параметры методов Python перечислены ниже. Все мутации, кроме create_task, принимают task_id и expected_version. Неправильный вызов сигнатуры остаётся TypeError; ошибки предметных значений дают TaskError.

| Метод | Обязательные параметры сверх task_id/expected_version |
| --- | --- |
| create_task | title, task_type, objective, original_request, acceptance_criteria |
| get_task / get_claim | только task_id; версии не требуют |
| list_tasks / summary / health_check | нет; чтение без версии |
| get_history | только task_id; optional after_sequence |
| get_document | task_id, role; без версии |
| list_executable_tasks | нет; optional limit |
| export_state / backup | destination; без task_id и версии |
| restore | source; без task_id и версии |
| start_preparation | run_ref |
| refine_task_definition | хотя бы одно: objective, problem_statement, acceptance_criteria, constraints |
| update_metadata | title |
| attach_artifact | role, ref; path и sha256 для plan/legacy specification |
| attach_execution_package | ref, plan_sha256, prepared_source_revision |
| mark_ready / recover_expired_claim / mark_awaiting_acceptance | нет |
| claim_task | worker_ref |
| renew_claim | claim_ref |
| release_claim | claim_ref, target_status, reason |
| link_workflow_run | run_ref, relation |
| add_blocker | blocker_type, summary |
| resolve_blocker | blocker_ref, resolution |
| record_user_decision | decision_type, value; candidate_revision для приёмки текущей ревизии |
| transition_status | to, reason |
| complete_task | completion_decision_ref |
| accept_task | candidate_revision, completion_decision_ref |
| cancel_task / archive_task / unarchive_task / purge_task | reason |
| register_external_link | tracker, external_ref |

```python
# Явная приёмка ранее показанного пользователю результата:
task = service.get_task("TASK-0001")
version = task["version"]
task = service.accept_task(
    task["id"], version, candidate_revision="commit-123",
    completion_decision_ref="acceptance/commit-123", operation_id="accept-task-1-rev-123",
)
# Повтор после неопределённого результата: те же аргументы и исходная version.
```

clock может возвращать aware datetime в любом часовом поясе; он переводится в UTC. Naive datetime означает UTC, а не локальное время компьютера. Для injected clock всегда используйте одну выбранную временную шкалу.

Хранилище локальное. Карточка Task Manager является канонической спецификацией задачи; `plan.md` описывает способ реализации. Старые `specification.md` читаются для совместимости, но не участвуют в `ready` guard. Graph Runtime и автоматический исполнитель также не входят в пакет.
