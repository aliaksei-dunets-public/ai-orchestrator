---
language: en
translation_of: README.ru.md
---

# AI Orchestrator

Portable, configurable orchestrator for skills, workflows, tasks, memory, and
Project Context across agent platforms and technology stacks.

## Specifications

- [Architecture specification](docs/specifications/orchestrator-specification.md)
- [Task Layer specification](docs/specifications/task-layer-specification.md)
- [Russian README](README.ru.md)

## Status

Version 1.2.0 contracts are implemented: task creation and execution, checks,
approval gates, documentation, target-owned Project Memory and Knowledge Graph,
bounded context retrieval, audit, backlog loop, adaptation profiles, and
selective system/bundled/optional skill installation. Constraints and upgrade
order are described in the [migration guide](docs/migrations/1.2.md).

The current branch also supports risk-based execution routing, bounded
evidence, and local telemetry:

```powershell
python -m orchestrator telemetry --json
python -m orchestrator context --root . --mode standard --term task-manager
python -m orchestrator memory --root . list
python -m orchestrator knowledge --root . list
```
