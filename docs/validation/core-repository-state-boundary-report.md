# Core Repository State Boundary Validation Report

## Scope

TASK-0008 establishes `.orchestrator/` as target-project-owned state. The
core repository now ignores and untracks its local state, while onboarding and
release packaging retain their separate target-state contracts.

## Evidence

- `git ls-files .orchestrator`: empty after index migration.
- Core boundary contract: passed; `.orchestrator/` is ignored and target
  onboarding remains selective for canonical memory and Knowledge Graph stores.
- Onboarding scenarios: passed, including fresh initialization, idempotency,
  rollback, graph indexing, and preservation of user instructions.
- Release acceptance: passed; rebuilt artifact contains no `.orchestrator`
  paths and managed upgrades preserve target state.
- Canonical workstation-path scan: zero matches.
- Strict Health Check: no `ERROR` or `CRITICAL` findings.
- Language policy with `--fail-on-errors`: passed.
- Documentation ownership, bilingual metadata, and local-link tests: passed.
- Read-only repository audit: no findings.
- Task review: approved; all acceptance criteria satisfied and no scope creep.
- Deterministic security review: approved; no unsafe construct or credential
  finding. External scanners were unavailable in this environment.

## Migration and rollback

Before untracking, the local state was snapshotted outside the repository at
`%TEMP%/ai-orchestrator-task-0008/orchestrator-state-before-untracking.zip`
with a SHA-256 manifest. The index migration used `git rm --cached`; no local
`.orchestrator` files or Git history were deleted or rewritten.

## Compatibility

Release construction continues to copy only the declared portable core
directories and files. Target onboarding keeps canonical memory and Knowledge
Graph files visible to Git and ignores only operational subtrees.
