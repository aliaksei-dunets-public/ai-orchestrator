# Задачи в проекте Orchestrator

**Статус:** интеграционная инструкция к реализованному Task Manager Service. Полный [гайд по отдельному пакету](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) содержит команды, Python API, панель и ограничения; [контракт](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md) описывает переходы и данные.

Из корня этого репозитория установите пакет командой `python -m pip install -e .\packages\task-manager`. Во внешнем проекте с submodule используйте `python -m pip install -e .\tools\orchestrator\packages\task-manager`. Затем можно запустить `orchestrator-tasks --project . list` или `orchestrator-tasks-web --project . --port 8765`.

Команда `orchestrator-tasks resources` показывает пути к полному гайду, контракту и [примеру skill](../../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md) в установленном пакете. В этом репозитории skill автоматически обнаруживается через [проектный указатель](../../.agents/skills/orchestrator-task-manager/SKILL.md). Во внешнем проекте агенту путь сообщает управляемый блок `AGENTS.md`, который добавляет онбординг.

Task Manager можно использовать и без онбординга, указав каталог целевого проекта. Его база локальна и не версионируется. Автоматического исполнения графа пока нет.
