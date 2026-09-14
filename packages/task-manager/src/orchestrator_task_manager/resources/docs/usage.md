# Использование Task Manager Service

**Статус:** инструкция к реализованному первому срезу. Нужна Python 3.11+; внешних зависимостей у пакета нет.

## Установка и расположение ресурсов

Установите пакет из каталога `packages/task-manager/` командой `python -m pip install .` или `python -m pip install -e .` для разработки. После установки исходный репозиторий не нужен. `orchestrator-tasks resources` возвращает пути к этому гайду, [контракту](contract.md) и [примеру skill](../examples/skills/orchestrator-task-manager/SKILL.md) внутри установленного пакета. Если хотите использовать пример как проектный Codex skill, скопируйте весь каталог `orchestrator-task-manager/` в `.agents/skills/` целевого проекта; не изменяйте чужие файлы в этом каталоге.

Всегда указывайте корень целевого проекта через `--project`, если команда запускается не из него. База создаётся в `<проект>/.orchestrator/state/tasks.sqlite3`; исключите `.orchestrator/state/` из Git. Спецификация и план, если нужны, могут версионироваться в `.orchestrator/tasks/`.

## CLI и панель

```powershell
orchestrator-tasks --project . create --title "Проверить расчёт" --type implementation --objective "Исправить X" --request "Исправь расчёт X" --criterion "X даёт ожидаемый результат"
orchestrator-tasks --project . list --status created
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks resources
orchestrator-tasks-web --project . --port 8765
```

CLI возвращает JSON. Для `list` доступны повторяемый `--status`, а также `--type`, `--query`, `--limit`; `history` поддерживает `--after-sequence`. `validate` возвращает пустой список при отсутствии обнаруженных проблем и ненулевой код выхода при найденных проблемах; она не исправляет данные. Созданная задача остаётся в `created`: подготовка и выполнение автоматически не запускаются.

Панель открывается по `http://127.0.0.1:8765/`, показывает список, поиск, фильтр, карточку, историю, блокеры, решения и привязанные документы. Она слушает только `127.0.0.1` и не имеет HTTP-команд изменения задач. Остановите сервер `Ctrl+C`; не публикуйте его через прокси, поскольку пользовательской аутентификации нет.

## Python API и версии

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

Хранилище локальное. Копирование работающей базы не является поддерживаемым резервным копированием; отдельный механизм экспорта и восстановления пока не реализован. Graph Runtime и автоматический исполнитель также не входят в пакет.
