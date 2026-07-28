# Changelog

## Unreleased

- Separated tracked Task Contexts into `.orchestrator/tasks/contexts/` and ignored execution checkpoints into `.orchestrator/tasks/checkpoints/`.
- Removed a task checkpoint after successful `done` persistence while preserving `cancelled` checkpoints for diagnostics.

## 1.1.0 — 2026-07-28

- Split canonical skills into system, bundled and optional distribution groups.
- Installed system and bundled skills by default while keeping optional skills behind explicit project approval.
- Added versioned optional selection and independent project-owned skill sources.
- Added atomic platform-projection synchronization with rollback, collision detection and Health Check coverage.
- Added technology-profile recommendations for optional skills without automatic installation.
- Added payload-free execution telemetry with JSONL storage and CLI summaries.
- Added deterministic evidence bounds with diagnostic tails, digests and artifact pointers.
- Added quick/standard/deep execution routing while keeping Security Review mandatory.
- Excluded release snapshots from default repository retrieval.
- Reduced the Python review entrypoint through progressive disclosure and bounded independent-review admission.
- Added a reproducible [token-efficiency validation report](docs/validation/token-efficiency-optimization-report.md).

## 1.0.0 — 2026-07-28

- Added portable task creation, execution, testing, review, approval, documentation, memory, audit, and backlog workflows.
- Added Codex, Google Antigravity, GitHub Copilot VS Code, and Claude VS Code capability profiles.
- Added explicit platform maturity and validation evidence: Codex is stable; three external adapters are experimental pending native smoke runs.
- Added Python and ABAP/RAP technology profiles and a 16-cell acceptance matrix.
- Integrated pinned `coding-discipline`, `security-gate`, `python-code-review`, and `optimizer` skills from the user-provided upstream skill repository.
- Added registry-driven Codex workspace skill installation with Health Check drift detection.
- Froze schema version 1 contracts for the stable compatibility window.
