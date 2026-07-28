# Worktree-Aware Task Execution Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Добавить выбор между последовательным выполнением и безопасным bounded parallel execution, где первая задача каждой parallel-сессии выполняется в основном workspace, а вторая и последующие — в отдельных Git worktrees.

**Architecture:** Task Manager сохраняет backward-compatible `serial` режим и получает `isolated_parallel` режим с явным run/group identity, cross-platform registry lock и workspace metadata. Parallel session сначала выполняет и коммитит первую задачу в main workspace, затем создаёт worktree/branch для каждой последующей задачи от нового validated `HEAD`; результаты проходят review и контролируемую интеграцию в main.

**Tech Stack:** Python 3.11+ standard library, Git CLI, JSON/JSON Schema, YAML workflows, Markdown, `unittest`, temporary sandbox repositories.

## Global Constraints

- `serial` остаётся default и сохраняет текущие Task Manager/API/CLI semantics.
- Нельзя выполнять две изменяющие задачи в одном workspace одновременно.
- Worktree paths, branch names, base commits и cleanup actions вычисляются и проверяются детерминированно; path escape и unsafe Git targets отклоняются.
- Registry writes сериализуются cross-platform lock; lock stale recovery не должна silently overwrite live work.
- Первая задача parallel run получает main workspace только после проверки чистого Git state; задача 2+ запускаются worktree-only после commit первой задачи.
- Каждая worktree-задача получает отдельный branch и checkpoint; operational metadata остаётся в ignored state, а Task Context и implementation commits — tracked.
- Merge/review конфликт останавливает run в `waiting_user` или `blocked`; автоматическое разрешение конфликтов не входит в scope.
- Не ослаблять security, freshness, approval, commit-per-task и documentation gates.

## Deliverables

- Конфигурация execution mode и bounded worker limits.
- Cross-platform registry lock и безопасный Worktree Manager.
- Task Registry metadata для run, sequence, workspace kind, branch, base commit и worktree path.
- Backlog/Execution workflow с фазами main bootstrap → worktree fan-out → review/integration.
- CLI/API для выбора режима, просмотра workspace assignment, cleanup и recovery.
- Contract/scenario/security/documentation tests и migration notes.

## Dependencies

- Existing Task Manager, Execution Runner and Backlog Loop phases.
- Existing `TASK-0003` Knowledge Curator onboarding work must remain isolated from this change.
- `TASK-0004` language migration may later translate the touched Russian canonical specifications; this task must preserve their current source-of-truth references until that migration completes.
- Git CLI available in the execution environment.

## Acceptance Criteria

- AC1: Default `serial` mode behaves exactly as today: one active task, main workspace, current status transitions and checkpoint semantics remain valid.
- AC2: `isolated_parallel` mode requires explicit `run_id`, `max_workers` and workspace root, validates bounds, and never allows concurrent writers in one workspace.
- AC3: The first claimed task in each isolated run is assigned `main`; it must pass freshness, clean-state and commit gates before task 2+ can start.
- AC4: Every task after the first receives a unique worktree and branch based on the post-bootstrap validated commit; assignments survive process restart and are recoverable from registry/checkpoint evidence.
- AC5: Registry mutations are serialized safely across processes, reject duplicate claims, preserve crash consistency and report stale/live lock states without silent data loss.
- AC6: A worktree task can run tests and create a commit independently; successful integration is explicit and conflict-safe, while conflict or missing commit evidence stops the run.
- AC7: Cleanup removes only validated task-owned worktrees/branches after completion or approved cancellation, preserves failed worktrees for recovery, and never deletes the main workspace.
- AC8: CLI, workflows, schemas, specifications, guides and Health Check agree on modes, assignment metadata, recovery and rollback; focused/full tests and strict Health pass.

## Testing Strategy

- Unit: mode validation, assignment state, branch/path sanitization, lock lifecycle, stale lock detection and cleanup guards.
- Contract: registry/schema fields, status transitions, CLI JSON, workflow ordering and backward-compatible serial behavior.
- Scenario: first-task main bootstrap, second+ worktree allocation, restart/recovery, bounded worker limits, duplicate claim, commit/integration conflict and cancellation cleanup.
- Sandbox integration: temporary Git repositories with real `git worktree add/remove`, branches and commits.
- Regression: existing Task Manager, Task CLI, Backlog Loop, Implementation Runner and Health suites.
- Security: path containment, branch injection, untrusted task titles, lock recovery and deletion target validation.

## Risks and Rollback

- Risk: task 2+ branches from an uncommitted or stale main state. Detection: clean-state/base-commit checks. Rollback: stop fan-out and remove only newly created worktrees.
- Risk: concurrent registry writers corrupt state. Detection: lock ownership/token and registry validation. Rollback: preserve the last valid registry and block recovery requiring user approval.
- Risk: merge conflict loses independent work. Detection: non-zero Git merge/check status. Rollback: keep the worktree/branch, restore main to its pre-integration commit and request manual integration.
- Risk: cleanup removes user data. Detection: canonical root/ownership manifest check. Rollback: cleanup is fail-closed; no deletion is attempted on mismatch.
- Risk: parallelism masks task-order dependencies. Detection: explicit dependency/run assignment validation. Rollback: fall back to serial mode for the run.

