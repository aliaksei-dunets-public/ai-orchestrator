# Knowledge Curator onboarding integration validation

**Date:** 2026-07-28
**Task:** `TASK-0003`
**Scope:** `knowledge_graph` proposal contract, onboarding preview/apply/rollback,
canonical `knowledge-curator` ownership, skill projections and documentation.

## Acceptance matrix

| Criterion | Evidence | Result |
|---|---|---|
| AC1 | `tests.scenarios.test_agent_led_onboarding`, graph proposal preview/hash | PASS |
| AC2 | `tests.scenarios.test_knowledge_bootstrap`, ontology/provenance/conflict checks | PASS |
| AC3 | onboarding apply/index/rollback scenario, deterministic rebuild | PASS |
| AC4 | existing onboarding suite and empty proposal idempotency | PASS |
| AC5 | canonical `skills/bundled/knowledge-curator/SKILL.md` and projection contract | PASS |
| AC6 | schema, docs, registry and documentation tests | PASS |
| AC7 | focused suites and full discovery | PASS |
| AC8 | strict Health, audit, skill drift and security gate | PASS |

## Test evidence

- Knowledge unit and bootstrap scenario: 5 tests passed.
- Onboarding scenario: 11 tests passed.
- Skill and lifecycle contract suites: 9 tests passed.
- Documentation suite: 5 tests passed.
- Full discovery: 209 tests passed.
- Acceptance matrix validation: passed through `orchestrator.testing.validate_test_plan`.
- Independent task review: approved; AC1-AC8 satisfied and no scope creep.
- Code review: approved; no blocking findings.
- Strict Health Check: no findings, highest severity `INFO`.
- Repository audit: no findings.
- Skill projections: zero drift after canonical installer regeneration.

## Behavioral result

Onboarding now accepts an optional schema-version-1 `knowledge_graph` proposal.
Core calculates source digests, validates ontology/provenance/effective endpoints,
merges stable IDs without silent overwrite, includes graph file changes in the
approved `plan_hash`, rebuilds ignored indexes and rolls graph changes back with
the rest of onboarding on validation failure. Missing or empty proposals remain a
valid no-op.

## Security gate

The staged scope was reviewed for proposal trust boundaries, path containment,
secret-like labels, unsafe deserialization, skill/agent routing and generated
artifact leakage. Deterministic unsafe-pattern and secret-pattern checks found no
blocking findings. Generic scanners unavailable in the environment remain a
coverage gap: gitleaks, semgrep, bandit, pip-audit, osv-scanner and trivy.
The change adds no dependencies, CI, IaC or container configuration.
