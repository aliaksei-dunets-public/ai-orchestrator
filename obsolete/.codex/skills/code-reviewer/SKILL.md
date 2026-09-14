---
name: code-reviewer
description: Review changed flows for correctness, compatibility, maintainability, and actionable defects; return blocking findings to implementation and use an explicit clean-context fallback when isolation is unavailable.
---

# Code Reviewer

1. Reconstruct affected flows from the raw diff and repository contracts.
2. Run only when the selected execution route includes `code-review`; quick low/medium-risk work is covered by tests and the mandatory Security Review fast path.
3. When the active technology profile is Python, pass task mode, risk and changed boundaries to the atomic `python-code-review` skill so it can load the smallest sufficient references.
4. Report only findings with file, evidence, impact, and remediation.
5. Mark demonstrable correctness, compatibility, data-loss, or acceptance defects as blocking.
6. Use an isolated reviewer only when the routed skill's admission contract requires it; otherwise stay in the current context.
7. Build only the bounded `ReviewerRequest` fields when independent review is
   admitted; the delegated reviewer is read-only and receives no conversation
   history, raw logs, secrets, or write-capable tools.
8. Call `orchestrator.review.code_review` and return `rework` on a blocking finding.