## Implementation Tasks

### Task 1: Execution mode, registry schema and configuration contract

**Files:**

- Modify: `config/defaults.yaml`
- Modify: `config/schemas/task-registry.schema.json`
- Modify: `orchestrator/task_manager.py`
- Create: `tests/contracts/test_parallel_execution_contract.py`
- Modify: `tests/unit/test_task_manager.py`

**Interfaces:**

- Consumes: `execution.mode`, `execution.max_workers`, `execution.worktree_root` and optional `run_id`.
- Produces: validated `serial`/`isolated_parallel` settings and per-task assignment metadata without breaking schema-version-1 serial records.

**Acceptance:** Serial remains the default; invalid mode, worker, run and workspace settings fail with stable JSON errors; registry validation accepts legacy records and validates new assignment fields.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest tests.contracts.test_parallel_execution_contract tests.unit.test_task_manager -v` passes.

- [ ] **Step 1:** Add failing contract tests for modes, limits, legacy records and assignment fields.
- [ ] **Step 2:** Run the focused command and confirm expected contract failures.
- [ ] **Step 3:** Implement configuration/registry validation with serial compatibility.
- [ ] **Step 4:** Run focused Task Manager and schema regression tests.
- [ ] **Step 5:** Record the accepted state model and pass it to Worktree Manager implementation.

### Task 2: Cross-platform registry lock and Worktree Manager

**Files:**

- Create: `orchestrator/registry_lock.py`
- Create: `orchestrator/worktree_manager.py`
- Create: `tests/unit/test_registry_lock.py`
- Create: `tests/unit/test_worktree_manager.py`
- Create: `tests/scenarios/test_worktree_sandbox.py`

**Interfaces:**

- `RegistryLock`: consumes task-root path and owner token; produces bounded acquire/release, live-owner and stale-lock outcomes.
- `WorktreeManager`: consumes repository root, validated task ID/title, run ID and base commit; produces task-owned path/branch assignment, status inspection and guarded cleanup.

**Acceptance:** Real temporary Git repositories can create and inspect worktrees, reject unsafe paths/branch names, preserve failed worktrees, and remove only validated task-owned resources. Lock tests cover contention, release, stale metadata and crash-safe cleanup.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest tests.unit.test_registry_lock tests.unit.test_worktree_manager tests.scenarios.test_worktree_sandbox -v` passes on the supported Windows environment.

- [ ] **Step 1:** Add failing sandbox cases for valid assignment, path escape, branch injection, contention and cleanup.
- [ ] **Step 2:** Implement platform-neutral lock abstraction with Windows/POSIX standard-library adapters and explicit owner metadata.
- [ ] **Step 3:** Implement Git worktree add/list/remove and branch ownership checks through bounded subprocess calls.
- [ ] **Step 4:** Run unit/sandbox tests twice and verify no task-owned artifacts escape the temporary repository.
- [ ] **Step 5:** Record command, commit, path and cleanup evidence for each sandbox lifecycle.

### Task 3: Task Manager assignment and claim semantics

**Files:**

- Modify: `orchestrator/task_manager.py`
- Modify: `orchestrator/task_cli.py`
- Modify: `tests/unit/test_task_manager.py`
- Modify: `tests/scenarios/test_task_cli.py`
- Create: `tests/scenarios/test_parallel_task_claim.py`

**Interfaces:**

- `claim-next` consumes mode/run/worker arguments and returns task ID, workspace kind/path, branch, base commit and sequence.
- Serial claims preserve `ACTIVE_TASK_EXISTS`; isolated claims allocate main for sequence 1 and worktree for sequence 2+ under registry lock.
- Status/complete/cancel consume assignment metadata and enforce workspace ownership and commit evidence.

