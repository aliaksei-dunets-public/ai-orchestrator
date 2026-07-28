# Serial Execution Branch Policy Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Make the serial execution contract explicitly require use of the current branch in the primary workspace, without creating, switching to, merging, or cleaning up a task branch or Git worktree.

**Architecture:** The Task Manager already enforces the runtime boundary: serial claims have no assignment and only `isolated_parallel` allocates task-owned worktrees. This change makes the missing agent-facing boundary declarative in the workflow and canonical implementation skill, then protects it with a cross-artifact contract test. It deliberately does not add runtime Git state, force `main`, or alter isolated-parallel allocation and integration.

**Tech Stack:** Python 3.11 standard-library `unittest`, UTF-8 Markdown, YAML workflow descriptors, canonical skill distribution through `orchestrator.skill_installer`.

## Global Constraints

- Keep `serial` on the user-selected current branch in the primary workspace; “primary workspace” does not mean forcibly checking out `main`.
- In serial mode, forbid agent-initiated `git switch`, `git checkout -b`, task-branch creation, `git worktree add`, merge, integration, and worktree cleanup.
- Preserve the existing `TaskManager` and `WorktreeManager` behavior and the complete `isolated_parallel` lifecycle.
- Edit only canonical `skills/` sources; regenerate `.codex/skills/` and `.agents/skills/` through the registered skill installer.
- Do not commit Task Registry state, lock files, generated temporary files, or an agent-created branch.
- A declarative contract controls orchestrator-managed agents. It is not a host-level prohibition on a user or external Git client.

## Deliverables

- Explicit serial branch-policy fields in `workflows/task-execution.yaml` and `workflows/backlog-loop.yaml`.
- Canonical serial/isolated Git-operating rules in `skills/bundled/implementation-runner/SKILL.md`.
- Regenerated managed skill projections that match the canonical skill.
- A regression contract test that detects weakening of the serial policy while confirming isolated-parallel remains the only task-owned-worktree route.
- Updated canonical task/workspace documentation, with one explicit documentation disposition for every document mapped from the changed workflow paths.

## Dependencies

- TASK-0004 English-first migration is complete; canonical documentation is English.
- TASK-0005 workspace-aware execution and TASK-0006 finalization enforcement remain the runtime and completion baselines.
- TASK-0007 analysis revision 1, baseline `e92970d`, and the fresh bounded retrieval pack are the planning evidence.

## Acceptance Criteria

1. The serial workflow states that it uses the current branch and primary workspace, and forbids creation or switching of task branches and worktrees.
2. The canonical Implementation Runner gives the same serial rule before execution and limits task-owned branches, integration, and cleanup to explicit `isolated_parallel` assignments.
3. Serial runtime behavior remains assignment-free and no runtime code adds a Git branch or worktree lifecycle; isolated-parallel behavior remains unchanged.
4. An executable regression contract test covers criteria 1–3 and the managed projections remain free of drift.
5. Canonical documentation describes the current-branch serial policy accurately; every document mapped by `config/documentation-map.json` receives an `updated` or evidence-backed `not_applicable` disposition.
6. The finalization receipt is current and records test, documentation, knowledge, and memory outcomes before TASK-0007 is completed and committed.

## Testing Strategy

- Regression contract: add a focused `unittest` module that reads the declarative workflow and canonical skill and asserts the serial prohibitions plus the unchanged isolated route.
- Existing contract coverage: run the workspace execution and skill-distribution contracts to preserve the serial default, assignment schema, and projection ownership.
- Documentation checks: validate local links for updated canonical documents and run the documentation/Health checks required by the repository.
- Task checks: validate the registered context, implementation plan, Task Registry, and finalization receipt.

## Risks and Rollback

- **Policy text drifts from a projection:** detect with skill-distribution contract; restore the canonical skill text and regenerate both projections through the installer.
- **Serial wording accidentally forces `main`:** detect with the regression contract’s current-branch assertion; revert the declarative policy change without touching runtime state.
- **Isolated lifecycle is weakened:** detect with the same contract and existing parallel-execution suites; restore the isolated-only statements.
- **Documentation overstates host-level enforcement:** detect in review against the stated boundary; revise docs to say the policy governs orchestrator-managed agents only.

## Implementation Tasks

### Task 1: Declare the serial branch boundary

**Files:**

- Modify: `workflows/task-execution.yaml:workspace_assignment`
- Modify: `workflows/backlog-loop.yaml:steps.serial`
- Test: `tests/contracts/test_serial_execution_branch_policy.py`

**Interfaces:**

- Consumes: execution mode selected by `TaskManager.ExecutionSettings` and the existing workflow descriptors.
- Produces: machine-readable statements that serial uses `current-branch` in `primary-workspace`, with task branch/worktree operations forbidden; isolated-parallel retains its existing assignment lifecycle.

**Acceptance:**

- No serial descriptor claims a task branch, task-owned worktree, integration, or cleanup step.
- The policy does not prescribe `git checkout main` and does not change runtime Python modules.

**Tests:**

