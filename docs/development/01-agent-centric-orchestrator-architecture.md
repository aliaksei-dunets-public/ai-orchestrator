# Agent-Centric AI Orchestrator Architecture

**Status:** Historical source material — current normative contract is the Russian architecture
**Decision:** Shift orchestration responsibility from a Python-controlled workflow engine to a global Orchestrator Agent  
**Scope:** AI Orchestrator core architecture

> **Актуализация Graphify (2026-09-18).** Диаграммы ниже используют раннюю подпись `Code Graph / Graphify` и сохранены как исходник агент-центричного решения. В действующей архитектуре это **единый Project Knowledge Graph**: код и отобранная долговечная документация находятся в одном графе. Semantic extraction документов выполняет Graphify skill текущего host-agent; отдельный documentation graph, headless backend и собственный Markdown extractor для v1 не вводятся. Нормативные детали находятся в [русском контракте Project Knowledge Service](../architecture/project-knowledge-service.md).

---

## 1. Executive decision

The AI Orchestrator will **not** be designed primarily as a Python script that hard-codes and executes every development step.

Instead, the core orchestration role will be performed by a **global Orchestrator Agent**.

The agent acts as the conductor of the development process:

- understands the current Task;
- reads the workflow graph;
- decides which valid step should run next;
- gathers and manages context;
- invokes skills and tools;
- queries the Project Knowledge Graph;
- creates or invokes specialized sub-agents when useful;
- asks the user for input when required;
- produces and updates artifacts;
- evaluates results;
- moves the Task through its lifecycle.

A small deterministic software layer remains, but its role is limited to **state, persistence, validation, safety, and execution primitives**.

The architecture therefore becomes:

```text
                  USER
                    ↓
          GLOBAL ORCHESTRATOR AGENT
                    │
       ┌────────────┼────────────┐
       ↓            ↓            ↓
 Workflow Graph   Skills     Knowledge Sources
       │            │            │
       │            │      ┌─────┴─────────┐
       │            │      ↓               ↓
       │            │  Code Graph       Memory
       │            │  / Graphify
       │            │
       ↓            ↓
 Tools / Commands / Sub-agents
                    │
                    ↓
          Deterministic Core Layer
          State / Artifacts / Guards
```

---

## 2. Previous architecture

The earlier mental model was closer to:

```text
Python Orchestrator
      ↓
Step 1
      ↓
LLM
      ↓
save output
      ↓
Step 2
      ↓
LLM
      ↓
save output
      ↓
Step 3
```

In this model, Python owns most of the workflow.

The script determines:

- which node executes;
- when the LLM is called;
- which context is passed;
- which tool is invoked;
- which output is stored;
- which node follows next.

The LLM acts mainly as a reasoning function inside a predefined software pipeline.

This approach is predictable, but it unnecessarily restricts the capabilities of modern development agents.

---

## 3. Why we are changing the approach

Modern development agents already possess the capabilities required for orchestration:

- reasoning;
- planning;
- tool use;
- file access;
- command execution;
- context selection;
- repository exploration;
- interaction with MCP servers;
- skill invocation;
- spawning or delegating to sub-agents;
- evaluating intermediate results;
- deciding when more information is needed.

Hard-coding the entire orchestration process in Python duplicates capabilities already available to the agent.

It also creates several problems.

### 3.1 Reduced agent autonomy

A rigid Python workflow can force the agent through steps that are unnecessary for the current Task.

### 3.2 Excessive implementation complexity

Every new workflow branch requires additional orchestration code.

### 3.3 Poor adaptability

Different Tasks require different depths of investigation, planning, validation, and review.

A fixed script handles this less naturally than an agent operating inside explicit constraints.

### 3.4 Platform coupling

A Python-heavy orchestration engine risks becoming tightly coupled to one runtime and one execution style.

Our goal is a portable Orchestrator that can work with:

- Codex;
- Claude;
- GitHub Copilot;
- Antigravity;
- other future agent platforms.

### 3.5 Duplication of reasoning logic

The workflow engine should not attempt to encode in Python decisions that a capable agent can already make safely from structured rules and state.

---

## 4. New mental model

