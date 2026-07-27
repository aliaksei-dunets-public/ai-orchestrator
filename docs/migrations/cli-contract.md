# CLI Contract Migrations

## Unreleased

`orchestrator telemetry [--path PATH] [--json]` is an additive command that
summarizes optional local JSONL execution metrics. Existing Health Check and Task
Manager commands, output fields and exit codes are unchanged, so no consumer
migration is required.

An absent telemetry file returns a successful zero summary. Invalid JSONL fails
closed with a diagnostic error.
