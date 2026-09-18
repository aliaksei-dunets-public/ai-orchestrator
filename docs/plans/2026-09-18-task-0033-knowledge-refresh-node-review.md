# Self-review TASK-0033 — KnowledgeRefreshNode

**Статус:** review подготовки; 2026-09-18. Это не пользовательская приёмка реализации.

План следует согласованному дизайну: обновление графа является отдельной Workflow Graph node и по умолчанию находится после work units, tests и final validation перед commit authorization. `auto` выбирает incremental code refresh, но не выполняет молчаливый full fallback. `full` требует explicit decision либо `authorization=automatic`, заданного для конкретной доверенной ноды.

Граница ответственности сохраняется: `ProjectKnowledgeService` владеет Graphify provider, snapshot, immutable artifacts и pointer; node владеет policy, моментом запуска, wait/resume и structured result; Task Manager и Git commit остаются внешними действиями. TASK-0020 API остаётся совместимым переходным слоем.

Проверяемые риски: повторное выполнение по CAS/wait identity, отказ provider с сохранением старого graph, stale source snapshot, попытка runtime-agent изменить authorization, automatic full только для доверенной node, и отсутствие новых semantic backends. План не включает документный semantic admission TASK-0031.
