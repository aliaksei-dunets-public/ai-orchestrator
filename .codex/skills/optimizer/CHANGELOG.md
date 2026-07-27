# Changelog

## 1.6.0 — 2026-07-15

- Added automatic user-facing report language selection.
- Made explicit user language instructions override request, source artifact, and prior-context languages.
- Added fallback to the latest substantive user request, then the most recent explicit user-facing language or configured default.
- Added mixed-language handling that excludes code, paths, identifiers, product names, and quotations from language inference.
- Preserved technical tokens and canonical machine schemas unless translation is explicitly requested.
- Added a multilingual regression fixture covering Russian automatic selection and Spanish explicit override.

## 1.5.0 — 2026-07-15

- Replaced the default multi-section audit report with four compact sections: important findings, changes, conditional questions, and metrics.
- Removed executive summary, execution model, scorecard, separate recommendations, and evaluation approach from standard output.
- Limited standard reports to five material root findings and quick reports to three, except for additional critical or high findings.
- Made deep analysis appendices explicitly opt-in and prohibited repeating the compact report.
- Added rules to omit empty questions and unavailable metric columns and to label estimated token values.
- Added an optimizer-report regression fixture.

## 1.4.0 — 2026-07-14

- Added output-contract auditing for concise but complete user and agent responses.
- Added consumer classification for user, orchestrator, peer-agent, machine, and artifact outputs.
- Added `compact`, `standard`, and `detailed` response-mode checks with explicit expansion conditions.
- Added analysis-depth versus output-length separation and prompt/runtime/schema/application placement guidance.
- Added compact delta-handoff patterns for subagents and unbounded-state detection.
- Added evaluation criteria for retained evidence, output tokens, repeated information, follow-up turns, and retries.
- Added two behavioral fixtures covering verbose user output and narrative subagent handoffs.

## 1.3.0 — 2026-07-14

- Added platform adapters for OpenAI Codex, Google Antigravity, GitHub Copilot in VS Code, and Claude Code for VS Code.
- Added explicit IDE-versus-CLI parity checks and thin-adapter guidance for multi-platform repositories.
- Added safe platform installation helper and documented canonical installation paths.
- Added non-interactive eval command profiles and a cross-platform eval runner with dry-run support.
- Added conservative sandbox, permission, persistence, budget, turn, and credit defaults where supported.
- Added four platform-focused behavioral fixtures.
- Extended validation to check platform metadata, command templates, JSON configs, install paths, and dangerous default flags.

## 1.2.0 — 2026-07-14

- Reduced the always-loaded `SKILL.md` and moved detailed checks behind a routing index.
- Added adaptive `quick`, `standard`, and `deep` report modes.
- Added explicit no-fabricated-findings and no-material-issue behavior.
- Added trust hierarchy, prompt-injection, permissions, and secret-exposure audit.
- Added write-tool side-effect, idempotency, rollback, approval, and concurrency checks.
- Added measurable token/cost/quality protocol and representative eval guidance.
- Added context selection, ordering, truncation, retrieval, and stale-state checks.
- Added confidence and evidence-type rubrics.
- Split OpenAI guidance into common and model-specific files with freshness metadata.
- Added provider/platform extension contract.
- Added self-test fixtures and a static skill validator.

## 1.1.0 — 2026-07-14

- Added eval-driven optimization and prompt/runtime separation.
- Added OpenAI GPT-5.4, GPT-5.5, and GPT-5.6 guidance.
- Added state, caching, compaction, and tool-output optimization checks.

## 1.0.0

- Initial optimizer audit skill.
