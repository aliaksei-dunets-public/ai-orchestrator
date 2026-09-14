# AI Orchestrator --- Task Creation Architecture

**Status:** Draft / baseline decision\
**Scope:** First level of the execution graph:
`User Request → Task Creation`\
**Purpose:** Define a minimal, portable architecture that can later be
moved into a dedicated repository and extended.

## 1. Core idea

The orchestrator should use a graph-based execution model.

The graph controls **the process**: which node runs, what it receives,
what result it must return, and where execution continues.

Skills remain **atomic capabilities**. A skill should know how to
perform its own responsibility, but should not need to know the complete
development workflow.

Sub-agents may execute individual graph nodes. The orchestrator
coordinates them and primarily exchanges structured artifacts instead of
carrying the entire conversation history through every step.

This gives the system:

-   predictable execution;
-   reusable skills;
-   configurable workflows;
-   smaller context windows for individual agents;
-   explicit transitions and loops;
-   separation between process control and AI reasoning.

## 2. Separation of responsibilities

### Graph

The graph describes:

-   nodes;
-   inputs and outputs;
-   transitions;
-   conditions;
-   loops;
-   failure paths;
-   optional project-specific configuration.

The graph answers:

> What runs next?

### Node

A node is a logical step in the graph.

A node describes:

-   which capability is invoked;
-   which input artifacts are required;
-   which output contract is expected;
-   which execution outcomes are valid.

A node does **not** need to correspond one-to-one with every internal
reasoning step.

For example, `create_task` can internally understand the request,
inspect context, identify constraints, and create an artifact while
remaining one graph node.

### Skill

A skill describes how a specialized operation is performed.

For example, `task-creator` knows how to transform a user request into a
structured task.

A skill should not decide which graph node runs after it.

### Sub-agent

A sub-agent can execute a node using the appropriate skill and limited
context.

The sub-agent can be short-lived. After producing its artifact, its
conversation history does not need to be passed to later agents.

### Task Manager Service

Task Manager is implemented as a deterministic `TaskManagerService`, not as an AI agent.

It owns:

- persistent Task state;
- coarse-grained Task lifecycle;
- artifact references;
- blockers;
- user decisions;
- Task history/events;
- state-transition guards.

It does not own:

- request understanding;
- implementation reasoning;
- workflow routing;
- current graph node;
- code review/testing decisions.

Principle:

> Task Creator thinks. Task Manager stores and guards state. Graph Runtime orchestrates.

Task state is separate from Workflow Run state.

```text
Task:
  created / preparing / ready / active / awaiting_input / blocked /
  awaiting_acceptance / completed / cancelled

Workflow Run:
  workflow / current_node / retries / routing / execution state
```

For v1, canonical Task storage is a Git-friendly filesystem repository under `.orchestrator/tasks`.

External trackers such as GitHub Issues are optional projections through a `TaskTrackerAdapter`; they are not sources of truth.


## 3. First-level workflow

Managed work now has an explicit preparation phase before it becomes executable.

```text
                  USER
                    ↓
              REQUEST ROUTER
                    ↓
               CREATE TASK
                    ↓
             TASK MANAGER
              status=created
                    ↓
          START PREPARATION
              status=preparing
                    ↓
                 CONTEXT
                    ↓
                 ANALYSIS
                    ↓
                PLANNING
                    ↓
              PLAN REVIEW
                /       \
      correction routes  approved
                           ↓
                  EXECUTION PACKAGE
                           ↓
                    status=ready
                     /        \
                immediate    deferred
                   ↓            ↓
                 claim         STOP
                   ↓
             execution phase
```

The important boundary is:

> A Task may exist before deep technical analysis, but it is not executable until preparation is complete and Plan Review has approved the implementation plan.

This allows the user-facing agent to prepare a task now and let a separate asynchronous executor implement it later without relying on the original conversation.

## 4. `create_task` node

### Responsibility

`create_task` creates the initial persistent problem contract.

It is responsible for:

1. understanding the user's intent at problem/outcome level;
2. capturing the original problem statement;
3. identifying the initial objective;
4. preserving explicit user constraints;
5. extracting obvious acceptance criteria without inventing technical details;
6. recording unresolved information;
7. setting the target workflow and desired handoff mode;
8. producing the initial Task Artifact.

