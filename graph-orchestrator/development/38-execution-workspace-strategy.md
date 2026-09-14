# Execution Workspace Strategy

**Status:** Accepted design v0.1  
**Scope:** Development Workflow — physical workspace / branch selection before Implementation

## 1. Core decision

For v1, the default Development execution strategy is:

```text
configured development branch
+
current repository workspace
```

No separate branch or Git worktree is created by default.

A dedicated task branch/worktree is created only when:

```text
the user explicitly requests it
or
a task/run configuration explicitly overrides the default
```

This keeps interactive development simple while preserving an isolation option when needed.

---

## 2. Position in workflow

```text
READY TASK
    ↓
CLAIM / START EXECUTION
    ↓
EXECUTION PREFLIGHT
    ↓
WORKSPACE RESOLUTION
    ↓
IMPLEMENTATION
```

Workspace resolution answers only:

> Where should this task be physically executed?

It does not decide whether the Plan is still valid. Plan/context freshness belongs to Execution Preflight.

---

## 3. Workspace strategies

Supported strategy enum:

```yaml
workspace_strategy:
  enum:
    - current_workspace
    - task_branch
    - task_worktree
```

### `current_workspace`

Use the configured Development branch in the current checkout.

This is the v1 default.

### `task_branch`

Create/switch to a task-specific branch in the current checkout.

Used only by explicit override.

### `task_worktree`

Create a task-specific branch and isolated Git worktree.

Used only by explicit override in v1.

---

## 4. Development branch

The orchestrator should not hard-code `main`.

Project Profile defines the primary development branch.

Candidate:

```yaml
development:
  workspace:
    development_branch: auto
```

Resolution order:

```text
Task override
→ Run override
→ Project Profile
→ repository default branch
```

Examples:

```text
main
develop
dev
master
```

`auto` means resolve from repository metadata / configured project conventions.

---

## 5. Default interactive behavior

For a normal chat / interactive execution:

```text
user does not mention workspace
        ↓
use configured development branch
        ↓
use current repository workspace
```

Do not ask:

> Which environment / branch / worktree should I use?

on every task.

User questioning is reserved for ambiguity or unsafe conditions.

---

## 6. Explicit user override

Examples:

```text
“Сделай это в отдельном worktree.”
“Создай отдельную ветку.”
“Работай в текущей feature branch.”
```

These become execution overrides.

Example:

```yaml
execution_override:
  workspace_strategy: task_worktree
```

or:

```yaml
execution_override:
  workspace_strategy: task_branch
```

The override applies to the execution run, not to the global project default unless explicitly requested.

---

## 7. Task-level override

A prepared Task may optionally contain:

```yaml
execution:
  workspace:
    strategy: inherit | current_workspace | task_branch | task_worktree
```

Default:

```yaml
strategy: inherit
```

`inherit` resolves through Project Profile.

This keeps Task preparation independent from one specific platform while allowing an explicit requirement when necessary.

---

## 8. Safety checks

Before Implementation, workspace resolution checks:

```text
repository exists
configured development branch exists/resolves
current branch
working tree status
untracked files
ongoing merge/rebase/cherry-pick
existing task branch/worktree
```

These checks do not automatically change user state.

---

## 9. Dirty workspace policy

Default safety behavior:

```yaml
dirty_workspace:
  auto_stash: false
  ask_when_unsafe: true
```

### Safe case

Current workspace is already on configured development branch and local changes are intentionally part of the current work context.

Project policy may allow continuation.

### Unsafe / ambiguous case

Examples:

```text
dirty workspace on another branch
ongoing merge/rebase
uncommitted changes that overlap task scope
branch switch would require stashing
```

Then:

```text
do not auto-stash
do not silently discard changes
ask user / block execution
```

---

## 10. Current branch differs from development branch

Default policy:

```text
clean workspace
→ switch to configured development branch if safe

dirty workspace
→ do not switch automatically
→ ask user
```

If the current branch was explicitly selected by the user for this run, it becomes the run override and may be used.

---

## 11. Deferred / executor-loop behavior

For v1, deferred execution does **not** automatically imply worktree isolation.

The same configured workspace policy applies:

```text
Task Executor Loop
      ↓
Project Profile workspace strategy
      ↓
current_workspace by default
```

If later practical usage shows that autonomous loops need stronger isolation, the default can be changed to `task_worktree` without changing the Development Workflow contract.

---

## 12. Workspace metadata

Execution Run should record the resolved workspace.

Example:

```yaml
execution_workspace:
  strategy: current_workspace

  repository_root: /project
  branch: develop

  base_revision: abc123
  start_revision: abc123

  dirty_at_start: false

  task_branch: null
  worktree_path: null
```

This gives Code Review, Testing, Final Check, and Health Check a stable reference.

---

## 13. Relationship with revision integrity

Workspace selection and revision validation are separate.

```text
Workspace Strategy
→ where execution happens

Execution Preflight
→ whether prepared artifacts are still valid

Final Check
→ whether accepted/reviewed/tested revision matches final candidate
```

Do not overload Workspace Manager with analysis freshness.

---

## 14. Cleanup

For `current_workspace`:

```text
no workspace cleanup required
```

For `task_branch` / `task_worktree`:

cleanup follows explicit policy after completion/merge/acceptance.

Candidate future configuration:

```yaml
cleanup:
  task_worktree_on_completed: remove
  task_branch_on_completed: keep
```

Not required for the default v1 path.

---

## 15. Accepted decisions

1. `current_workspace` is the v1 default.
2. Execution targets the configured primary Development branch.
3. No worktree is created automatically.
4. No workspace question is asked on every run.
5. User/task/run may explicitly override workspace strategy.
6. Dirty/unsafe workspace situations trigger a question/block rather than automatic stash.
7. `auto_stash` is disabled by default.
8. Deferred executor loops use the same default policy in v1.
9. Workspace metadata is recorded in Workflow Run state.
10. Worktree isolation remains a future policy change, not an architectural rewrite.
