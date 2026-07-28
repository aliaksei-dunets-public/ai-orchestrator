# CLI Contract Migrations

## Unreleased

`claim-next` получил additive параметры `--mode`, `--run-id`,
`--max-workers`, `--worktree-root` и `--repository-root`. Без них сохраняется
прежний serial contract. Для isolated assignment `complete` требует
`--commit-evidence` и проверяет SHA против назначенного workspace.

Добавлены `assignment`/`cleanup` в Task Manager CLI и
`orchestrator workspace inspect|cleanup`. Новые стабильные exit codes:
`7 INVALID_EXECUTION_MODE`, `8 WORKSPACE_ERROR`, `9 REGISTRY_LOCKED`.
Legacy consumers, не включающие isolated mode, менять не требуется.

Task Context paths returned by Task Manager commands moved from
`.orchestrator/tasks/<TASK-ID>.md` to
`.orchestrator/tasks/contexts/<TASK-ID>.md`. Consumers must treat the returned
`context` field as authoritative instead of constructing the path from an ID.

Execution checkpoints now use
`.orchestrator/tasks/checkpoints/<TASK-ID>.checkpoint.lock`; the entire
`checkpoints/` directory must be ignored by Git. `complete` removes the
checkpoint after persisting `done` and may return `cleanup_warning` if cleanup
fails. `cancel` preserves it.

`orchestrator telemetry [--path PATH] [--json]` is an additive command that
summarizes optional local JSONL execution metrics. Existing Health Check and Task
Manager commands, output fields and exit codes are unchanged, so no consumer
migration is required.

An absent telemetry file returns a successful zero summary. Invalid JSONL fails
closed with a diagnostic error.

## 1.2 additive commands

`orchestrator memory --root ROOT {propose,approve,promote,disable,supersede,list}`,
`orchestrator knowledge --root ROOT {add-node,add-edge,rebuild,list}`, and
`orchestrator context --root ROOT [--mode MODE] [--budget-chars N]` are additive.
Domain failures return exit code 2 and a JSON object with `ok=false`; they do not
print a traceback. Successful operations return exit code 0 and `ok=true`.

Existing Health, telemetry, and Task Manager commands and exit codes remain
compatible. Context budgets default to 2048/6144/12288 characters for
quick/standard/deep routes.
