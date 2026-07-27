# AI Orchestrator

Универсальный, конфигурируемый оркестратор для управления навыками, workflow, задачами, памятью и проектным контекстом на разных агентных платформах и технологических стеках.

## Спецификации

- [Главная архитектурная спецификация](docs/specifications/orchestrator-specification-ru.md)
- [Спецификация уровня задач](docs/specifications/task-layer-specification-ru.md)

## Статус

Реализован контракт версии 1.0.0: создание и выполнение задач, проверки, approval gates, документация, память, аудит, backlog loop и профили адаптации. Ограничения и порядок обновления описаны в [руководстве миграции](docs/migrations/1.0.md).

Текущая ветка дополнительно поддерживает risk-based execution routing, bounded evidence и локальную telemetry:

```powershell
python -m orchestrator telemetry --json
```
