# Detailed Python Review Workflow

Review Python software as a system, not as isolated rule violations. Before
consulting a checklist, build an independent model of purpose, behavior,
boundaries, state, invariants, and failure propagation. Frameworks and tools
widen coverage; they do not replace judgment or limit valid findings.

## When to Use

Use this skill:

- before merging a pull request or branch;
- after implementing a feature, refactor, migration, or complex bug fix;
- after code was produced by another human or agent;
- when auditing a Python module, package, service, subsystem, or repository;
- when the user asks for code review, architecture review, production-readiness
  assessment, regression analysis, or a project-quality audit.

Do not use it as a substitute for:

- incident debugging when the immediate task is to discover an unknown root
  cause;
- implementation work when the user asked only for changes;
- formatting-only checks already enforced by deterministic tools.

## Operating Rules

1. **Review is read-only by default.** Do not modify code, tests,
   configuration, dependencies, or Git state unless the user explicitly asks
   for fixes.
2. **Global understanding precedes local judgment.** Inspect enough surrounding
   code to understand behavior and architecture before evaluating individual
   lines.
3. **Checklists are non-exhaustive prompts.** The reviewer is expected to find
   problems, strengths, and design insights not named in this skill.
4. **Exploration may use hypotheses; final findings require evidence.** During
   investigation, generate possible failure modes and architectural concerns.
   Report them only after they are confirmed or clearly labelled as unresolved
   risk.
5. **Trace causes and consequences.** Prefer an end-to-end causal chain over a
   local observation such as “this function is complex.”
6. **Evidence over assertion.** Every actionable finding must identify a code
   location or architectural boundary, a triggering scenario, and a concrete
   impact.
7. **No invented execution.** Never claim a command or test passed unless it was
   run and observed.
8. **Tools support judgment; they do not provide it.** Linters, type checkers,
   scanners, and coverage reports produce evidence, not conclusions.
9. **Calibrate depth to risk.** Spend more effort on core workflows, shared
   abstractions, irreversible side effects, stateful code, security boundaries,
   migrations, concurrency, money, and public contracts.
10. **Distinguish current defects from broader design debt.** Do not block a
    focused change for unrelated historical debt, but explain when existing
    design materially affects the safety of the change.
11. **Verify independent feedback.** A second reviewer is a challenge mechanism,
    not an authority.

## Review Target vs Analysis Horizon

Never equate the files being reviewed with the context needed to review them.

Record three scopes:

- **Target scope** — the change, component, or project for which a verdict is
  requested.
- **Context scope** — callers, dependencies, tests, configuration, schemas,
  persistence, and neighboring modules needed to understand the target.
- **System horizon** — the larger runtime and architectural behavior that may be
  affected, even when most of its files are unchanged.

The final findings should remain relevant to the target scope. The analysis may
cross any repository boundary necessary to establish correctness and impact.

Supported modes:

- `CHANGE_REVIEW` — Git diff, pull request, branch, commit range, or
  uncommitted changes.
- `COMPONENT_REVIEW` — package, service, feature, module, or subsystem.
- `PROJECT_AUDIT` — architecture and quality assessment of a repository or a
  major project area.

Record:

- `REVIEW_MODE`;
- target, context, and system horizon;
- `BASE_REF` and `HEAD_REF` when relevant;
- requirements, issue, plan, or expected behavior;
- exclusions, generated code, vendor code, and known environment limitations.

If requirements are unavailable, assess internal coherence and likely behavior,
but do not claim complete requirement compliance.

## Progressive Disclosure

Read supporting material in this order:

1. Read this file.
2. For every non-trivial review, read `references/system-analysis.md`.
3. Perform the initial open-ended semantic pass.
4. Then read relevant sections of `references/python-review.md`.
5. Read `references/tooling.md` before selecting automated checks.
6. Read `reviewers/independent-reviewer.md` only when dispatching the second
   review.
7. Use `templates/review-report.md` for the final report.

Do not load all references before forming the initial system model. This reduces
checklist anchoring.

# Review Workflow

## Phase 0 — Establish the Review Contract

Determine:

- requested mode and verdict;
- target scope, context scope, and system horizon;
- known requirements and critical domain rules;
- acceptable review depth and environmental constraints;
- whether independent execution is available.

