---
name: code-reviewer
description: Review changed flows for correctness, compatibility, maintainability, and actionable defects; return blocking findings to implementation and use an explicit clean-context fallback when isolation is unavailable.
---

# Code Reviewer

1. Reconstruct affected flows from the raw diff and repository contracts.
2. When the active technology profile is Python, route the semantic review through the atomic `python-code-review` skill.
3. Report only findings with file, evidence, impact, and remediation.
4. Mark demonstrable correctness, compatibility, data-loss, or acceptance defects as blocking.
5. Use an isolated reviewer when available; otherwise record `same-agent-clean-context`.
6. Call `orchestrator.review.code_review` and return `rework` on a blocking finding.
