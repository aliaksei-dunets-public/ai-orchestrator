# Execution Workspace Policy

**Status:** Accepted v1 policy

## 1. Recommended Project Profile

```yaml
development:
  workspace:
    strategy: current_workspace
    development_branch: auto

    allow_run_override: true
    allow_task_override: true

    prompt_on_start: false

    dirty_workspace:
      auto_stash: false
      ask_when_unsafe: true

    isolated_execution:
      task_branch:
        enabled: true

      task_worktree:
        enabled: true
```

---

## 2. Resolution precedence

```text
Explicit user instruction
→ Workflow Run override
→ Task execution override
→ Project Profile
→ core default
```

Core default:

```yaml
strategy: current_workspace
development_branch: auto
```

---

## 3. User interaction policy

Do not ask the user to select a workspace when the default can be applied safely.

Ask only when:

```text
workspace is dirty and a safe branch switch is impossible
ongoing Git operation exists
requested branch/worktree conflicts with current repository state
configured development branch cannot be resolved
execution would risk overwriting/mixing unrelated changes
```

---

## 4. Explicit isolated execution

Example user instruction:

```text
“Выполни задачу в отдельном worktree.”
```

Resolved run configuration:

```yaml
development:
  workspace:
    strategy: task_worktree
```

This changes only the current run unless the user explicitly changes Project Profile policy.

---

## 5. Default branch resolution

If `development_branch: auto`:

```text
Project Profile known branch
→ repository default branch
→ current branch when repository has no resolvable default
```

The resolved branch should be persisted in Workflow Run metadata.

---

## 6. Safety

Never automatically:

```text
stash user changes
discard changes
reset branch
force checkout
delete branch/worktree containing unmerged work
```

unless a future explicit policy and authorization allows it.

---

## 7. Future evolution

Possible later defaults:

```text
interactive_default: current_workspace
executor_loop_default: task_worktree
```

This remains compatible with the v1 Workspace Strategy contract.
