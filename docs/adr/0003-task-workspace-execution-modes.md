# ADR 0003: Режимы workspace для выполнения задач

- Статус: accepted
- Дата: 2026-07-28

## Контекст

Последовательный Task Manager разрешал только одну активную задачу и один
изменяющий процесс. Простое увеличение числа активных задач смешивает
незакоммиченные изменения, checkpoints и Git-состояние одного workspace.

## Решение

Поддерживаются два режима:

- `serial` остаётся режимом по умолчанию и сохраняет прежний single-slot
  контракт;
- `isolated_parallel` требует `run_id`, `max_workers` и `worktree_root`.

В isolated run задача с `sequence=1` выполняется в main workspace. До её
успешного commit нельзя выделять следующие задачи. Задачи `sequence>=2`
получают уникальную ветку и Git worktree от проверенного commit первой задачи.

Task Registry хранит assignment: run, sequence, worker limit, workspace kind,
path, branch, base commit и commit evidence. Все registry mutations проходят
через bounded owner-aware lock. Execution freshness и checkpoint проверяются
относительно назначенного workspace.

Интеграция worktree-ветки выполняется явно. Конфликт, отсутствующий commit или
несовпадение ownership останавливают run. Failed worktree сохраняется для
восстановления. Cleanup запрещён для main и разрешён только после проверки
ownership manifest.

## Последствия

- В одном workspace по-прежнему допускается только один writer.
- Параллельность ограничена `max_workers` и требует Git CLI.
- Operational lock, worktrees и ownership metadata исключаются из Git.
- Для возврата к прежнему поведению достаточно выбрать `serial`; миграция
  существующих registry records не требуется.
