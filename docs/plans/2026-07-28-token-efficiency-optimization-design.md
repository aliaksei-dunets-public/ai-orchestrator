# Token-Efficiency Optimization Design

Date: 2026-07-28

## Decision

The audit findings OPT-001 through OPT-005 are accepted as one optimization
change-set. Three approaches were considered:

1. Prompt-only compression is the smallest edit, but it cannot measure total
   system cost and leaves unbounded runtime evidence unchanged.
2. Runtime-first optimization adds telemetry and deterministic bounds before
   changing routing. This is the selected approach because later savings become
   measurable and correctness gates remain explicit.
3. A separate telemetry service would provide richer analytics, but adds an
   external dependency and operational complexity that are unjustified for the
   single-developer 1.x runtime.

## Architecture

The runtime gains a platform-neutral telemetry contract and an optional JSONL
sink. Events contain counters and identifiers only: duration, attempts,
retries, tool calls, agent handoffs and provider-reported token usage. Prompts,
tool output and evidence text are never copied into telemetry. The default
operational path is `.orchestrator/telemetry/events.jsonl`, which remains
outside Git.

Execution evidence remains backward-compatible as strings for public callers,
but every stored value is bounded. Oversized evidence keeps a compact head,
diagnostic tail, original character count and SHA-256 digest; callers may add a
source or artifact pointer. Short evidence remains byte-for-byte unchanged.

Execution routing is selected by task mode and risk rather than one unconditional
semantic pipeline. Freshness, implementation, tests and Security Review remain
mandatory. Quick low-risk work skips semantic Task Review and Code Review;
standard work includes both; deep or high-risk work additionally requires
independent review. Approval and documentation steps are included only when
their impact flags require them.

Repository search excludes `releases/` by default because the release artifact
duplicates canonical sources. Release validation addresses that directory
explicitly. The Python review skill becomes a small routing entrypoint; detailed
review phases move behind conditional references, and independent review is
admitted only for defined risk boundaries.

## Failure behavior and compatibility

Telemetry is observational: a disabled sink changes no behavior, while a sink
write failure is reported without silently corrupting execution state. Negative
or inconsistent counters fail validation. Existing short `StepOutcome`
construction and checkpoint loading remain compatible.

Security is never skipped. Quick mode uses the same immutable security gate with
a fast deterministic pass and escalates to semantic review on a finding or
security-sensitive change. Existing release artifacts remain reproducible after
canonical sources and projections are synchronized.

## Acceptance and measurement

- Telemetry events are schema-valid, contain no evidence text and aggregate
  provider-reported usage when available.
- Evidence size is deterministic and bounded while preserving a diagnostic tail
  and optional pointer.
- Quick, standard and deep workflow selections have direct scenario tests;
  Security Review is present in every route.
- Default `rg` search does not traverse `releases/`; explicit release checks
  still work.
- The Python review entrypoint is materially smaller and routes detailed
  procedures by review mode/risk.
- Full regression, strict 16-cell workspace/release matrices, Health Check,
  audit, skill drift and release-manifest checks pass.

Baseline static evidence is recorded before edits; exact token savings remain
unavailable until provider usage is supplied through the new telemetry contract.
