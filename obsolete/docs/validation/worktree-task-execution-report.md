# Worktree-aware task execution validation

**Date:** 2026-07-28
**Task:** `TASK-0005`
**Scope:** serial compatibility, isolated parallel assignments, registry lock,
Git worktree lifecycle, bounded backlog execution, CLI, Health and docs.

## Acceptance matrix

| Criterion | Evidence | Result |
|---|---|---|
| AC1 | 27-test pre-change serial baseline and existing Task Manager/backlog suites | PASS |
| AC2 | execution settings contract, unique active workspace and worker-limit tests | PASS |
| AC3 | main bootstrap clean-state and commit gate scenario | PASS |
| AC4 | real Git sandbox, unique task worktrees and restart recovery | PASS |
| AC5 | owner-aware lock contention/stale recovery and atomic registry tests | PASS |
| AC6 | independent worktree commit, explicit integration and conflict/missing-evidence stops | PASS |
| AC7 | ownership manifest, clean/merged branch and main-preservation cleanup guards | PASS |
| AC8 | CLI/Health/schema/workflow/docs checks, full discovery and strict Health | PASS |

## Test evidence

- Serial baseline: 27 tests passed before implementation.
- Focused execution/lock/worktree/claim/workflow/CLI/Health suites: 45 tests passed.
- Review regressions: 25 tests passed, including early cleanup, invalid transition,
  uncommitted branch and unintegrated branch protection.
- Full discovery: 232 tests passed after reproducible release artifact rebuild.
- Strict Health: no findings, highest severity `INFO`.
- Repository audit: no findings.
- Documentation impact resolved and affected local links valid.

## Behavioral result

`serial` remains the default and preserves the existing active-slot contract.
An `isolated_parallel` run requires explicit run, worker and worktree settings.
Sequence 1 is assigned to a clean main workspace and must provide verified commit
evidence before sequence 2+ receives unique branches and worktrees. Registry
mutations are lock-serialized. Execution checkpoints are workspace-bound.
Integration is explicit; conflicts and missing evidence stop the run. Failed or
dirty worktrees are preserved, while successful cleanup requires matching
ownership and an integrated clean branch.

## Review and security

Code review and task review are approved after regression fixes. The staged
security gate found no blocking or warning findings in command construction,
path containment, branch identity, lock recovery, commit verification or cleanup
ownership. Git is invoked with argument arrays and bounded timeouts; task titles
never enter paths or commands. No dependencies, CI, IaC or container settings
were added.

Generic scanners were unavailable and remain a coverage gap: gitleaks, semgrep,
bandit, pip-audit, osv-scanner and trivy. A staged deterministic secret/unsafe
pattern scan found no credential material or unsafe dynamic/shell execution; one
synthetic owner-token fixture was reviewed as non-secret test data.
