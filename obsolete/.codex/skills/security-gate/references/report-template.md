# Security Gate Report

## Gate

**PASS | WARN | FAIL**

One-sentence reason.

## Scope

- Mode: staged | working-tree | commit | range/PR | full | history-secrets
- Target: `<commit/range/paths>`
- Reportable scope: changed lines/files or full repository
- Context inspected outside scope: `<brief description or none>`

## Coverage

| Category | Method/tool | Result | Notes |
|---|---|---|---|
| Secrets | ... | Completed / Findings / Skipped | ... |
| SAST | ... | ... | ... |
| Dependencies | ... | ... | ... |
| IaC/CI/containers | ... | ... | ... |
| Contextual data flow | AI/manual | Completed | ... |

## Blocking Findings

| ID | Severity | Confidence | CWE / OWASP | Location | Finding | Exploit path and impact | Remediation |
|---|---|---|---|---|---|---|---|

Use redacted evidence only. Omit the table when empty and state: **No blocking findings detected within the defined scope and coverage.**

### Detailed Finding Format

For each blocking finding, expand below the table:

- **ID / Title**
- **Severity / Confidence**
- **CWE / OWASP** (when applicable)
- **Location:** exact file and line/range
- **Evidence (redacted)**
- **Source → Sink:** attacker-controlled source and dangerous sink
- **Exploit path:** realistic prerequisites and steps
- **Impact**
- **Remediation:** specific, minimal fix addressing root cause
- **Regression test:** recommended test to prevent reintroduction

## Needs Verification

| ID | Suspected severity | Location | Missing evidence | Verification step |
|---|---|---|---|---|

Omit when empty.

## Remediation Order

1. **Immediate:** credential rotation, active exploitation containment, or Critical fixes.
2. **Before merge:** all FAIL findings and required regression tests.
3. **Follow-up:** WARN findings, coverage gaps, hardening, and CI enforcement.

## Residual Risk

One concise statement explaining what the review did not prove or cover.