### Explicit non-responsibilities

`create_task` should not:

- deeply inspect the repository to determine root cause;
- perform Impact Analysis;
- create the detailed implementation plan;
- select architecture prematurely;
- write production code;
- perform Plan Review or Code Review;
- execute tests.

Deep technical preparation belongs to:

```text
Context → Analysis → Planning → Plan Review
```

The Task Creator captures the initial **problem/outcome contract**. The preparation phase turns that persisted Task into an executable package.

## 5. Internal behavior of `create_task`

The graph sees one initial Task Creator node.

```text
understand user request
      ↓
normalize problem statement
      ↓
identify initial objective / constraints
      ↓
extract only obvious acceptance criteria
      ↓
select target workflow
      ↓
select handoff mode
      ↓
create initial Task Artifact
```

After persistence, a separate Development Preparation phase performs the expensive project work:

```text
Context
  ↓
Analysis / Investigation
  ↓
Impact Analysis
  ↓
Planning
  ↓
Plan Review
```

During `preparing`, the task definition may be refined from evidence while the original user request remains immutable and auditable.

Before `ready`, blocking open questions must be resolved or explicitly accepted by policy.

## 6. Context strategy

The initial Task Creator should use only enough context to normalize the user request safely.

It should **not** front-load the full repository investigation.

Deep context collection belongs to the reusable Context Subgraph in the preparation phase.

Preparation artifacts are attached to the Task:

```text
Task
+ Context Package ref
+ Analysis ref
+ Plan ref
+ Plan Review ref
+ Execution Package ref
```

A later executor receives these structured artifacts rather than the previous chat history.

This supports both immediate and asynchronous execution.

## 7. Task Artifact

The Task is the stable persistent boundary between free-form user interaction and managed work.

Initial example:

```yaml
id: TASK-0042
title: Incorrect payment calculation
status: created
type: implementation

source:
  type: user_request
  original_request_ref: REQUEST-0042

problem_statement: >
  Payment calculation is incorrect for scenario X.

objective: >
  Investigate and correct the payment calculation problem.

constraints: []
acceptance_criteria: []
open_questions: []

execution:
  target_workflow: development
  handoff_mode: deferred

artifacts:
  context: null
  analysis: null
  plan: null
  plan_review: null
  execution_package: null
```

After preparation, the same Task may be enriched and become executable:

```yaml
status: ready

objective: >
  Correct scenario X while preserving existing valid payment behavior.

acceptance_criteria:
  - id: AC-01
    text: Scenario X returns the expected payment result.

execution:
  prepared_source_revision: abc123

artifacts:
  context: CONTEXT-0042-v2
  analysis: ANALYSIS-0042-v1
  plan: PLAN-0042-v2
  plan_review: PLAN-REVIEW-0042-v2
  execution_package: EXEC-PKG-0042-v1
```

The original user request remains immutable. Refinements are versioned Task events/evidence-based updates.

## 8. Outcomes

The first version should support at least these outcomes.

### `success`

The request is sufficiently understood and a valid Task Artifact has
been created.

The graph may register the task in Task Manager and continue later to
another workflow.

### `needs_input`

Required information is missing and guessing would materially change the
task.

Example:

``` yaml
result: needs_input

questions:
  - Which API or endpoint is affected?
  - What behavior is currently incorrect?
```

The graph routes execution back to the user. After the answer,
`create_task` is executed again with the additional information.

### `failure`

Task creation could not complete because of an execution/tool/system
problem rather than a normal lack of user information.

The exact failure policy will be designed later.

## 9. Important design principles

### Preserve intent, do not invent solutions

If the user asks for a capability, Task Creator should capture the
desired capability. It should not prematurely decide whether the
solution must be a skill, graph, script, service, or architectural
component.

### Artifacts over conversation history

Agents exchange stable artifacts and references wherever possible.

### Atomic skills, configurable graph

Skills should be reusable across projects. Project-specific behavior
should eventually be expressed through graph configuration and project
profiles rather than forks of every skill.

### Keep graph granularity practical

Do not create a graph node for every LLM reasoning step. Create a node
when the step needs an independent contract, routing, retry behavior,
observability, reuse, or policy.

