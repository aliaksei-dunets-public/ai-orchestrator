# System Analysis Reference

Use this reference for non-trivial change reviews, component reviews, and
project audits. It provides investigation techniques, not a mandatory checklist.
The reviewer should adapt them to the codebase and continue beyond them when the
system suggests other important questions.

## 1. Reconstruct Architecture from Executable Reality

Documentation is useful but may be incomplete or stale. Confirm architecture in
code by locating:

- entry points and composition roots;
- dependency construction and configuration;
- public interfaces and adapters;
- core domain or application services;
- persistence and external clients;
- asynchronous workers, schedulers, and event consumers;
- cross-cutting concerns such as authentication, logging, retries, and metrics.

Describe actual dependency direction. Note where runtime wiring contradicts the
intended architecture.

## 2. Build a Behavioral Model

For each important workflow identify:

- trigger or input;
- validation and normalization;
- orchestration steps;
- state reads and writes;
- external side effects;
- decision points and invariants;
- output or externally visible result;
- failure and recovery behavior.

Prefer a short causal narrative over a list of functions.

## 3. Identify Invariants

Examples of invariants include:

- a state transition occurs only once;
- a balance or aggregate remains conserved;
- an entity cannot be persisted in an invalid state;
- authorization is checked before access or side effects;
- retries do not duplicate irreversible operations;
- a resource always has one clear owner;
- a public response preserves schema and semantics;
- cancellation cannot leave partial work hidden as success.

Infer invariants from requirements, tests, domain objects, validation, database
constraints, and repeated assumptions. Verify that every path preserves them.

## 4. Trace Data Lineage

Follow important data from origin to final use:

- where it is trusted or untrusted;
- how it is validated, normalized, enriched, or defaulted;
- where type, unit, precision, timezone, encoding, or ownership changes;
- where it is persisted, cached, logged, serialized, or exposed;
- whether stale or partially updated representations can coexist.

Data-lineage analysis often reveals defects that local function review misses.

## 5. Trace State and Lifecycle

For stateful code determine:

- owner and lifetime;
- valid states and transitions;
- concurrent readers and writers;
- transaction or lock boundaries;
- initialization and shutdown order;
- recovery after restart or partial failure;
- cache invalidation and consistency;
- cleanup responsibility.

Look for hidden temporal coupling: code that is correct only if methods are
called in a particular undocumented order.

## 6. Trace Failure Propagation

Start from a realistic dependency or operation failure and follow it upward and
downward:

- which exception or result is produced;
- whether it is translated, swallowed, retried, logged, or converted to success;
- whether partial side effects already occurred;
- whether retry is safe and bounded;
- whether the user or operator receives actionable information;
- whether state can be reconciled afterward.

Inspect how multiple failures interact, especially cleanup failure after a
primary failure.

## 7. Evaluate Abstraction Fitness

Ask whether each important abstraction:

- represents a stable domain or technical concept;
- owns a coherent responsibility;
- reduces rather than relocates complexity;
- exposes the information callers actually need;
- hides details that are safe to hide;
- supports realistic variation rather than speculative futures;
- has a clear replacement or extension boundary.

Warning signs include pass-through layers, generic managers, duplicated domain
rules, framework types leaking through every layer, and abstractions that require
callers to understand their internals.

## 8. Evaluate Changeability

Imagine one or two plausible future changes:

- a new provider or storage backend;
- a changed business rule;
- an added state or event type;
- a schema version transition;
- a new authentication or authorization rule;
- a higher volume or concurrency level.

Do not demand hypothetical generalization. Use the exercise to expose duplicated
knowledge, misplaced responsibilities, brittle contracts, and excessive change
propagation.

## 9. Look for Systemic Patterns

A project-level problem may be visible only across several files. Search for:

- repeated error-handling or retry logic with inconsistent semantics;
- duplicated validation or business rules;
- multiple competing abstractions for the same concept;
- divergent transaction, session, or client lifecycle patterns;
- inconsistent time, identifier, serialization, or configuration conventions;
- circular or bidirectional dependencies;
- modules with high fan-in, high fan-out, or broad global state;
- tests repeatedly constructing the same complicated environment.

A systemic finding should cite representative evidence and explain the common
root cause. Do not list every occurrence as a separate issue.

## 10. Use Counterfactual and Adversarial Scenarios

Useful questions include:

- What happens if this function is called twice?
- What happens if the dependency succeeds but the process dies before state is
  recorded?
- What happens if old and new versions run simultaneously?
- What happens if data is missing, stale, duplicated, reordered, or malformed?
- What happens if latency is ten times higher?
- What happens if a supposedly internal value becomes attacker-controlled?
- What happens when cleanup or rollback itself fails?
- What happens when a test mock behaves more simply than the real dependency?

Select scenarios that are credible for the system. Avoid arbitrary edge-case
enumeration.

## 11. Analyze Test Architecture

Use tests to discover intended behavior, but challenge their assumptions.
Assess:

- whether critical workflows are protected end to end;
- whether boundaries are tested with realistic protocols;
- whether mocks remove the behavior most likely to fail;
- whether fixtures reveal excessive setup coupling;
- whether test layers duplicate effort or leave gaps;
- whether the suite supports safe refactoring;
- whether failure, recovery, concurrency, and migration behavior are exercised.

Green tests can coexist with an incorrect model of the real system.

## 12. Evidence Levels

Classify investigation statements:

- **Observed** — directly visible in code, configuration, test output, or runtime
  evidence.
- **Inferred** — strongly supported by several observations but not directly
  executed.
- **Unknown** — important but not verifiable with available context.
- **Contradicted** — a candidate concern disproved by evidence.

Final defects should normally be observed or strongly inferred with a concrete
triggering scenario. Unknowns belong in residual risk, not disguised as facts.

## 13. Project-Audit Sampling

When exhaustive reading is impractical, sample intentionally:

- one or more primary end-to-end workflows;
- one failure-heavy workflow;
- central shared modules;
- representative modules from each architectural layer;
- high-churn or high-complexity areas;
- persistence and external integration boundaries;
- test infrastructure and CI configuration.

Record inspected, sampled, and uninspected areas. Generalize only when repeated
evidence supports it.

## 14. Open-Ended Review Prompts

Use these prompts when analysis becomes mechanical:

- What is the most surprising dependency in this design?
- Which assumption is doing the most work but has the least enforcement?
- Where can the system be locally correct and globally wrong?
- Which failure would be hardest to diagnose in production?
- Which piece of duplicated knowledge is most likely to diverge?
- Which abstraction makes simple behavior difficult to see?
- What would a new maintainer misunderstand first?
- What important behavior exists only in mocks, comments, or convention?
- Which code path has irreversible effects but weak evidence of idempotency?
- Which risk would not be found by a linter, type checker, or standard checklist?
