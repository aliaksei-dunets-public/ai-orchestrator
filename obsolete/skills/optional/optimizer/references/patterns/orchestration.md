# Orchestration Patterns

Apply only when the diagnosed problem justifies them.

## Admission control

Delegate only for specialized tools, permissions, knowledge, context isolation,
independent review, or genuinely independent work.

## Bounded fan-out

Define maximum parallel agents, non-overlapping assignments, shared-state
contract, result schema, consolidation owner, conflict resolution, and stop
conditions.

## Coordinator, not duplicate worker

The orchestrator classifies, selects context, delegates, tracks state, resolves
conflicts, validates integration, and consolidates. It repeats child analysis
only when evidence conflicts, risk is high, or targeted verification is needed.

## Independent review

Give reviewers requirements, changed artifacts, constraints, and validation
results—not the implementer's persuasive narrative. Reviewers report blocking
issues, non-blocking issues, gaps, and approval status.

## Compact handoff

```yaml
status: completed | partial | blocked | failed
summary: "one to three sentences"
new_findings: []
changes: []
validation: {}
risks: []
blockers: []
next_actions: []
```

Omit empty fields and unchanged history.

## Tiered validation

Use focused checks for local changes, component checks for affected boundaries,
and full regression only when scope or risk warrants it.

## Stop and escalation

Stop on measurable completion evidence. Escalate for security, data loss,
conflicting requirements, insufficient evidence, significant architecture
change, or unresolved tool failure. Bound retries and recursive delegation.
