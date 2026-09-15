# AI Orchestrator --- Task Creation Graph Template


> **Актуализация 2026-09-15:** положения о каноническом файловом состоянии задач, `task.yaml`, `events.jsonl` и файловом репозитории заменены [контрактом состояния и хранения](../architecture/state-and-storage.md). Источник истины — SQLite Task Manager; каталог задачи содержит Specification и Plan. Остальной текст — импортированный проектный материал, не подтверждение реализации.

This file is a **conceptual template**, not yet a frozen runtime schema.
It records the current graph design in a form that can later evolve into
the actual YAML configuration.

## Conceptual flow

``` text
USER_REQUEST
     │
     ▼
CREATE_TASK
     │
     ├── needs_input ──► ASK_USER ──► CREATE_TASK
     │
     ├── success ──────► REGISTER_TASK
     │
     └── failure ──────► FAILURE_HANDLER   # policy TBD
```

## Candidate YAML

``` yaml
graph:
  id: task_creation
  version: 0.1

  entrypoint: create_task

  nodes:

    create_task:
      type: agent

      agent: task_creator
      skill: task-creator

      execution:
        model_profile: cheap
        escalation_profile: standard

      inputs:
        required:
          - user_request
        optional:
          - project_profile
          - relevant_context
          - previous_user_answers

      outputs:
        artifact: task
        result:
          enum:
            - success
            - needs_input
            - failure

      transitions:
        success: register_task
        needs_input: ask_user
        failure: task_creation_failed

    ask_user:
      type: interaction

      inputs:
        - questions

      transitions:
        answered: create_task

    register_task:
      type: action

      capability: task_manager_service

      inputs:
        - task

      command:
        name: create_task

      effects:
        task_status: created
        canonical_store: task_repository

      terminal: true

    task_creation_failed:
      type: failure

      policy: TBD

      terminal: true
```

## Candidate Task Artifact

``` yaml
task:
  id: TASK-XXXX
  title: ""

  status: created
  type: null

  source:
    type: user_request

  objective: ""

  expected_outcome: []

  constraints: []

  acceptance_criteria: []

  open_questions: []

  context_refs: []

  context_summary: null

  created_by: task-creator
```

## Candidate node result contract

Successful execution:

``` yaml
result: success
artifact:
  type: task
  ref: tasks/TASK-XXXX/task.yaml
```

Additional information required:

``` yaml
result: needs_input
questions:
  - ""
```

Execution failure:

``` yaml
result: failure
error:
  type: ""
  message: ""
```

## `task-creator` skill boundary

The skill should:

-   understand the user's requested outcome;
-   retrieve only context needed to define the task;
-   formulate the objective;
-   capture constraints;
-   formulate expected outcomes;
-   formulate or extract acceptance criteria;
-   expose unresolved questions;
-   create the Task Artifact.

The skill should not:

-   produce a detailed implementation plan;
-   choose architecture prematurely;
-   implement code;
-   review code;
-   run the development lifecycle;
-   decide which graph node executes next.

## Context hand-off

Preferred:

``` text
User Request
+ Project Profile
+ Relevant Context
        │
        ▼
   Task Creator
        │
        ▼
 Task Artifact
 + Context Refs
```

Avoid:

``` text
Entire conversation history
        │
        ▼
every subsequent agent
```

## Model routing template

Model choice is an execution concern of the node, not a property of the
skill.

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

Example node policy:

``` yaml
create_task:
  skill: task-creator

  execution:
    model_profile: cheap
    escalation_profile: standard
```

The concrete model mapping can be overridden by the target
environment/project without changing the skill or graph semantics.

Future versions may support conditional escalation based on ambiguity,
risk, context conflicts, contract validation, or other quality signals.

## Open design questions

1.  Should `ask_user` be an explicit node or a runtime interaction
    state?
2.  Should Task Manager registration be an explicit graph node or an
    engine side effect?
3.  Which fields in the Task Artifact are mandatory?
4.  How are `context_refs` resolved across different coding
    environments?
5.  Should task type/risk/classification belong to Task Creator or a
    later analysis node?
6.  Which parts of the graph are universal and which belong in a project
    profile?
7.  What is the minimum portable graph runtime needed for Codex and
    other agent environments?

These questions are deliberately left open for the next design
iterations.


## Extended top-level graph template

```yaml
graph:
  id: request_to_task
  version: 0.2

  entrypoint: request_router

  nodes:

    request_router:
      type: agent
      skill: request-router

      execution:
        model_profile: cheap
        escalation_profile: standard

      inputs:
        required:
          - user_request
        optional:
          - project_profile

      outputs:
        route:
          enum:
            - direct_response
            - managed_work
        suggested_type:
          enum:
            - implementation
            - analysis
            - investigation
            - incident
            - exploration
            - null
        confidence:
          enum:
            - low
            - medium
            - high

      transitions:
        direct_response: direct_response
        managed_work: create_task

    direct_response:
      type: interaction
      terminal: true

    create_task:
      type: agent
      skill: task-creator

      execution:
        model_profile: cheap
        escalation_profile: standard

      inputs:
        required:
          - user_request
          - suggested_type
        optional:
          - project_profile
          - relevant_context
          - previous_user_answers

      outputs:
        artifact: task
        result:
          enum:
            - success
            - needs_input
            - failure

      transitions:
        success: register_task
        needs_input: ask_user
        failure: task_creation_failed

    ask_user:
      type: interaction

      inputs:
        - questions

      transitions:
        answered: create_task

    register_task:
      type: action
      capability: task_manager_service

      inputs:
        - task

      command:
        name: create_task

      effects:
        task_status: created
        canonical_store: task_repository

      terminal: true

    task_creation_failed:
      type: failure
      policy: TBD
      terminal: true
```

## Request Router contract

Managed work is appropriate when the request needs persistent state, artifacts, multiple execution steps, checkpoints, or later continuation.

Managed result:

```yaml
route: managed_work
suggested_type: investigation
confidence: high
```

Direct result:

```yaml
route: direct_response
suggested_type: null
confidence: high
```

The router must not perform the actual analysis, implementation, investigation, or incident handling.

## Task type template

```yaml
task:
  type:
    enum:
      - implementation
      - analysis
      - investigation
      - incident
      - exploration
```

Initial semantics:

```yaml
implementation:
  purpose: change or create system behavior

analysis:
  purpose: study a system/problem and produce findings or recommendations

investigation:
  purpose: determine root cause using evidence and hypothesis validation

incident:
  purpose: handle an operational problem requiring triage and controlled response

exploration:
  purpose: perform structured research or brainstorming with a defined deliverable
```

Task type influences the later execution workflow. It does not require a separate Task Creator skill by default.


---

## Accepted Task Manager runtime boundary

`register_task` invokes the deterministic `TaskManagerService`.

```text
Task Creator
→ register_task action
→ TaskManagerService.create_task()
→ canonical Task stored
```

The Task Manager is not a graph-level reasoning agent.

Task status is coarse-grained and separate from Workflow Run execution state.

External tracker synchronization is triggered from committed Task events and is not required for successful task registration.

Recommended v1 external mode:

```yaml
task_tracker:
  mode: outbound_mirror
  provider: github
  required: false
```

The earlier open question about Task Manager responsibility is resolved:

> Registration semantics are explicit in the graph, while persistence/state invariants belong to TaskManagerService.
