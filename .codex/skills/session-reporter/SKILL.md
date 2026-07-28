---
name: session-reporter
description: Produce a compact session report from structured changes, checks, decisions, risks, and next actions; redact credentials before writing and omit empty sections. Use after task execution or a backlog loop stops.
---

# Session Reporter

After evidence is validated, build structured, secret-safe candidates with
`orchestrator.session_report.session_memory_candidates`. Candidates remain
proposals; never bypass source-authority or approval policy.

1. Collect only confirmed deltas from the current session.
2. Pass data to `orchestrator.session_report.render_session_report`.
3. Verify that secrets and empty sections are absent.
4. Save the report only after successful redaction.
5. Return the report path and a short summary; do not change Task Registry.
6. Invoke this skill once after execution or backlog stops. Persist session-derived
   memory only as idempotent proposals; because a session report is
   non-authoritative, never auto-promote its candidates and never retroactively
   change an already completed task status.
