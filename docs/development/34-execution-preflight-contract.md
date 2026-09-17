# Execution Preflight — Architecture and Contract

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted design v0.2  
**Scope:** Validate a prepared Specification + Plan before Implementation starts

## 1. Purpose

Execution Preflight protects deferred tasks from implementing a stale approved Plan.

It is lightweight and deterministic-first.

It is not another Context/Analysis/Plan Review pass.

---

## 2. Inputs

```yaml
execution_preflight_request:
  task_ref: TASK-0042
  execution_package_ref: EXEC-PKG-0042-v2

  specification_ref: SPEC-0042-v1
  plan_ref: PLAN-0042-v2
  plan_review_ref: PLAN-REVIEW-0042-v2

  prepared_source_revision: abc123
  current_source_revision: xyz789

  project_profile_ref: PROJECT-PROFILE
```

---

## 3. Checks

```text
Execution Package matches Task
Specification hash/version matches approved binding
Plan hash/version matches approved binding
Plan Review approved that exact Spec+Plan pair
Task is executable/current
prepared/current source relationship is known
changed project areas since preparation are identifiable
no blocker invalidates execution
```

If source changed, compare delta against:

```text
Specification change surface
Plan file/object structure
Plan interfaces/contracts
```

---

## 4. Outcomes

```text
fresh
specification_refresh_required
replanning_required
needs_input
blocked
failure
```

### fresh

```text
→ Implementation
```

### specification_refresh_required

Relevant project truth may have changed enough to invalidate the durable Specification.

```text
→ Task preparing
→ Context / Analysis as needed
→ Specification Synthesis
→ Planning
→ Plan Review
→ new Execution Package
```

### replanning_required

Specification remains valid, but concrete Plan targets/order no longer match current project state.

```text
→ Planning against current Specification
→ Plan Review
→ new Execution Package
```

---

## 5. Change comparison example

```yaml
revision_delta:
  changed_paths:
    - docs/unrelated.md

  overlap_with_specification_surface: false
  overlap_with_plan_targets: false
```

Result:

```text
fresh
```

If `src/payment/service.py` changed and it is a Plan target, Preflight evaluates whether the Plan can be safely regenerated from the still-valid Specification or whether the Specification itself needs refresh.

---

## 6. Result contract

```yaml
execution_preflight_result:
  id: PREFLIGHT-0042-v2

  result:
    fresh | specification_refresh_required | replanning_required | needs_input | blocked | failure

  task_ref: TASK-0042
  execution_package_ref: EXEC-PKG-0042-v2

  prepared_source_revision: abc123
  current_source_revision: xyz789

  revision_changed: true
  relevant_overlap: false

  route:
    target: implementation
```

---

## 7. Immediate execution

Immediate mode still runs Preflight:

```text
package binding valid?
source revision unchanged?
no blocker?
→ fresh
```

This keeps immediate and deferred semantics identical.

---

## 8. Accepted decisions

1. Preflight validates the durable Spec+Plan handoff.
2. It does not require raw Context/Analysis.
3. Material project truth changes trigger Specification refresh.
4. Concrete target drift with stable requirements may trigger Planning only.
5. Any refresh produces a new approved binding before execution resumes.

---

## Workspace resolution

After preparation freshness checks pass, Execution Preflight resolves the physical execution workspace.

Default v1:

```yaml
workspace:
  strategy: current_workspace
  development_branch: auto
```

Resolution is delegated to the Execution Workspace Strategy.

Execution Preflight records the resolved branch/workspace in Workflow Run metadata.

Unsafe dirty-workspace conditions return:

```text
needs_input
or
blocked
```

rather than automatically stashing/discarding user changes.