The new model is:

> The Orchestrator is an Agent.  
> The workflow graph defines the allowed process.  
> Skills define how specialized work is performed.  
> Knowledge sources provide facts and project context.  
> The deterministic core guarantees state integrity and safety.

Conceptually:

```text
Agent decides
     ↓
Graph constrains
     ↓
Skills guide
     ↓
Knowledge informs
     ↓
Tools execute
     ↓
Core validates and persists
```

---

## 5. Global Orchestrator Agent

There is one main agent that owns the active development session.

Its role is broader than that of a normal implementation agent.

The Orchestrator Agent is responsible for:

```text
understanding
planning
routing
context management
delegation
artifact management
validation
user interaction
workflow progression
```

It is the process conductor.

The agent does **not** need the entire workflow encoded as imperative Python.

Instead, it receives structured information about:

- current Task state;
- Workflow Graph;
- Project Profile;
- available skills;
- available tools;
- artifact contracts;
- current repository state;
- Project Knowledge Graph;
- relevant memory;
- transition rules.

It reasons over these inputs and decides the next valid action.

---

## 6. Workflow Graph

The Workflow Graph remains a central architectural component.

However, its role changes.

It is no longer primarily an execution graph interpreted by a Python controller.

It becomes the **navigation and policy model for the Orchestrator Agent**.

Example:

```text
created
   ↓
preparing
   ↓
context
   ↓
analysis
   ↓
specification
   ↓
planning
   ↓
plan review
   ↓
ready
   ↓
active
   ↓
implementation
   ↓
code review
   ↓
testing
   ↓
documentation
   ↓
knowledge refresh
   ↓
acceptance
   ↓
completed
```

The graph defines:

- valid states;
- valid transitions;
- gates;
- loops;
- retry limits;
- possible failure routes;
- points where user input may be required.

The agent decides which valid path is appropriate based on the Task and current evidence.

---

## 7. Agent freedom vs deterministic constraints

The architecture must deliberately separate two categories.

### Agent-owned decisions

The agent should decide:

- how much context is required;
- which files need inspection;
- whether deeper analysis is necessary;
- which skills are relevant;
- whether a sub-agent is useful;
- which tools to invoke;
- whether new evidence invalidates the current Plan;
- whether the user must answer a question;
- which valid workflow route should be taken next.

### Deterministic constraints

Software should guarantee:

- valid Task transitions;
- artifact persistence;
- version consistency;
- required artifact existence;
- hashes / references;
- claims / leases when asynchronous execution is used;
- safe workspace rules;
- permissions;
- bounded retries where configured;
- immutable audit events;
- protection against destructive Git actions;
- machine-readable state.

This creates the core principle:

```text
Agent = intelligence and orchestration
Core  = guarantees and enforcement
```

---

## 8. The deterministic core

The term **Kernel** may be used conceptually for this minimal deterministic layer.

It is not a second orchestrator.

It does not determine the whole workflow.

It does not replace agent reasoning.

Its role is to provide reliable primitives.

Possible responsibilities:

```text
TaskManagerService
ArtifactStore
WorkflowStateStore
TransitionGuard
ExecutionWorkspaceManager
GraphProviderAdapter
MemoryStore
ToolRegistry
PolicyValidator
EventLog
```

The layer should remain small and deterministic.

Example:

```text
Orchestrator Agent:
"I have finished preparation and want to set this Task to READY."

Core:
- specification exists?
- plan exists?
- plan review approved?
- hashes match?
- blockers empty?

yes → transition accepted
no  → transition rejected with structured reason
```

The agent decides **why** it wants to transition.

The core guarantees that the transition is valid.

---

## 9. Skills

Skills are reusable specialist instructions and capabilities.

They tell the agent **how to perform a class of work**.

Examples:

```text
context-gathering
task-creation
analysis
planning
plan-review
implementation
code-review
security-review
testing
documentation
health-check
optimizer
debug-inspector
```

The Orchestrator Agent selects and invokes the relevant skills.

A skill may:

- guide the same agent;
- invoke tools;
- call an MCP service;
- delegate work to a specialized sub-agent.

