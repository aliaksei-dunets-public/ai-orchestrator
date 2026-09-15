# Контекст проекта: Orchestrator

## Назначение

Платформенно-независимый графовый оркестратор разработки. Этот репозиторий одновременно является ядром и целевым проектом; система развивается поэтапно на основе материалов docs/.

## Команды проверок

- .venv/Scripts/python.exe -m unittest discover -s tests
- .venv/Scripts/python.exe -m unittest discover -s packages/task-manager/tests
- .venv/Scripts/python.exe -m unittest discover -s packages/onboarding/tests

## Ограничения

- Состояние задачи принадлежит Task Manager Service, состояние запуска — Graph Runtime.
- Сохранять границу подготовки, ready и исполнения и контракты структурированных артефактов.
- Не импортировать, не запускать и не изменять архив obsolete/ при реализации новой системы.
- Использовать публичный API пакета orchestrator-task-manager, не менять SQLite напрямую.
- Документацию и пользовательские инструкции писать на русском языке.