### Deterministic orchestration around non-deterministic reasoning

The agent can reason freely inside a node, while the graph constrains
valid inputs, outputs, and transitions.

## 10. Model routing and execution policy

Model selection belongs to the **node execution policy**, not to the
skill itself.

A reusable skill should describe how to perform a capability without
being permanently bound to a specific provider or model. The graph/node
configuration decides which model profile is appropriate for a
particular execution.

Prefer logical model profiles over hard-coded model names:

``` yaml
model_profiles:
  cheap:
    provider: configurable
    model: configurable
    reasoning: low

  standard:
    provider: configurable
    model: configurable
    reasoning: medium

  expert:
    provider: configurable
    model: configurable
    reasoning: high
```

A node references the logical profile:

``` yaml
create_task:
  type: agent
  skill: task-creator

  execution:
    model_profile: cheap
    escalation_profile: standard
```

This separation allows the same graph and skills to run across Codex,
other cloud providers, or local models by changing execution
configuration rather than rewriting workflow logic.

### Dynamic escalation

A node may start with a cheaper model and escalate only when the task
requires it.

Conceptually:

``` text
cheap model
    │
    ├── sufficient result ──► accept
    │
    └── insufficient/complex ──► stronger model
```

Possible escalation signals include:

-   high ambiguity;
-   conflicting context;
-   high-risk task classification;
-   inability to satisfy the output contract;
-   low-quality or incomplete result;
-   policy requiring stronger review.

The exact escalation mechanism and confidence policy are intentionally
deferred.

### Initial routing guidance

Typical defaults may be:

-   context lookup / summarization → cheap;
-   task creation → cheap, with escalation to standard;
-   classification / routing → cheap;
-   implementation → standard or expert depending on complexity;
-   architecture analysis → expert;
-   plan review → expert;
-   code review → expert;
-   security review → expert;
-   documentation synchronization → standard;
-   memory/session summarization → cheap or standard;
-   deterministic lint/build/test operations → no LLM unless
    interpretation is required.

For the first workflow, the intended default is:

``` yaml
create_task:
  execution:
    model_profile: cheap
    escalation_profile: standard
```

The actual provider/model mapping belongs to environment or project
configuration.

## 11. Deferred decisions

The following are intentionally not finalized yet:

-   complete Task Artifact schema;
-   exact YAML graph schema;
-   graph runtime/engine implementation;
-   storage format and directory layout;
-   task ID generation;
-   context retrieval implementation;
-   project profile schema;
-   agent/runtime provider abstraction;
-   retry and failure policies;
-   later nodes such as analysis, planning, implementation, review,
    testing, documentation, memory, and health check.

These should be designed incrementally after the
`User Request → Task Creation` level is stable.


## Request Routing Layer

Not every user request should create a managed Task.

A lightweight `request_router` should sit before Task Creation and decide whether the request requires persistent, multi-step managed work or can be handled directly.

```text
                         USER
                           │
                           ▼
                 ┌──────────────────┐
                 │  REQUEST ROUTER  │
                 └────────┬─────────┘
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
        ▼                 ▼                  ▼
 Direct Response      Managed Work       Interaction
                           │
                           ▼
                     CREATE TASK
                           │
                           ▼
                    TASK MANAGER
                      created
                           │
                           ▼
              DEVELOPMENT PREPARATION
          Context → Analysis → Planning → Review
                           │
                           ▼
                         ready
                           │
                           ▼
                    Workflow Router
                           │
       ┌───────────┬───────┼─────────┬────────────┐
       ▼           ▼       ▼         ▼            ▼
Implementation  Analysis  Investigation Incident Exploration
```

The routing criterion is not whether the request changes code.

> Does this request require managed work with state, artifacts, multiple steps, checkpoints, or later continuation?

Examples:

| Request | Managed Task? |
|---|---|
| Explain what this class does | Usually no |
| Explain REST vs GraphQL | No |
| Analyze this module and prepare a report | Yes |
| Find the cause of a memory leak | Yes |
| Fix the memory leak | Yes |
| Production is failing | Yes, incident |
| Brainstorm ideas informally | Usually no |
| Compare three architectures and recommend one | Yes, exploration |
| Write a small regex | Usually no |
| Refactor an authentication subsystem | Yes |

