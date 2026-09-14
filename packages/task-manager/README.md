# Task Manager Service

Самостоятельный Python-пакет для хранения и просмотра задач. Не требует ядра Orchestrator и Graph Runtime. Требуется Python 3.11+; внешних зависимостей нет.

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
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks resources
orchestrator-tasks-web --project . --port 8765
```

CLI возвращает JSON; панель доступна на `http://127.0.0.1:8765/` и только для чтения. Состояние находится в `<проект>/.orchestrator/state/tasks.sqlite3`. Каталог `state/` следует исключить из Git. Сервис не создаёт спецификацию, план или запуск графа автоматически.

Публичный Python API:

```python
from pathlib import Path
from orchestrator_task_manager import TaskManagerService

service = TaskManagerService(Path("."))
task = service.get_task("TASK-0001")
events = service.get_history(task["id"])
```

Для мутаций после создания передавайте текущую `task["version"]` как `expected_version`. Подробности — во входящих в пакет [контракте](src/orchestrator_task_manager/resources/docs/contract.md) и [гайде](src/orchestrator_task_manager/resources/docs/usage.md). Полный [пример skill для агента](src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) также входит в пакет и не ссылается на материалы ядра. После установки команда `orchestrator-tasks resources` покажет точные пути к этим трём файлам; для проектного использования скопируйте каталог примера в `.agents/skills/` целевого проекта.

## Проверка при разработке

После установки пакета в окружение запустите из корня репозитория:

```powershell
python -m unittest discover -s packages/task-manager/tests -v
```

Тесты пакета не требуют запущенного Graph Runtime или ядра Orchestrator.
