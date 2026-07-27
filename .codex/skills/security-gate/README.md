# Security Gate Agent Skill

A portable Agent Skill for pre-commit, commit/range, pull-request, full-repository, and Git-history security reviews.

## Contents

- `SKILL.md` — core workflow and behavior.
- `references/review-checklist.md` — detailed vulnerability categories.
- `references/tooling.md` — safe scanner selection and commands.
- `references/severity.md` — severity, confidence, and gate policy.
- `references/report-template.md` — standardized output.
- `references/git-commands.md` — Git commands by mode.
- `references/sources.md` — authoritative maintenance references.
- `templates/pre-commit-config.yaml` — fast local secret gate using Gitleaks.
- `templates/github-security-controls.md` — CI enforcement checklist.
- `evals/trigger-cases.md` — positive and negative routing tests.
- `evals/scenarios.md` — functional evaluation scenarios with planted vulnerabilities.
- `evals/criteria.md` — scoring dimensions and pass thresholds.

## Recommended Use

Install the folder in the skills directory supported by the target agent. Invoke it before commit/merge and pair it with mandatory CI controls. The skill intentionally does not auto-install tools, execute project code, or auto-fix findings.