- [ ] **Step 1:** Add failing assertions for the missing serial current-branch and forbidden-operation fields.
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_serial_execution_branch_policy` and confirm the expected failure.
- [ ] **Step 3:** Add the minimal workflow declarations and make the assertions pass.
- [ ] **Step 4:** Run `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_serial_execution_branch_policy tests.contracts.test_parallel_execution_contract` and confirm isolated assertions remain green.
- [ ] **Step 5:** Record the workflow change for documentation and review.

### Task 2: Make the execution skill enforce the boundary

**Files:**

- Modify: `skills/bundled/implementation-runner/SKILL.md`
- Regenerate through installer: `.codex/skills/implementation-runner/`
- Regenerate through installer: `.agents/skills/implementation-runner/`
- Modify: `tests/contracts/test_serial_execution_branch_policy.py`
- Test: `tests/contracts/test_skill_distribution_contract.py`

**Interfaces:**

- Consumes: the active execution mode and an optional Task Manager assignment.
- Produces: an instruction that serial agents retain the current branch, perform neither manual branch/worktree lifecycle nor integration, and that isolated agents use only a registered assignment.

**Acceptance:**

- The canonical skill names the forbidden serial Git operations and explicitly preserves a user-selected branch.
- The canonical skill assigns branch/worktree creation, merge, integration, and cleanup only to the explicit isolated route.
- Generated projections are regenerated, never hand-edited, and have no drift.

**Tests:**

- [ ] **Step 1:** Extend the policy contract with failing canonical-skill assertions.
- [ ] **Step 2:** Run the new contract and confirm the skill assertions fail before editing the source.
- [ ] **Step 3:** Make the smallest canonical skill change and regenerate projections with `orchestrator.skill_installer.install_registered_skills` for the `.codex/skills` and `.agents/skills` destinations.
- [ ] **Step 4:** Run `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_serial_execution_branch_policy tests.contracts.test_skill_distribution_contract` and confirm both pass.
- [ ] **Step 5:** Capture the installer output and drift result as task evidence.

### Task 3: Align canonical documentation and dispositions

**Files:**

- Modify: `docs/specifications/orchestrator-specification.md:workspace-aware execution`
- Modify: `docs/specifications/task-layer-specification.md:serial and isolated execution`
- Modify: `docs/migrations/1.3-task-workspaces.md:serial mode`
- Modify: `docs/adr/0003-task-workspace-execution-modes.md:decision and consequences`
- Modify when the workflow descriptor is documented there: `docs/architecture/component-contracts.md`
- Review for disposition: `docs/migrations/cli-contract.md`, `docs/migrations/1.4-task-finalization.md`, `docs/adr/0004-task-finalization-receipts.md`, `docs/guides/memory-and-knowledge.md`, and `docs/guides/memory-and-knowledge-ru.md`

**Interfaces:**

- Consumes: the declared serial policy, existing public workflow contract, and `config/documentation-map.json`.
- Produces: canonical documentation distinguishing the primary workspace from a forced branch and limiting task-owned Git lifecycle to isolated execution.

**Acceptance:**

- Updated documents agree with the workflow and canonical skill.
- `cli-contract`, finalization, and memory/knowledge documents are either updated only if their public contract changes or recorded as `not_applicable` with the precise reason that no CLI, finalization, or retrieval contract changed.

**Tests:**

- [ ] **Step 1:** Run Documentation Manager impact analysis for the changed workflow paths and create the full disposition list.
- [ ] **Step 2:** Update only the affected canonical documents; do not modify generated projections or Russian companions except where a mapped owner document requires it.
- [ ] **Step 3:** Run `.\.venv\Scripts\python.exe -m unittest tests.unit.test_documentation tests.contracts.test_specifications` and confirm success.
- [ ] **Step 4:** Run the local-link validation using `orchestrator.documentation.broken_local_links` for every updated document and confirm an empty result.
- [ ] **Step 5:** Attach the full `updated`/`not_applicable` disposition set to finalization.

### Task 4: Verify, finalize, and close without a serial branch

**Files:**

- Modify: `docs/plans/2026-07-28-serial-execution-branch-policy.md:execution evidence` only if the plan requires a completed evidence note.
- Create through Task Finalization: `.orchestrator/tasks/finalization/TASK-0007/receipt.json`
- Do not commit: `.orchestrator/tasks/tasks.json` or locks.

**Interfaces:**

- Consumes: changed-path inventory, contract-test results, documentation dispositions, and explicit Knowledge Curator and Memory Manager proposals.
- Produces: a ready, current finalization receipt bound to TASK-0007’s registered context and checkpoint.

**Acceptance:**

- Focused regression and affected existing contracts pass.
- Health Check has no `ERROR` or `CRITICAL`.
- The receipt has no missing, stale, or pending-approval gate; task completion and commit happen from the current serial branch without merge or worktree cleanup.

**Tests:**

- [ ] **Step 1:** Run the focused tests from Tasks 1–3 plus `.\.venv\Scripts\python.exe -m unittest tests.contracts.test_parallel_execution_contract tests.contracts.test_skill_distribution_contract tests.unit.test_documentation tests.contracts.test_specifications`.
- [ ] **Step 2:** Run `.\.venv\Scripts\python.exe .codex\skills\task-creator\scripts\validate_plan.py docs\plans\2026-07-28-serial-execution-branch-policy.md` and validate the registered TASK-0007 context.
- [ ] **Step 3:** Run the repository Health Check and `orchestrator-task validate`; stop if either reports an error-level finding.
- [ ] **Step 4:** Invoke Task Finalization with the documentation dispositions, a knowledge proposal stating whether the durable workflow-policy relation is added, and secret-safe memory candidates.
- [ ] **Step 5:** Verify the receipt is ready and current, then commit only the approved task artifacts on the current branch and mark TASK-0007 done.
