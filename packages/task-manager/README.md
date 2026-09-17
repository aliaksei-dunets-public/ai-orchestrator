# Task Manager Service

Самостоятельный Python-пакет для хранения, просмотра и защищённого изменения задач. Не требует ядра Orchestrator и Graph Runtime. Требуется Python 3.11+; внешних зависимостей нет.

## Установка

Из корня репозитория для разработки:

```powershell
python -m pip install -e .\packages\task-manager
```

Для целевого проекта с репозиторием в `tools/orchestrator`:

```powershell
python -m pip install -e .\tools\orchestrator\packages\task-manager
```

Для отдельного использования можно установить пакет из его каталога обычным `python -m pip install <путь-к-пакету>`; после установки репозиторий Orchestrator не нужен для работы сервиса.

## Использование

```powershell
orchestrator-tasks --project . create --title "Проверить расчёт" --objective "Исправить X" --request "Исправь X" --criterion "X работает"
orchestrator-tasks --project . list
orchestrator-tasks --project . list --format table
orchestrator-tasks --project . summary
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
orchestrator-tasks api
orchestrator-tasks-web --project . --port 8765
orchestrator-task-manager-mcp --project .
```

CLI возвращает JSON; панель доступна на `http://127.0.0.1:8765/` и только для чтения. Состояние находится в `<проект>/.orchestrator/state/tasks.sqlite3`. Каталог `state/` следует исключить из Git. Версия схемы хранится в `PRAGMA user_version`; изменения схемы применяются встроенным реестром миграций, а неподдерживаемая будущая версия отклоняется без записи. Для повторяемых запросов ключевые методы принимают необязательный `operation_id`; `event_context` связывает событие с актором, источником, корреляцией и запуском. Архивирование обратимо, а `purge` разрешён архивным `completed` и `cancelled` задачам после трёх календарных месяцев и сохраняет tombstone. `export` создаёт переносимый JSON, `backup` — консистентную копию, `restore` проверяет копию и сохраняет предыдущую БД как `.pre-restore`. Карточка задачи является каноническим определением; сервис не создаёт `plan.md` или запуск графа автоматически.

CLI покрывает подготовку, артефакты, ready, claim/lease, паузы, блокеры, решения и завершение через публичный API. Мутация без `--expected-version` читает текущую версию; с флагом проверяет указанную. `accept` атомарно регистрирует явную приёмку текущей ревизии и завершает задачу, требуя `--candidate-revision` и `--completion-decision-ref`. `summary` агрегирует SQL без загрузки карточек. По умолчанию JSON сохраняет полные данные; `--format table` даёт компактный list/show/summary. Неправильные аргументы также дают JSON-ошибку. Перед restore остановите другие процессы и мутации Task Manager; на Windows открытая база может препятствовать замене.

MCP stdio-адаптер:

Для внешнего агента используйте `orchestrator-task-manager-mcp --project <корень-проекта>`. Клиент MCP запускает один процесс на проект; пакет и код общие, состояние и SQLite раздельны. Сервер реализует JSON-RPC stdio и предоставляет инструменты чтения, полного жизненного цикла, переноса состояния и диагностики. `project_root` фиксируется при запуске и не меняется инструментальным вызовом. Бизнес-правила выполняет публичный `TaskManagerService`; MCP не пишет SQLite напрямую. CLI остаётся резервным интерфейсом.

После установки проверьте окружение через onboarding: `orchestrator-onboarding check-task-manager --target . --python .\.venv\Scripts\python.exe`. Для MCP-хоста можно явно сгенерировать локальный фрагмент: `orchestrator-onboarding mcp-config --target . --python .\.venv\Scripts\python.exe --output .tmp\task-manager-mcp.json`. Эти команды не изменяют глобальные настройки хоста; конфигурация создаётся только по явному вызову и только внутри проекта.

Для Python-клиента внутри одного процесса используйте API напрямую, без MCP и запуска CLI на каждую операцию:

```python
from pathlib import Path
from orchestrator_task_manager import TaskManagerService

service = TaskManagerService(Path("."))
task = service.get_task("TASK-0001")
events = service.get_history(task["id"])
```

Для мутаций после создания передавайте текущую `task["version"]` как `expected_version`. Карточка Task Manager является канонической спецификацией; отдельный `specification.md` для `ready` не нужен, требуется только согласованный `plan.md`. Подробности — во входящих в пакет [контракте](src/orchestrator_task_manager/resources/docs/contract.md) и [гайде](src/orchestrator_task_manager/resources/docs/usage.md). Полный [пример skill для агента](src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) также входит в пакет и не ссылается на материалы ядра. После установки команда `orchestrator-tasks resources` покажет точные пути к этим трём файлам; для проектного использования скопируйте каталог примера в `.agents/skills/` целевого проекта.

## Проверка при разработке

Реализация разделена по ответственности: contracts, migrations, repository, service, storage_transfer, diagnostics и task_mcp. `task_manager.py` сохраняет прежние импорты; API, схема SQLite и команды не меняются. Границы описаны во входящей в wheel [архитектуре пакета](src/orchestrator_task_manager/resources/docs/architecture.md).

После установки пакета в окружение запустите из корня репозитория:

```powershell
python -m unittest discover -s packages/task-manager/tests -v
```

Тесты пакета не требуют запущенного Graph Runtime или ядра Orchestrator.

Воспроизводимые замеры на временных проектах, без изменения рабочей базы:

```powershell
python packages/task-manager/benchmarks/benchmark_task_manager.py --counts 100 500 1000 --repeats 10
```

Для парного сравнения с доверенным самостоятельным `task_manager.py` до рефакторинга:

```powershell
python packages/task-manager/benchmarks/compare_task_manager.py --baseline <путь-к-прежнему-task_manager.py> --count 1000 --repeats 30
```

Скрипт загружает baseline как Python-код; используйте только собственную проверенную копию. Обе реализации читают одну временную базу с чередованием AB/BA, рабочая база проекта не используется.
