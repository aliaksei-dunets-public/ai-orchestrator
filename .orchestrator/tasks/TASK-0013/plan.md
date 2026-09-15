# План TASK-0013

1. Добавить миграцию схемы с таблицей tombstone и timestamp terminal-состояния.
2. Реализовать archive/unarchive/purge с retention в три календарных месяца и operation_id.
3. Скрыть архив по умолчанию в API/CLI и добавить просмотр архива в веб-панель.
4. Добавить тесты lifecycle, retention, физического удаления и tombstone.
5. Обновить контракт, README, usage, skill, project-status и worklog; затем пройти lifecycle задачи.
