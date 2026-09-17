# Независимый аудит агентского взаимодействия с Task Manager Service

**Дата:** 2026-09-17  
**Профиль аудитора:** GPT-5.6 Luna, reasoning high  
**Статус:** завершённый аудит/тестирование; реализация не изменялась

## Итог

Собственный сквозной harness явно вызвал все 35 публичных методов `TaskManagerService` и все 35 CLI-команд. Положительно проверены также четыре метода, отсутствовавшие в статической сверке штатных тестов: `get_claim`, `list_executable_tasks`, `register_external_link`, `release_claim`.

Обнаружена одна воспроизводимая проблема P1: CLI-команда `export` завершается необработанным `AttributeError`, потому что dispatch пытается вызвать `TaskManagerService.export`, хотя публичный метод называется `export_state`. Остальные проверенные сценарии дали ожидаемые результаты. После purge `get_task` возвращает `task_not_found`; это оставлено как намеренный результат: общий список кодов ошибки сам по себе не обещает отдельный код для `get`, а tombstone доступен через export.

### Сводка покрытия

| Область | Результат |
|---|---:|
| Публичные методы Python API | 35/35 явно проверены |
| CLI-команды | 35/35 вызваны; имена считались пересечением с каталогом команд, `--help` не включён |
| Успешный путь CLI | 34/35; `export` — подтверждённый дефект |
| Штатные тесты Task Manager | 57/57 passed |
| Неожиданные ошибки harness | 0 в финальном прогоне |
| Найденные дефекты | 1: P1 CLI export |

## Границы и безопасность проверки

Проверялись только новый пакет `packages/task-manager/src/orchestrator_task_manager` и его публичные интерфейсы. `obsolete/` не импортировался, не запускался и не редактировался. Рабочие задачи, включая TASK-0024, не принимались и не завершались; restore/purge в рабочем проекте не выполнялись.

Все мутирующие операции собственного сценария выполнялись в уникальных проектах под:

