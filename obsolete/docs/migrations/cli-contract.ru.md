---
language: ru
translation_of: docs/migrations/cli-contract.md
---

# Миграции CLI-контракта

[English version](cli-contract.md)

Новые параметры `claim-next` для serial и isolated workspace являются
additive. Task Context теперь возвращается из `contexts/`, checkpoints — из
`checkpoints/`, а `complete` требует finalization receipt. Новые exit codes:
`7 INVALID_EXECUTION_MODE`, `8 WORKSPACE_ERROR`, `9 REGISTRY_LOCKED`.

```powershell
.\.venv\Scripts\orchestrator-task.exe finalize TASK-0003 `
  --request finalization.json --repository-root .
.\.venv\Scripts\orchestrator-task.exe complete TASK-0003 `
  --finalization-receipt .orchestrator/tasks/finalization/TASK-0003.json
```

Добавленные команды memory, knowledge, context и telemetry не изменяют старые
exit codes. Отсутствующий telemetry file даёт успешный нулевой summary.

```text
orchestrator telemetry [--path PATH] [--json]
```