The router classifies and routes. It does not solve the problem.

Candidate result:

```yaml
route: managed_work
suggested_type: investigation
confidence: high
```

Direct interaction:

```yaml
route: direct_response
suggested_type: null
confidence: high
```

## Universal Task Model

Task Creation is not limited to implementation work.

A Task is the universal **managed unit of work**. Its `type` describes the nature of the work; the graph determines how that work is executed.

Initial task types:

- `implementation`
- `analysis`
- `investigation`
- `incident`
- `exploration`

### Analysis

```yaml
type: analysis
objective: >
  Identify the causes of degraded Payment API performance.
expected_outcome:
  - identified bottlenecks
  - supporting evidence
  - recommendations
```

### Investigation

```yaml
type: investigation
objective: >
  Determine the root cause of intermittent test failures.
```

An investigation may end with a report. It does not automatically imply a code change.

A later implementation Task can reference the investigation:

```yaml
parent: TASK-0102
derived_from: investigation
```

### Incident

```yaml
type: incident
priority: critical
incident:
  environment: production
  severity: critical
  symptoms:
    - payments are failing
```

An incident may later route through triage, evidence collection, mitigation, root-cause analysis, fix, verification, and postmortem.

### Exploration

Informal brainstorming does not always need a Task. Structured exploration with a defined deliverable should become managed work.

```yaml
type: exploration
objective: >
  Explore alternative architectures and recommend an approach.
expected_outcome:
  - alternatives
  - pros and cons
  - recommendation
  - unresolved questions
```

## Request Router execution policy

`request_router` should normally use a cheap/fast model profile.

```yaml
request_router:
  type: agent
  skill: request-router

  execution:
    model_profile: cheap
    escalation_profile: standard
```

It should escalate only when classification is ambiguous or project policy requires it.

## Architectural principle

> Task is the universal managed-work unit. Type describes the work. Graph selects how it is executed.

The same `task-creator` skill should normally be reused for implementation, analysis, investigation, incident, and exploration tasks.

Separate Task Creator skills should only be introduced if their contracts diverge substantially.

## New open questions

- What exact rules distinguish direct interaction from managed work?
- Should `request_router` be an LLM node, hybrid rules + LLM, or engine-level logic?
- Which task types require additional mandatory fields?
- Should `workflow_router` be an explicit node or an engine-level transition?
- How should low-confidence routing be escalated?


---

## 11. Task persistence and external tracker

Accepted v1 architecture:

```text
Task Creator
      ↓
TaskManagerService
      ↓
TaskRepository
      ↓
FilesystemTaskRepository
      ↓
.orchestrator/tasks
```

Optional tracker projection:

```text
committed Task event
      ↓
TaskTrackerSync
      ↓
TaskTrackerAdapter
      ↓
GitHub Issues / future provider
```

The external tracker never replaces canonical Task state in v1.

Detailed specifications:

- `03-task-manager-service-architecture.md`
- `04-task-manager-service-contract.md`
- `05-task-tracker-adapter-architecture.md`
- `06-task-tracker-adapter-contract.md`
- `07-task-management-integration-patch.md`


## Prepared Task / execution readiness

For implementation-style managed work, the Task lifecycle includes a durable preparation boundary:

```text
created → preparing → ready → active
```

`ready` means the Task has:

```text
valid Context Package
successful Implementation Analysis
approved Implementation Plan
approved Plan Review
Execution Package
no blocking preparation questions/blockers
```

A separate executor loop may safely pick only `ready` tasks.

Detailed specifications:

- `08-task-readiness-and-execution-package.md`
- `09-task-executor-loop-architecture.md`
- `../orchestrator-development-spec-v2/33-development-preparation-execution-boundary.md`
- `../orchestrator-development-spec-v2/34-execution-preflight-contract.md`


## Task definition refinement

The initial Task is allowed to be incomplete at technical level. During `preparing`, evidence from Context and Analysis may refine the objective, acceptance criteria, constraints, and problem statement through `TaskManagerService.refine_task_definition()`.

The original user request remains immutable.

By the time the Task reaches `ready`, blocking ambiguity should be resolved and the Task should reference the approved technical preparation package.