`C:\Users\aliak\Documents\development\ai-orchestrator\.tmp\task-manager-agent-audit-luna\task-manager-agent-audit-akjvpk7l\`

Внутри были отдельные synthetic-проекты `api`, `cli`, `cli-special\accept`, `cli-special\recover`, `cli-special\purge`, `retention`, `transfer`. Карточки, планы, решения, ссылки и run-ref были явно synthetic. Рабочая SQLite не читалась и не изменялась через прямой SQL; harness использовал `TaskManagerService`, CLI и HTTP read-only панель.

## Окружение и команды

- Windows, текущая рабочая директория: `C:\Users\aliak\Documents\development\ai-orchestrator`.
- Python: `C:\Users\aliak\Documents\development\ai-orchestrator\.venv\Scripts\python.exe`.
- Пакет `orchestrator-task-manager` 0.1.0 установлен в `.venv` editable-режимом.
- Исходники: `packages/task-manager/src/orchestrator_task_manager`.
- Тесты: `packages/task-manager/tests`.

Штатный прогон:

```powershell
& '.venv\Scripts\python.exe' -m unittest discover -s packages/task-manager/tests -v
```

Результат: `Ran 57 tests ... OK`.

Собственный финальный прогон:

```powershell
& '.venv\Scripts\python.exe' '.tmp\task-manager-agent-audit-luna\audit_task_manager_agent.py'
```

Результат финального запуска: `public_methods_checked=35`, `cli_commands_checked=35`, `findings=1`, `errors=0`. Машинные результаты сохранены в [audit-results.json](../../.tmp/task-manager-agent-audit-luna/audit-results.json); harness — в [audit_task_manager_agent.py](../../.tmp/task-manager-agent-audit-luna/audit_task_manager_agent.py).

Дополнительно выполнены импорт без ядра через `python -S`, проверка legacy-импорта, запуск `orchestrator-tasks-web`, локальный HTTP GET/POST и все CLI-вызовы harness.

## Матрица покрытия публичного Python API

| Возможность / метод | Как проверена | Фактический результат | Замечания |
|---|---|---|---|
| `create_task` | API: synthetic card, обязательные поля, Unicode, `operation_id`, `event_context`, повтор | Успех, повтор вернул ту же карточку | Дубликата нет |
| `get_task` | Повторное чтение, после каждой мутации; после purge — чтение удалённого ID | Успех; после purge `task_not_found` | Для `get` это не объявлено отдельным обещанием в контракте |
| `list_tasks` | query/type/status/limit; cursor на двух страницах; archive default/include | Успех | Архив скрыт по умолчанию, cursor работает |
| `summary` | query и агрегаты по synthetic карточке | Успех | Не смешивает tombstone с total |
| `get_history` | Полная история и `after_sequence=1` | Успех | События соответствуют мутациям |
| `get_document` | Чтение UTF-8 plan, SHA-256; файл изменялся и возвращался | Успех; stale даёт `guard_failed` | Проверяются возвращаемые байты |
| `get_claim` | До claim — `None`, после конкурентного claim — активный claim | Успех | Явно покрыт собственным runtime-сценарием |
| `list_executable_tasks` | После прохождения `ready` guard | Успех | Development-задача найдена |
| `health_check` | Начальный `[]`, stale plan, возврат исходных байтов, повторный `[]` | Успех | Read-only диагностика обнаружила stale ready |
| `archive_task` | Completed synthetic task, затем список | Успех | Status остаётся terminal, archive скрывает карточку |
| `unarchive_task` | Снятие archive и повторная архивация | Успех | Операция обратима |
| `purge_task` | Cancel + archive; ранний отказ; injected clock после 3 календарных месяцев; replay | Успех | Tombstone и сохранение ID подтверждены через export/replay |
| `export_state` | Export активных/архивных/tombstone данных; nested parent; API | Успех | Создаёт отсутствующий parent; это не дефект |
| `backup` | SQLite backup в отдельный временный файл | Успех | Источник состояния не изменён |
| `restore` | Round-trip, corrupt input, safety copy, source сохранён | Успех | Невалидный backup даёт `repository_failure` |
| `start_preparation` | `created → preparing`, `run_ref`, event context, operation replay | Успех | Активный preparation run закрыт отдельно |
| `refine_task_definition` | Objective/problem/criteria/constraints/evidence refs | Успех | Definition version увеличивается |
| `update_metadata` | Unicode title и expected-version conflict/re-read retry | Успех | Terminal guard также проверен |
| `attach_artifact` | Plan с реальным SHA-256, review/readiness/acceptance roles | Успех | Невалидный/stale документ не обходится |
| `attach_execution_package` | Package с plan hash и prepared source revision | Успех | Связь с текущей версией plan проверена ready guard-ом |
| `mark_ready` | Полный plan/review/package guard и закрытый run | Успех | `ready` не достигается одной записью статуса |
| `claim_task` | Два конкурента с одной версией + обычный claim | Один победитель; второй `task_version_conflict` | Атомарность и lease подтверждены |
| `renew_claim` | Продление активного claim с UTC lease | Успех | Lease увеличен |
| `release_claim` | `active → blocked` и `active → awaiting_input` с сохранением guards | Успех | Явно покрыт собственным runtime-сценарием |
| `recover_expired_claim` | Injected clock: claim 30 s, clock +31 s, без active run | Успех, `active_claim=None`, status `ready` | Собственный успешный API-путь |
| `link_workflow_run` | `active` и `finished` для preparation и execution run | Успех | Active run блокирует преждевременный ready/acceptance |
| `add_blocker` | Synthetic blocking blocker с evidence ref | Успех, status `blocked` | Open blocker мешает resume/ready |
| `resolve_blocker` | Resolve по blocker ref и resolution | Успех | После resolve возобновление прошло |
| `transition_status` | blocked/resume и awaiting_input/decision/resume | Успех | Без blocker/decision guards не обойдены |
| `record_user_decision` | Clarification в awaiting_input и acceptance перед complete | Успех | Acceptance привязана к candidate revision |
| `mark_awaiting_acceptance` | Readiness + acceptance package + закрытый run | Успех | Claim очищается атомарно |
| `complete_task` | Decision `acceptance=approved` + complete для текущей ревизии | Успех | Terminal guards проверены |
| `accept_task` | Atomic explicit synthetic acceptance, wrong-path guards, same operation replay | Успех | Решение и completion записываются одной мутацией |
| `cancel_task` | Synthetic `created → cancelled`; terminal/active guards | Успех | После cancel архивирование разрешено |
| `register_external_link` | API-ссылка на synthetic tracker и retention карточку | Успех | Сохранена как `projection` |

### Отдельно проверенные ранее не покрытые статической сверкой методы

`get_claim`, `list_executable_tasks`, `register_external_link` и `release_claim` вызваны непосредственно из собственного Python harness, а не засчитаны по косвенным CLI-тестам. `recover_expired_claim` также имеет успешную собственную API-пробу с injected clock.

## Матрица CLI

Проверка считала только пересечение имён фактически вызванных команд с каталогом `CLI_COMMANDS`; smoke `--help` не увеличивает число команд. Итого 35/35. У `accept`, `recover`, `purge` были и отрицательные guard-вызовы, и успешные positive-вызовы на отдельных временных synthetic проектах. Единственная error-only команда — `export`.

| Команды | Фактический результат |
|---|---|
| `resources`, `api`, `list`, `summary`, `show`, `history`, `document`, `validate` | Успешно; JSON и локальные read-only ответы проверены |
| `create`, `metadata`, `refine`, `start`, `artifact`, `execution-package`, `ready` | Успешно; обычный CLI lifecycle |
| `claim`, `renew`, `release`, `run-link`, `blocker-add`, `blocker-resolve`, `decision`, `transition`, `awaiting-acceptance`, `complete` | Успешно; pause/resume и acceptance guards пройдены |
| `accept` | Успешно на `cli-special\accept`; дополнительно неверный terminal-path дал `invalid_transition` |
| `cancel`, `archive`, `unarchive`, `external-link` | Успешно на synthetic CLI карточках |
| `recover` | Успешно на `cli-special\recover`; injected API clock создал lease в 2020, CLI с текущими часами увидел истечение |
| `purge` | Успешно на `cli-special\purge`; cancel+archive с injected временем 2020, CLI подтвердил retention. Ранний purge также дал ожидаемый `retention_not_elapsed` |
| `backup`, `restore` | Успешно; backup/restore round-trip через CLI |
| `export` | P1: traceback `AttributeError`; положительный путь не работает |

Парсерные ошибки и JSON-коды выхода также представлены штатными тестами (`test_parse_errors_are_json_and_do_not_create_state`). В собственном запуске конфликт версии CLI вернул код 2 и JSON, без немого повтора.

## Сквозные результаты по группам требований

### Обнаружение, чтение и подготовка

`resources`, `api`, `--help` вызваны без необходимости создавать рабочее состояние. API и CLI карточки сохраняются и читаются повторно. Unicode `ё 日本語 🚦 Ω` сохраняется в title/request/criteria. Проверены статусы, type/query-фильтры, cursor, archive filter, summary, history, document и executable projection.

Подготовительный путь `created → preparing → ready` прошёл с `run_ref`, закрытием подготовки, реальным `plan.md`, SHA-256, approved `plan_review`, Execution Package и source revision. Stale plan после ready был обнаружен `health_check` и `get_document`; после возврата исходных байтов диагностика снова чистая. Отдельная инвалидация после изменения определения covered штатным тестом `test_definition_change_after_ready_invalidates_package`; она не выдается за результат только собственного сценария.

### Claim, lease, гонки и идемпотентность

Два потока с двумя сервисными экземплярами и одинаковой `expected_version` дали ровно одного победителя. Проигравший получил `task_version_conflict` (`expected=10`, `actual=11`), а не перезаписал claim. Renew увеличил lease. Active/finished run-ref, blocker, release и recover проверены. Naive/aware UTC и календарный retention проверены injected clock-ом.

`operation_id` проверен для create, preparation/ready/run-link/decision/accept/purge; одинаковый отпечаток возвращает прежний результат, другой payload должен быть новым намерением. Event context сохраняется в событиях synthetic карточки. Конфликт expected version обработан безопасно: stale mutation отклонена, затем выполнен reread и осознанный retry.

### Ожидание, блокировки и приёмка

Проверены `blocked`, `awaiting_input`, `pending_decision_count`, resume только после resolve/decision, активный run guard, acceptance package и readiness. Есть два acceptance пути: атомарный `accept_task` с synthetic decision harness и прежний раздельный `record_user_decision` + `complete_task`. Проверены wrong revision/terminal guards и успешный CLI `accept`.

### Archive/retention/purge

Архивирование выполнено только для completed/cancelled; default list скрывает архив, include-archived показывает, unarchive обратим. Injected clock `2026-01-31 → 2026-04-30` проверил именно календарные месяцы и ранний отказ. Успешный purge создал tombstone, не освободил ID, а повтор с тем же operation ID вернул сохранённый результат. `get_task` после purge дал `task_not_found`; это не внесено в findings, так как контракт не обещает `task_purged` именно для get.

### Export/backup/restore/validate

API export, backup и restore прошли round-trip. Corrupt backup отвергнут без замены текущего состояния; safety copy создана при успешном restore; nested parent для export создаётся штатно. `validate`/`health_check` read-only. CLI backup/restore прошли; CLI export отдельно выявил P1 ниже.

### Панель и модульная независимость

`orchestrator-tasks-web` ответил `200` на `127.0.0.1`, тело 9004 байта содержит UI, POST получил `405`; mutation endpoint не обнаружен в проверенном пути. Импорт пакета с `python -S` при добавленном только `packages/task-manager/src` завершился `ok`; `TaskManagerService` из фасада и legacy `task_manager` — тот же класс. Штатные модульные тесты также подтвердили dependency layers, read transaction и совместимые импорты.

## Измерения агентского удобства

Все числа ниже — один локальный Windows-прогон, не норматив производительности. Времена CLI включают отдельный запуск процесса; API-времена не включают конструктор/миграцию.

### Обычный сценарий

Для фактического synthetic CLI пути `create → prepare → ready → claim → pause/resume → acceptance → complete` harness отдельно насчитал:

| Метрика | Значение |
|---|---:|
| CLI-вызовов | 36 |
| read-команд внутри него (`list/summary/show/history/document/validate`) | 6 |
| JSON bytes stdout+stderr | 66 983 |
| суммарное время процессов | 5.847 s |

Эти 36 вызовов не включают smoke/help, 20 повторных show, stale-conflict chain, secondary cancel/archive карточку, transfer-команды и специальные positive accept/recover/purge. Совокупный harness составил 79 CLI-вызовов, 125 906 stdout bytes + 1 548 stderr bytes и 12.542 s; эти числа не приписываются ordinary lifecycle.

### API и CLI на одной и той же карточке

Перед claim одна неизменная CLI карточка `TASK-0001` была прочитана API `get_task` и CLI `show`; `API result == CLI result` — `true`.

| Операция, 20 повторов | JSON bytes | Время | Среднее |
|---|---:|---:|---:|
| API `get_task` той же карточки | 26 940 | 0.004976 s | 0.249 ms |
| CLI `show` той же карточки | 34 840 | 2.988606 s | 149.430 ms |

Один ответ: API result сериализуется в 1 347 байт, CLI JSON с `ok/result`, indent и переводами строк — 1 742 байта. Разница — формат оболочки, а не содержимое карточки. Сравнение не является чистым измерением IPC: CLI включает новый процесс, parsing, создание сервиса и migration check; API использует уже созданный сервис. Это даёт конкретное основание рассмотреть долгоживущий структурированный адаптер при высокочастотной работе, но не обосновывает пока новый daemon/MCP.

### Восстановление после конфликта

Реальная цепочка CLI была `claim` со stale `--expected-version=9` → `show` → успешный `metadata` retry с актуальной версией:

| Шаг | Время | JSON bytes |
|---|---:|---:|
| stale claim, код 2 | 0.165 s | 302 |
| reread `show` | 0.145 s | 1 928 |
| осознанный retry | 0.157 s | 1 926 |
| последовательность | 0.466 s | 4 156 |

API-сценарий expected-version дал `task_version_conflict`, затем retry после reread. Дополнительный API benchmark 100 `get_task`: 250 100 JSON bytes, 0.028627 s, 0.286 ms/call. Это узкие локальные измерения одной карточки; массовая нагрузка 100/1000 карточек в аудит не включалась.

## Findings

### P1 — CLI `export` вызывает несуществующий метод

- **Воспроизведение:** `orchestrator-tasks --project <temporary-project> export <temporary-project>\cli-export.json`.
- **Ожидание:** JSON export и `ok=true`, как для публичного `export_state` и как заявлено в usage/contract.
- **Факт:** процесс завершается кодом 1 с traceback: `AttributeError: 'TaskManagerService' object has no attribute 'export'`.
- **Исходник:** [task_cli.py](../../packages/task-manager/src/orchestrator_task_manager/task_cli.py:195) — ветка выбирает `getattr(service, args.command)` для `args.command == "export"`; публичный метод находится в [service.py](../../packages/task-manager/src/orchestrator_task_manager/service.py:143) как `export_state`.
- **Влияние:** агент не может экспортировать состояние штатным CLI; требуется Python API или обход. Ошибка не оформляется JSON и не получает предусмотренный код 2, а оставляет traceback. Backup/restore через CLI при этом работают.
- **Минимальное исправление:** явно сопоставить CLI `export` с `service.export_state` (или переименовать dispatch mapping), добавить CLI regression test на файл, JSON-ответ, exit code и отсутствие traceback.

Других findings по финальному собственному прогону нет. `task_not_found` после purge не является finding этого отчёта: контракт перечисляет `task_purged` среди общих кодов, но не требует его для метода `get_task`; наблюдаемое поведение согласовано с обычным not-found чтением и отдельно подтверждается tombstone в export.

## Архитектурная оценка и приоритеты

### Обязательное исправление

1. Исправить P1 CLI `export` и добавить регрессионную проверку. Это единственная подтверждённая поломка агентского публичного пути.

### Полезные улучшения после P1

- Добавить в CLI dispatch единый явный mapping `command → public method`, чтобы подобные расхождения имён обнаруживались тестом/проверкой API.
- Для частых агентских read-операций рассмотреть структурированный адаптер или долгоживущий процесс: на этой машине 0.249 ms для API против 149.430 ms для отдельного CLI запуска на той же карточке. Это рекомендация по подтверждённой стоимости запуска, не требование вводить daemon.
- Сохранить компактные проекции (`summary/list`) как основной путь агента; full `show` нужен для решения и аудита. В этом срезе нет массового benchmark, поэтому нельзя утверждать пороги, при которых потребуется отдельная projection API.

### Преждевременное усложнение

Внедрение MCP, нового daemon-протокола, новых зависимостей или составных mutation-операций сейчас не оправдано измерениями. Guards и expected-version должны остаться на границе сервиса; ускорение должно использовать существующий публичный API, а не ослаблять атомарность/идемпотентность. Нет evidence по сетевой многопользовательской нагрузке, Graph Runtime и внешним трекерам.

## Ограничения аудита

- Положительный CLI `export` не проверен, потому что команда неисправна; API `export_state` проверен.
- Для CLI positive `recover` и `purge` состояние с прошедшим временем было подготовлено API с injected clock в отдельных проектах, затем мутация выполнена настоящим CLI с сохранённой версией; это проверяет CLI dispatch и guards, но не CLI-инъекцию часов (такого флага нет).
- Нет нагрузочного прогона 100/1000 карточек, длительного многопроцессного contention, сетевого размещения или recovery Graph Runtime.
- Web проверен локально и read-only; authentication, reverse proxy и внешний доступ намеренно не проверялись.
- Штатные 57 тестов отделены от собственных сквозных проб; документация и project-status не трактовались как доказательство runtime без вызова.

## Тестовые артефакты и изменённые файлы

Созданы только разрешённые собственные артефакты:

- [audit_task_manager_agent.py](../../.tmp/task-manager-agent-audit-luna/audit_task_manager_agent.py) — воспроизводимый harness;
- [audit-results.json](../../.tmp/task-manager-agent-audit-luna/audit-results.json) — результаты последнего прогона;
- этот отчёт: `docs/reports/2026-09-17-task-manager-agent-audit-luna.md`.

Harness также создал synthetic temporary cards/plans, backup/export inputs, safety copies и логи внутри `.tmp/task-manager-agent-audit-luna/task-manager-agent-audit-*`. Они не относятся к рабочему проекту. Product code, существующие тесты, рабочие гайды, `project-status`, рабочие задачи и рабочая SQLite в рамках аудита не изменялись.
