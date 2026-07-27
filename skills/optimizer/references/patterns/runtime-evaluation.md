# Runtime and Evaluation Patterns

## Correct control layer

- prompt: goals, decision policy, behavior, tool-use criteria;
- structured schema: machine-validated result shape;
- runtime: model, reasoning effort, verbosity, token/tool limits, caching;
- application: authorization, secrets, idempotency, approvals, rollback;
- state/retrieval: reusable facts, source pointers, context selection.

Do not use long natural-language rules to compensate for controls enforceable by
the runtime or application.

## Response modes

Use compact output for agent handoffs, standard output for normal users, and
detailed output only for formal audits or complex decisions. Reasoning depth and
answer verbosity should be configured independently where supported.

## Soft budgets

Budgets may include context files, search results, subagent fan-out, retries,
and response mode. Permit justified exceptions for correctness, security, or
insufficient evidence and record the reason.

## Controlled experiment

Preserve baseline, change one variable, rerun the same representative cases,
compare success and tail metrics, then retain or roll back. Do not combine prompt
compression, model migration, and tool redesign in one unmeasurable change.

## Migration

Start from a clean baseline for the target model where practical. Reintroduce
legacy scaffolding only when eval evidence shows a need. Separate model-specific
instructions from universal behavior.

## Structured outputs

Prefer an enforceable schema for machine-consumed responses. Keep semantic
requirements in instructions and field constraints in the schema. Validate
schema failures separately from task-quality failures.
