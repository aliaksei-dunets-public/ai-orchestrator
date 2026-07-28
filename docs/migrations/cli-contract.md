---
language: en
translation_of: docs/migrations/cli-contract.ru.md
---

# CLI contract migrations

## Unreleased

`claim-next` has additive `--mode`, `--run-id`, `--max-workers`,
`--worktree-root`, and `--repository-root` options. Without them the previous
serial contract remains unchanged. In isolated mode, `complete` requires
`--commit-evidence` and verifies the SHA against the assigned workspace.

Task Manager adds `assignment` and `cleanup`; `orchestrator workspace` adds
`inspect` and `cleanup`. Stable exit codes are `7 INVALID_EXECUTION_MODE`,
`8 WORKSPACE_ERROR`, and `9 REGISTRY_LOCKED`. Legacy consumers do not need a
migration unless they opt into isolated mode.

Task Context paths are under `.orchestrator/tasks/contexts/` and checkpoints are
under `.orchestrator/tasks/checkpoints/`. Consumers must use the returned
`context` field rather than derive paths from task IDs. The checkpoint directory
must be ignored by Git.

Completion requires finalization followed by completion:

```powershell
.\.venv\Scripts\orchestrator-task.exe finalize TASK-0003 `
  --request finalization.json --repository-root .
.\.venv\Scripts\orchestrator-task.exe complete TASK-0003 `
  --finalization-receipt .orchestrator/tasks/finalization/TASK-0003.json
```

`complete` removes the checkpoint after persisting `done` and may return a
`cleanup_warning`; `cancel` preserves it. Historical `done` records without a
finalization field remain readable, while a new completion without a receipt
returns `FINALIZATION_REQUIRED`.

Telemetry is additive:

```text
orchestrator telemetry [--path PATH] [--json]
```

An absent telemetry file returns a successful zero summary. Invalid JSONL fails
closed with a diagnostic error.

## 1.2 additive commands

`orchestrator memory --root ROOT {propose,approve,promote,disable,supersede,list}`,
`orchestrator knowledge --root ROOT {add-node,add-edge,rebuild,list}`, and
`orchestrator context --root ROOT [--mode MODE] [--budget-chars N]` are additive.
Domain failures return exit code `2` and `{ "ok": false }`; successful
operations return exit code `0` and `{ "ok": true }`. Context budgets are
2048/6144/12288 characters for quick/standard/deep routes.
