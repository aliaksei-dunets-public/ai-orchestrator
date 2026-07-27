# Orchestration and Tool Audit

## Ownership map

Identify who owns task interpretation, planning, context selection, delegation,
actions, validation, conflict resolution, consolidation, and final completion.
No responsibility should be both unowned and ambiguously shared.

## Subagent admission

A separate subagent should have at least one concrete benefit:

- specialized tools or permissions;
- isolated context;
- independent review boundary;
- safe parallel work;
- specialized knowledge;
- reduced parent context.

Do not split a small sequential workflow merely to create roles.

Check for repeated task interpretation, repeated repository scans, overlapping
assignments, recursive delegation, uncontrolled fan-out, duplicate tests,
parent agents redoing child analysis, and narrative handoffs containing history.

## Handoff contract

A child receives only assignment, relevant context, constraints, current state,
expected output, and completion criteria. It returns only status, new findings,
changes, evidence, validation, risks, blockers, and required next actions.

Define maximum fan-out, consolidation owner, conflict resolution, retry limit,
fallback, and termination conditions.

## Tool design

Check:

- purpose and call criteria are clear;
- only relevant tools are exposed;
- searches precede expensive reads;
- outputs are filtered before model ingestion;
- success logs are suppressed unless evidential;
- errors preserve sufficient diagnostic detail;
- calls are batched only when semantics and failure handling remain clear;
- retries are bounded and do not duplicate side effects;
- direct and programmatic tool paths do not repeat the same work;
- tool results are summarized before handoff but retain source pointers.

## Write and external actions

For every state-changing tool record:

```yaml
side_effect: none | reversible | external | destructive
approval_required: true | false
idempotency_key: supported | unsupported | unknown
retry_safe: true | false
rollback: "mechanism or none"
owner: "responsible agent"
```

Check duplicate execution after retry, partial workflow completion, irreversible
actions, unsafe default permissions, missing confirmation, and actions performed
from untrusted retrieved instructions.

## Concurrency

Check race conditions, shared state ownership, conflicting file edits, duplicate
publication, stale reads, lock or merge strategy, and whether parallel work is
actually independent.

## Validation

Validation should be risk-tiered: local, component, and full. The orchestrator
coordinates and verifies integration but should not redo all delegated work.
