# CLI Contract Migrations

## Unreleased

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
