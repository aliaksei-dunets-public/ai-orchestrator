# ADR-0001: Границы Core и источники истины

**Статус:** принято

## Контекст

Оркестратор должен работать на нескольких агентных платформах и технологических стеках. Смешение project state, platform adapters и orchestration logic сделает переносимость непроверяемой.

## Решение

- `orchestrator/` содержит platform-neutral runtime.
- `skills/` является каноническим source навыков; platform-каталоги являются устанавливаемыми проекциями.
- `registries/` связывает логические identifiers с существующими артефактами.
- `profiles/` описывает возможности платформ и стеков, но не изменяет Core.
- `docs/specifications/orchestrator-specification-ru.md` определяет архитектуру и roadmap.
- `docs/specifications/task-layer-specification-ru.md` определяет контракты Task Layer.
- `.orchestrator/tasks/tasks.json` является локальным operational state и не хранится в Git.
- Task Context и Execution Record остаются версионируемыми.

Контракты изменяются через новую revision спецификации, migration note и regression/contract tests. Immutable security policies имеют приоритет над любым локальным слоем.

## Последствия

Core зависит от capabilities, а не от названий платформ. Новая platform integration обязана реализовать общий contract и пройти acceptance suite, прежде чем станет стабильной.

## Откат

До появления зависимого runtime-кода ADR можно заменить новым решением. После публикации контракта несовместимое изменение требует superseding ADR и migration.