For large projects, state a review strategy rather than pretending every file
will receive equal depth. Prefer representative end-to-end flows, architectural
boundaries, shared abstractions, central state, and risk hotspots.

## Phase 1 — Reconstruct the System

Before detailed judgment, build a concise system model from code and project
materials.

Inspect as relevant:

- repository instructions and architecture documents;
- package layout and dependency direction;
- application entry points and composition roots;
- core domain objects and services;
- API, worker, scheduler, CLI, event, and persistence boundaries;
- configuration and dependency injection;
- tests that reveal expected behavior;
- deployment, migration, and operational assumptions.

Be able to describe:

- the system's purpose and primary workflows;
- major components and their responsibilities;
- control flow and data flow across boundaries;
- ownership and lifetime of important state and resources;
- important invariants and contracts;
- expected failure, retry, cancellation, and recovery behavior;
- architectural constraints and intentional trade-offs.

If this model cannot be formed, record the missing context. Do not compensate by
performing a purely syntactic review.

## Phase 2 — Open-Ended Semantic Review

Review the implementation without consulting the Python checklist yet.

Use the model's general software-engineering reasoning to assess:

- whether the code solves the intended problem directly and coherently;
- whether responsibilities are placed at the correct layer;
- whether abstractions match real domain concepts or merely hide complexity;
- whether control flow, state mutation, and side effects are understandable;
- whether the design creates hidden coupling, temporal dependencies, or invalid
  intermediate states;
- whether duplicated logic represents accidental repetition or inconsistent
  business rules;
- whether local correctness depends on undocumented global assumptions;
- whether tests describe the real contract or only mirror the implementation;
- whether the implementation is likely to remain correct under future changes;
- whether a simpler design would remove an entire class of risk.

Generate an investigation set containing:

- key invariants to verify;
- suspicious assumptions;
- possible failure chains;
- architectural tensions;
- missing context;
- candidate strengths that reduce risk.

These are hypotheses, not reportable findings yet.

## Phase 3 — Trace Representative End-to-End Behavior

Select scenarios based on the actual system rather than a fixed list.

At minimum consider the normal path and the most credible failure path. Where
relevant also trace:

- invalid, empty, boundary, or large input;
- dependency timeout or malformed response;
- partial success after an external side effect;
- duplicate request, retry, replay, or repeated job execution;
- concurrent access or out-of-order events;
- process restart, cancellation, or shutdown during work;
- old/new schema or version coexistence;
- rollback, compensation, cleanup, or recovery;
- authorization changes across layers;
- scale or load growth that changes behavior.

Follow each selected scenario across functions and files until its final state,
output, or failure is clear. Do not stop at the first wrapper or mocked boundary.

## Phase 4 — Map the Change and Blast Radius

For `CHANGE_REVIEW`, inspect the complete change and surrounding implementation.
Useful read-only commands include:

```bash
git status --short
git diff --stat <base>...<head>
git diff --name-status <base>...<head>
git diff --find-renames <base>...<head>
git diff <base>...<head>
git log --oneline --decorate <base>..<head>
```

For uncommitted work inspect both:

```bash
git diff --cached
git diff
```

Trace affected symbols and contracts through:

- callers and call sites;
- interfaces, protocols, public exports, and dependency bindings;
- validation, serialization, API schemas, and compatibility layers;
- models, queries, migrations, and transaction boundaries;
- configuration, defaults, feature flags, and environment variables;
- tasks, retries, queues, scheduling, and idempotency;
- tests, fixtures, mocks, factories, and snapshots;
- documentation and examples that function as public contract.

Do not infer low risk from a small diff. A one-line change to a default,
signature, query, or lifecycle rule may have system-wide consequences.

## Phase 5 — Hypothesis-Driven Investigation

Investigate the hypotheses created during the semantic pass.

For each material hypothesis:

1. Identify the code and runtime conditions that would make it true.
2. Trace the causal path to a user-visible, operational, security, data, or
   maintainability impact.
3. Inspect tests and history for confirming or contradicting evidence.
4. Attempt to disprove the hypothesis.
5. Classify it as:
   - **confirmed finding**;
   - **rejected hypothesis**;
   - **residual risk / unknown**;
   - **intentional trade-off**.

