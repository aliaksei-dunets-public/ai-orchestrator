# Задачи в проекте Orchestrator

Реализация пакета разделена на модули без изменения публичного API и схемы базы. Агент может использовать MCP stdio, CLI или импорт из `orchestrator_task_manager`; внутренние границы описаны в [архитектуре пакета](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/architecture.md).

**Статус:** интеграционная инструкция к реализованному Task Manager Service. Полный [гайд по отдельному пакету](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) содержит команды, Python API, панель и ограничения; [контракт](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md) описывает переходы и данные.

Из корня этого репозитория установите пакет командой `python -m pip install -e .\packages\task-manager`. Во внешнем проекте с submodule используйте `python -m pip install -e .\tools\orchestrator\packages\task-manager`. Затем можно запустить `orchestrator-tasks --project . list` или `orchestrator-tasks-web --project . --port 8765`.

Команда `orchestrator-tasks resources` показывает пути к полному гайду, контракту и [примеру skill](../../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) в установленном пакете. В этом репозитории skill автоматически обнаруживается через [проектный указатель](../../.agents/skills/orchestrator-task-manager/SKILL.md). Во внешнем проекте агенту путь сообщает управляемый блок `AGENTS.md`, который добавляет онбординг.

Task Manager можно использовать и без онбординга, указав каталог целевого проекта. Его база локальна и не версионируется. Автоматического исполнения графа пока нет.

Для краткой сводки используйте `orchestrator-tasks --project . summary`, для просмотра человеком — `list --format table`. Защищённые операции подготовки, claim/lease, блокеры и приёмка доступны через CLI; список параметров возвращает `<команда> --help`, Python-сигнатуры — `orchestrator-tasks api`. JSON остаётся основным форматом агента. Перед restore остановите панель и другие процессы/мутации; конфликт версии требует перечитать карточку, а не повторять изменение автоматически.

Для внешнего агента подключайте `orchestrator-task-manager-mcp --project <корень-проекта>` через локальный stdio MCP. Один пакет используется всеми проектами, но клиент запускает отдельный экземпляр на каждый корень; `project_root` фиксирован, а пути MCP export/backup/restore не могут выйти за его пределы. Внутри Python-оркестратора вызывайте `TaskManagerService` напрямую; CLI остаётся запасным интерфейсом.

После установки можно проверить подключение выбранным окружением: `orchestrator-onboarding check-task-manager --target . --python .\.venv\Scripts\python.exe`. Для MCP-хоста, которому нужен явный JSON, используйте `orchestrator-onboarding mcp-config --target . --python .\.venv\Scripts\python.exe --output .tmp\task-manager-mcp.json`. Это создаёт локальный фрагмент с абсолютным Python и фиксированным корнем, но не меняет глобальные настройки хоста.
