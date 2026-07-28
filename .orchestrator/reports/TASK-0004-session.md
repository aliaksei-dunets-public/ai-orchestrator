# TASK-0004 English-first language migration

Migrated the project to an English-first canonical language while preserving Russian user documentation and historical baselines.

## Changes

- Added the repository language policy and 487-file inventory with English graph-source enforcement.
- Added English canonical specifications, bilingual guides and migrations, and Russian companion documents.
- Updated source authority, retrieval, task creation, task management, templates, skills, release metadata, and Health Check.
- Added contract and scenario coverage for bilingual documentation and English-only Knowledge Graph retrieval.
- Committed all staged changes as ead93b4.

## Validation

- 271 unittest tests passed.
- Strict Health Check passed with highest severity INFO and ok=true.
- Language inventory passed: 487 files inspected, 0 errors.
- Staged security gate passed with 0 deterministic findings.
- Staged diff check passed with 0 whitespace issues.

## Decisions

- English is the canonical project and Knowledge Graph language; Russian remains available for user-facing guides and instructions.

## Risks

- External scanners gitleaks, semgrep, osv-scanner, bandit, pip-audit, and trivy were unavailable in the local environment; deterministic repository security review passed.
- Session-derived memory proposals were not auto-promoted because the report is stored under the excluded operational tree.