Use Git history or blame only when it helps explain intent, compatibility, or a
regression. Do not substitute historical speculation for current evidence.

## Phase 6 — Run Targeted Automated Checks

Read `references/tooling.md`. Prefer repository-native commands and existing
environments.

Select checks that answer active review questions, for example:

1. focused behavioral tests;
2. broader tests around affected flows;
3. lint and formatting checks;
4. static type checks;
5. security and dependency checks;
6. coverage, profiling, or complexity checks when they test a specific concern.

Rules:

- do not mutate lockfiles or install tools merely to make a review appear
  complete;
- record command, scope, exit status, result, relevance, and limitations;
- distinguish baseline failures from regressions introduced by the target;
- treat green checks as supporting evidence, never proof of correctness.

## Phase 7 — Structured Coverage Sweep

Only after the open-ended and hypothesis-driven passes, use the following axes
as a backstop for missed areas.

### A. Behavior and Correctness

Review requirement alignment, contracts, boundary cases, state invariants,
error semantics, partial success, retries, cancellation, cleanup, compatibility,
and regression sensitivity.

### B. Clarity and Local Design

Review naming, cohesion, hidden side effects, unnecessary indirection,
understandability, duplication, comments, and consistency with established
patterns.

### C. Architecture and Changeability

Review responsibility placement, dependency direction, abstraction fitness,
framework coupling, data ownership, public API evolution, migration/deployment
ordering, and the likely cost of future change.

### D. Security and Data Protection

Review trust boundaries, validation, authorization, injection, unsafe
serialization, file/path handling, secrets, sensitive data, privilege changes,
and supply-chain effects.

### E. Reliability, Performance, and Operations

Review complexity on realistic workloads, repeated I/O, blocking async work,
unbounded concurrency, lifecycle ownership, timeouts, backpressure, retries,
cache consistency, observability, diagnosis, startup, shutdown, and recovery.

A completed axis does not mean “no issue found.” It means the reviewer has
considered how that dimension applies to the actual system.

## Phase 8 — Python-Specific Coverage

Now read relevant sections of `references/python-review.md`.

Use them to challenge and extend the semantic analysis, especially around:

- runtime and type-level contracts;
- mutability and object lifetime;
- exceptions and cleanup;
- async, concurrency, cancellation, and task ownership;
- iterators, generators, imports, and module initialization;
- data models, datetime, numeric precision, and serialization;
- database transactions and resource ownership;
- Python-specific security behavior;
- pytest isolation, fixture design, and mock fidelity.

Do not report a Python rule merely because it exists. Explain why it matters in
this implementation. Continue to report valid issues that are not represented
in the reference.

## Phase 9 — Test Architecture and Confidence

Assess the test suite as a model of system behavior, not only as a collection of
passing checks.

Determine:

- which business and technical contracts are actually protected;
- whether tests would fail for the real defect being considered;
- whether mocks preserve important boundary behavior;
- whether unit, integration, contract, and end-to-end tests are balanced for the
  architecture;
- whether fixtures and shared state create false confidence;
- which critical workflows remain unverified;
- whether tests make refactoring safer or simply encode implementation details.

For project audits, identify structural test gaps such as untested integration
boundaries, missing failure-path suites, slow feedback loops, or duplicated test
setups that hide architectural fragmentation.

## Phase 10 — Project-Audit Strategy

For `PROJECT_AUDIT`, do not mechanically iterate every file with equal depth.
Build and disclose a coverage strategy.

Prioritize:

1. entry points and composition roots;
2. central domain workflows and irreversible side effects;
3. shared abstractions and high fan-in dependencies;
4. stateful, concurrent, scheduled, financial, security-sensitive, or migration
   code;
5. external boundaries and persistence;
6. repeated patterns and representative modules;
7. test architecture and CI quality gates;
8. hotspots indicated by complexity, churn, incidents, TODOs, or duplicated
   logic.

Produce both:

- **systemic findings** that recur or arise from architecture;
- **localized findings** tied to a concrete implementation.

State what was inspected deeply, sampled, or not inspected. Never imply complete
coverage when the audit used sampling.

## Phase 11 — Independent Review

