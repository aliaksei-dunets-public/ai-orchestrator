---
name: task-creator
description: Create and validate Task Context documents and executable plans from a user request, approved specification, or roadmap. Choose quick, standard, or deep mode; identify user decisions; define scope, acceptance criteria, tests, risks, and implementation steps. Use for roadmap decomposition, Task Manager registration preparation, plan audits, or handoff.
---

# Task Creator

## Memory and knowledge context

Before repository analysis in every quick, standard, or deep route, build a
fresh bounded context pack with
`orchestrator.task_creation.retrieve_task_creation_context`. An empty pack is a
valid no-op; never substitute stale or unbounded data.

Convert requirements into one or more self-contained Task Context documents and
plans. Do not implement the task or edit Task Registry; registration belongs to
Task Manager.

## Workflow

1. Read the normative requirements and relevant project files. Use
   `docs/specifications/task-layer-specification.md` and
   `docs/specifications/orchestrator-specification.md` as sources of truth.
2. Choose `quick` for obvious low-risk local work, `standard` for normal bugs
   and features, or `deep` for architectural, high-risk, ambiguous, or
   irreversible changes.
3. Separate goal from implementation, define included and excluded scope,
   dependencies, risks, and affected interfaces.
4. Record only decisions that cannot be inferred reliably. Deep work requires
   explicit approval of the selected approach before registration.
5. Split independent subsystems or phases into separate plans. Link plans to the
   canonical roadmap and state dependencies; do not create a parallel backlog.
6. Read [plan-format.md](references/plan-format.md) before writing a plan.
7. Read [task-context-contract.md](references/task-context-contract.md) before
   writing a context. Never put operational status in Task Context.
8. Self-review coverage, scope, placeholders, interface consistency, ordering,
   security impact, and documentation impact.
9. Run the validators:

```powershell
python .codex/skills/task-creator/scripts/validate_plan.py <plan> [<plan> ...]
python .codex/skills/task-creator/scripts/validate_task_context.py <context> [--draft|--registered]
```

10. Fix every validator error. If the user asks to register a task, hand the
    validated draft to Task Manager and never edit `tasks.json` directly.

## Result

Return created artifact paths, mode, dependencies, validation commands, and
unresolved user decisions. If there are none, explicitly say that no user
decisions are required.