Skills should remain atomic and reusable.

---

## 10. Sub-agents

Sub-agents are optional.

The architecture does not require that every workflow stage be implemented as a separate agent.

For v1, the Global Orchestrator Agent may execute most stages itself.

A sub-agent should be created only when there is practical value, such as:

- independent review;
- specialist expertise;
- isolation of large context;
- parallel investigation;
- security review;
- code review where independence matters.

Example:

```text
Orchestrator Agent
      │
      ├── Context work itself
      ├── Planning itself
      ├── Implementation itself
      │
      ├── Code Review Agent
      └── Security Review Agent
```

This avoids unnecessary multi-agent complexity.

---

## 11. Context management

The Orchestrator Agent owns active context management.

It should not load the entire repository and all previous history into every reasoning step.

Instead it selects context from:

```text
Task
Development Specification
Implementation Plan
Project Profile
Project Knowledge Graph
Project Memory
Repository
Documentation
Tool output
Previous artifacts
```

The agent should pass minimal useful context to skills and sub-agents.

Artifacts remain the primary durable communication mechanism between stages.

---

## 12. Project Knowledge Graph

The Knowledge Graph is a major information source for the Orchestrator Agent.

Example:

```text
Orchestrator Agent
       ↓
Project Knowledge Service
       ↓
Graphify Adapter
       ↓
Graphify MCP
       ↓
Local Project Graph
```

The graph can answer structural questions such as:

- which modules are related;
- who calls a function;
- which component owns an API;
- what depends on a changed module;
- what code belongs to a subsystem;
- which relationships exist between components.

The agent uses the graph to reduce blind repository exploration.

The graph informs decisions but does not itself control the workflow.

---

## 13. Project Memory

Project Memory is different from the Knowledge Graph.

Knowledge Graph:

```text
What exists in the project?
How is it connected?
```

Project Memory:

```text
What did we previously decide?
What constraints have we learned?
What conventions matter?
What important findings should survive sessions?
```

The Orchestrator Agent may use both.

```text
               Context
                  ↑
        ┌─────────┴─────────┐
        │                   │
 Knowledge Graph       Project Memory
```

---

## 14. Task state

Task state must remain external to the LLM conversation.

The current state should be stored deterministically.

Example:

```yaml
task:
  id: TASK-0042
  status: preparing
  type: implementation

artifacts:
  specification: SPEC-0042-v1
  plan: null

workflow:
  current_stage: planning

blockers: []

updated_at: ...
```

The Orchestrator Agent reads this state and proposes changes.

The state store validates and persists them.

The agent must not rely on conversational memory as the canonical Task state.

---

## 15. Artifact storage

Durable work remains artifact-based.

Example:

```text
.orchestrator/
├── tasks/
│   └── TASK-0042/
│       ├── task.yaml
│       ├── specification.md
│       ├── plan.md
│       ├── execution-package.yaml
│       └── events.jsonl
│
└── runs/
    └── RUN-0042-01/
        ├── run.yaml
        └── working/
            ├── context.json
            ├── analysis.json
            └── validation.json
```

The important architecture principle remains:

> Durable artifacts carry state between stages; full chat history does not.

---

## 16. Example execution

User says:

```text
"Payment calculation is broken."
```

The Global Orchestrator Agent receives the request.

### Step 1

The agent determines that this requires Managed Work.

It creates a Task through TaskManagerService.

```text
TASK-0042
status = created
```

### Step 2

The agent transitions the Task to `preparing`.

### Step 3

The agent invokes Context Gathering.

It may:

- query Graphify;
- inspect code;
- inspect documentation;
- run repository searches;
- inspect tests.

### Step 4

The agent determines whether enough evidence exists.

If not:

```text
expand context
```

or:

```text
ask user
```

### Step 5

The agent performs analysis and produces a Development Specification.

### Step 6

The agent creates an Implementation Plan.

### Step 7

A separate reviewer agent may review the Plan.

If approved, the agent requests:

```text
Task → ready
```

The deterministic core validates the gate.

### Step 8

The Orchestrator Agent starts execution.

It invokes Implementation skills and tools.

### Step 9

It invokes independent Code Review where configured.