Follow the admission contract in `../SKILL.md`. Dispatch at most one independent
reviewer and do not dispatch outside those criteria merely because a change is
non-trivial.

### Preferred mechanism

Dispatch a fresh agent or model using `reviewers/independent-reviewer.md`.
Provide only:

- target, context, and system horizon;
- requirements and critical invariants;
- Git refs or component paths;
- repository instructions and architecture references;
- compact validation summaries and artifact/source pointers;
- known limitations and read-only constraints.

Include bounded raw diagnostics only when the reviewer needs them to investigate
a concrete failure and no stable artifact pointer is available.

Do not provide the primary findings, severities, conclusions, or implementation
session history.

### Fallback

If independent execution is unavailable:

1. finish the primary review;
2. rebuild the system model from tests and entry points rather than from the
   original reading order;
3. re-trace at least one normal and one failure scenario;
4. actively search for evidence that disproves primary findings;
5. search for important risks outside the structured axes;
6. disclose that the second pass was not independently executed.

Never silently skip required independent review.

## Phase 12 — Reconcile and Report

Verify every candidate finding against the codebase. Merge duplicates by root
cause. Reject incorrect, unreachable, irrelevant, or preference-only feedback.
Resolve severity from impact, likelihood, detectability, and recovery cost.

Use `templates/review-report.md`.

The report must distinguish:

- system understanding and architectural assessment;
- confirmed systemic and local findings;
- strengths that materially reduce risk;
- verification evidence;
- residual risks and coverage limitations;
- independent-review contribution;
- merge or release verdict when requested.

Every Critical, Blocking, or Important finding must include:

- exact location or architectural boundary;
- evidence and triggering scenario;
- causal path and impact;
- recommended correction or acceptance criterion;
- confidence: `high`, `medium`, or `low`.

## Severity and Verdict

Severities:

- **Critical** — credible security compromise, data loss/corruption, dangerous
  financial effect, systemic outage, or fundamentally broken core behavior.
- **Blocking** — incorrect behavior, contract violation, serious regression,
  or unacceptable security/reliability risk that must be addressed before
  merge.
- **Important** — meaningful architectural, maintainability, test,
  error-handling, performance, or operational risk that should be corrected or
  explicitly accepted.
- **Minor** — localized low-risk quality issue.
- **Suggestion** — optional alternative without a demonstrated defect.

Verdicts:

- `APPROVE` — no unresolved Critical or Blocking findings.
- `APPROVE WITH FOLLOW-UPS` — no blockers; remaining risks are acceptable and
  can be tracked separately.
- `REQUEST CHANGES` — one or more unresolved Blocking findings.
- `BLOCK` — one or more unresolved Critical findings.
- `INCONCLUSIVE` — evidence, requirements, code, or environment is insufficient
  for a responsible verdict.

## Completion Criteria

A review is complete only when:

- [ ] target scope, context scope, and system horizon are explicit;
- [ ] the reviewer can explain the affected system and primary workflows;
- [ ] important invariants, state, resources, and failure propagation were
      identified;
- [ ] representative end-to-end scenarios were traced;
- [ ] open-ended semantic analysis occurred before checklist coverage;
- [ ] candidate hypotheses were verified, rejected, or recorded as unknown;
- [ ] blast radius and contract impact were assessed;
- [ ] relevant automated evidence was gathered or its absence explained;
- [ ] structured and Python-specific coverage were used as safeguards;
- [ ] test architecture and confidence were assessed;
- [ ] independent review was completed or its limitation disclosed;
- [ ] systemic findings are separated from local findings;
- [ ] every actionable finding contains evidence, impact, and location;
- [ ] coverage limits and residual risks are explicit;
- [ ] a clear verdict is provided when requested.

## Anti-Patterns

Never:

- start a non-trivial review by mechanically walking the Python checklist;
- assume the changed files define the full analysis boundary;
- replace system understanding with linter, type-checker, or scanner output;
- approve solely because CI is green;
- report generic advice without a causal defect or risk;
- suppress a valid insight because it is not named in this skill;
- inflate severity to make the review look thorough;
- demand unrelated redesign to approve a focused change;
- describe a sampled project audit as complete repository coverage;
- let the same reasoning context impersonate an independent reviewer without
  disclosure;
- modify code during review unless explicitly requested.
