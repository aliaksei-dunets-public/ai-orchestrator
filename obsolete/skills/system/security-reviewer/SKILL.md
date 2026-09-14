---
name: security-reviewer
description: Apply immutable security routing, threat-focused review, deterministic unsafe-pattern checks, and credential redaction before user handoff.
---

# Security Reviewer

1. Load the immutable policy from `config/policies/security.yaml`.
2. Route sensitive paths and content through `orchestrator.security.route_security_review`.
3. For `deterministic` depth, run the immutable pattern/credential checks without loading a semantic skill; escalate on any finding, sensitive path, unknown coverage, or failed check.
4. For `semantic` depth or an escalation, use the atomic `security-gate` skill for scoped scanner selection, exploit-path validation, coverage gaps, and its PASS/WARN/FAIL gate.
5. Normalize actionable results through `orchestrator.security.security_review`.
6. Redact credentials from evidence and reports.
7. Block handoff on critical or high findings; never accept a local bypass.
