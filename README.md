# AI Orchestrator

Универсальный, конфигурируемый оркестратор для управления навыками, workflow, задачами, памятью и проектным контекстом на разных агентных платформах и технологических стеках.

## Спецификации

- [Главная архитектурная спецификация](docs/specifications/orchestrator-specification-ru.md)
- [Спецификация уровня задач](docs/specifications/task-layer-specification-ru.md)

## Статус

Реализован контракт версии 1.2.0: создание и выполнение задач, проверки, approval gates, документация, target-owned Project Memory и Knowledge Graph, bounded context retrieval, аудит, backlog loop, профили адаптации и выборочная установка system/bundled/optional skills. Ограничения и порядок обновления описаны в [руководстве миграции](docs/migrations/1.2.md).

Текущая ветка дополнительно поддерживает risk-based execution routing, bounded evidence и локальную telemetry:

```powershell
python -m orchestrator telemetry --json
python -m orchestrator context --root . --mode standard --term task-manager
python -m orchestrator memory --root . list
python -m orchestrator knowledge --root . list
```