### Step 10

It runs Testing.

### Step 11

It updates Documentation.

### Step 12

It refreshes the Knowledge Graph.

### Step 13

It performs final validation and moves to acceptance / completion.

The important difference is:

```text
There is no Python function manually hard-coding every reasoning decision.

The Agent owns orchestration.
The software layer provides reliable primitives and guards.
```

---

## 17. What Python is still used for

Python is still useful.

But its role changes.

Good Python responsibilities:

```text
Task persistence
artifact storage
Git operations
MCP adapters
Graphify integration
filesystem operations
test execution
workspace management
state validation
transition guards
hashing
locking
event logs
configuration loading
```

Poor Python responsibilities:

```text
hard-code every reasoning path
decide what context is semantically relevant
decide implementation strategy
decide whether investigation is sufficient
simulate agent reasoning using nested if/else workflow logic
```

Python provides capabilities.

The Agent orchestrates them.

---

## 18. Architecture overview

```text
                         USER
                           ↓
                ┌────────────────────┐
                │ ORCHESTRATOR AGENT │
                │                    │
                │ reasoning          │
                │ routing            │
                │ context            │
                │ delegation         │
                │ workflow control   │
                └─────────┬──────────┘
                          │
       ┌──────────────────┼──────────────────┐
       ↓                  ↓                  ↓
 Workflow Graph        Skills          Project Knowledge
                                               │
                                    ┌──────────┴──────────┐
                                    ↓                     ↓
                               Graphify              Memory
                                    │
                                    ↓
                                Code Graph

                          │
                          ↓
                ┌────────────────────┐
                │ Deterministic Core │
                │                    │
                │ Task Manager       │
                │ State Store        │
                │ Artifact Store     │
                │ Guards             │
                │ Workspace          │
                │ Tools              │
                │ Event Log          │
                └─────────┬──────────┘
                          │
                          ↓
                Repository / Tests /
                Git / Files / APIs
```

---

## 19. Core architecture principles

1. The **Global Orchestrator Agent is the conductor**.
2. The workflow must not be reduced to a large imperative Python script.
3. The Workflow Graph defines valid routes and gates.
4. The Agent chooses the route based on current evidence.
5. Skills define reusable specialist behavior.
6. Sub-agents are optional and created only when they add value.
7. Knowledge Graph provides structural project knowledge.
8. Project Memory preserves learned development knowledge.
9. Durable artifacts replace dependence on conversation history.
10. Task state is stored outside the model.
11. Deterministic software validates and persists critical state.
12. The deterministic core must remain thin.
13. Python implements primitives and infrastructure, not the intelligence of orchestration.
14. The architecture must remain platform-agnostic.
15. The same concepts should work with Codex, Claude, Copilot, Antigravity, and future development agents.

---

## 20. Architectural shift

The project direction changes from:

```text
PYTHON ORCHESTRATOR
controls
AGENT
```

to:

```text
ORCHESTRATOR AGENT
uses
DETERMINISTIC SERVICES
```

Or even more simply:

```text
OLD

Python
  ↓
Workflow
  ↓
Agent


NEW

Agent
  ↓
Workflow Graph + Skills + Knowledge
  ↓
Deterministic Tools / State / Guards
```

This is the central architectural decision.

---

## 21. Next architecture work

After accepting this decision, the existing AI Orchestrator design should be reviewed and components classified into three groups.

### Keep as deterministic services

Examples:

```text
TaskManagerService
Task Registry
Artifact Store
Execution Workspace Manager
Graphify Adapter
Project Knowledge Service infrastructure
Event Log
state-transition validation
```

### Convert from controller logic to Agent instructions / workflow rules

Examples:

```text
routing decisions
context expansion decisions
analysis routing
planning depth
review remediation routing
test failure classification
documentation routing
```

### Keep as reusable Skills

Examples:

```text
Task Creator
Context Gathering
Analysis
Planning
Plan Review
Implementation
Code Review
Testing
Documentation
Security Review
Health Check
```

The next design phase should therefore be an **architecture refactor from controller-centric to agent-centric orchestration** rather than implementation of additional Python workflow control.