**Acceptance:** Two or more isolated claims are possible without `MULTIPLE_ACTIVE_TASKS` registry errors, while serial claims retain the existing single-slot behavior. A second task cannot claim a worktree before the first task has a validated commit and updated base commit.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest tests.unit.test_task_manager tests.scenarios.test_task_cli tests.scenarios.test_parallel_task_claim -v` passes.

- [ ] **Step 1:** Add failing serial/isolated claim matrix and bootstrap ordering tests.
- [ ] **Step 2:** Implement locked assignment and sequence-aware transitions.
- [ ] **Step 3:** Add commit/base/workspace ownership checks to completion and cancellation.
- [ ] **Step 4:** Run focused Task Manager/CLI regression tests and restart scenarios.
- [ ] **Step 5:** Record evidence for main bootstrap, worktree fan-out and failure preservation.

### Task 4: Backlog and execution workflow integration

**Files:**

- Modify: `orchestrator/backlog.py`
- Modify: `orchestrator/execution.py`
- Modify: `workflows/backlog-loop.yaml`
- Modify: `workflows/task-execution.yaml`
- Modify: `tests/scenarios/test_backlog_loop.py`
- Modify: `tests/scenarios/test_implementation_runner.py`
- Create: `tests/scenarios/test_parallel_backlog_execution.py`

**Interfaces:**

- Backlog consumes execution mode and bounded worker limit; produces ordered phases: bootstrap task, commit gate, worktree fan-out, task execution, review/integration and cleanup.
- Execution consumes workspace assignment and runs freshness/checkpoint gates relative to that workspace; no step may silently switch workspace.

**Acceptance:** Serial backlog behavior remains unchanged. Isolated mode completes the first task in main, then can execute tasks 2+ in independently assigned worktrees, stops on waiting_user/blocked/conflict, and never exceeds `max_workers`.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_backlog_loop tests.scenarios.test_implementation_runner tests.scenarios.test_parallel_backlog_execution -v` passes.

- [ ] **Step 1:** Add failing workflow-order, worker-limit, restart and conflict scenarios.
- [ ] **Step 2:** Implement bootstrap/fan-out/integration state machine without changing serial callback behavior.
- [ ] **Step 3:** Bind execution freshness and checkpoints to the assigned workspace.
- [ ] **Step 4:** Run focused backlog/execution suites and inspect Git status in sandbox repositories.
- [ ] **Step 5:** Record stop/recovery evidence and send workflow changes to review.

### Task 5: CLI, Health, documentation and migration contract

**Files:**

- Modify: `orchestrator/cli.py`
- Modify: `orchestrator/health.py`
- Modify: `config/documentation-map.json`
- Modify: `tests/scenarios/test_health_cli.py`
- Create: `docs/adr/0003-task-workspace-execution-modes.md`
- Modify: `docs/specifications/task-layer-specification.md`
- Modify: `docs/specifications/orchestrator-specification.md`
- Modify: `docs/architecture/component-contracts.md`
- Create: `docs/migrations/1.3-task-workspaces.md`
- Modify: `docs/plans/2026-07-27-phase-19-backlog-loop.md`

**Interfaces:**

- CLI exposes explicit mode/run/worker/worktree inspection and cleanup results as JSON with stable exit codes.
- Health validates worktree ownership, registry lock metadata, active assignment bounds, base commits and stale operational paths.
- Documentation defines the first-task-main exception, worktree lifecycle, merge/recovery and serial fallback.

**Acceptance:** Users can select and inspect execution mode; Health reports unsafe assignments as errors; ADR/specs/migration and component contracts agree; local links and documentation impact checks pass.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest tests.scenarios.test_health_cli tests.contracts.test_specifications tests.unit.test_documentation -v` passes.

- [ ] **Step 1:** Add failing CLI/Health/documentation contract checks.
- [ ] **Step 2:** Implement mode selection, assignment inspection and stable diagnostics.
- [ ] **Step 3:** Document the approved architecture and 1.x migration/rollback path.
- [ ] **Step 4:** Run local-link, documentation-impact and Health checks.
- [ ] **Step 5:** Review user-visible behavior and record non-applicability for unchanged documentation owners.

### Task 6: Full acceptance and security evidence

**Files:**

- Create: `docs/validation/worktree-task-execution-report.md`
- Modify: `tests/acceptance/matrix.json`
- Modify: `tests/acceptance/test_release.py`
- Test: `tests/contracts/test_parallel_execution_contract.py`
- Test: `tests/scenarios/test_parallel_task_claim.py`
- Test: `tests/scenarios/test_parallel_backlog_execution.py`
- Test: `tests/scenarios/test_worktree_sandbox.py`

**Interfaces:**

- Consumes: implemented mode/config/lock/worktree/Task Manager/workflow/documentation changes.
- Produces: AC1–AC8 evidence, security findings, full regression status and strict Health result.

**Acceptance:** Full discovery, acceptance matrix, security review and strict Health pass with no `ERROR` or `CRITICAL`; serial regression remains green; sandbox worktrees and branches have no leaks after successful cleanup.

**Tests:** `\.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` and `\.\.venv\Scripts\python.exe -m orchestrator health --strict --json` pass.

- [ ] **Step 1:** Map AC1–AC8 to executable checks and sandbox evidence.
- [ ] **Step 2:** Run focused suites, full discovery, acceptance matrix and strict Health.
- [ ] **Step 3:** Run security review for path, branch, lock and cleanup boundaries.
- [ ] **Step 4:** Inspect serial compatibility and failed-worktree recovery manually.
- [ ] **Step 5:** Write validation report and hand the implementation to Task Review and Code Review.

## Rollback Procedure

If any assignment, lock, worktree or integration invariant fails, stop the run, preserve the failing worktree/branch and restore the main workspace to its last validated commit. Disable `isolated_parallel` in project configuration and continue in `serial` mode; remove only task-owned worktrees after their ownership manifest is verified.
