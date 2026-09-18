# Graphify Integration for AI Orchestrator

**Status:** Working architecture decision  
**Scope:** Project Knowledge Graph for AI Orchestrator  
**Current target stack:** Python + React / Vue  
**SAP / ABAP support:** planned later as a separate extension

---

## 1. Decision summary

For the first versions of AI Orchestrator, we do **not** plan to build a complete Knowledge Graph engine from scratch.

Instead, we plan to use **Graphify as the underlying graph engine / backend**, while keeping it behind an Orchestrator-owned abstraction layer.

The Orchestrator should not depend directly on Graphify internals.

```text
AI Orchestrator
      ↓
Project Knowledge Service
      ↓
Graph Provider Adapter
      ↓
Graphify
      ↓
Local Knowledge Graph
```

This keeps Graphify replaceable in the future while allowing us to reuse an existing graph platform now.

---

## 2. Why use Graphify instead of building the graph engine ourselves

The main value of Graphify for our project is that the difficult low-level graph work already exists:

- parsing source code;
- extracting entities;
- extracting relationships;
- graph persistence;
- graph querying;
- incremental updates;
- MCP-based access;
- local execution.

Therefore, our development effort should focus on:

```text
Orchestrator integration
+
Knowledge Service contracts
+
workflow integration
+
project-specific semantics
```

rather than rebuilding a generic graph engine.

---

## 3. Initial target stack

The first practical use case is the current project stack:

```text
Backend:
Python

Frontend:
React
or
Vue
```

SAP / ABAP is **not part of the first integration milestone**.

ABAP support should be treated as a later extension, most likely through an additional parser / extractor / semantic enrichment layer.

The architecture must therefore remain language-independent.

---

## 4. Local deployment model

The Knowledge Graph is intended to run **locally on the developer machine**.

```text
Developer PC
│
├── Project source code
├── Graphify
├── Local graph data
├── Graphify MCP server
└── AI Orchestrator
```

The graph itself remains local.

Graphify exposes the graph through MCP so that agents and the Orchestrator can query it without directly manipulating graph storage.

For the first version, the preferred communication model is:

```text
Orchestrator
    ↓
Project Knowledge Service
    ↓
Graphify MCP
    ↓
Local graph
```

A separate remote graph infrastructure is not required for v1.

---

## 5. Project Knowledge Service

Graphify should not be called directly from every workflow node.

We introduce an Orchestrator-owned component:

```text
Project Knowledge Service
```

Responsibilities:

- abstract the concrete graph provider;
- expose stable graph operations to the Orchestrator;
- hide Graphify-specific MCP details;
- manage graph freshness;
- track source revision;
- trigger initial indexing;
- trigger incremental refresh;
- normalize query results;
- later combine code graph information with Orchestrator memory.

Example conceptual API:

```text
initialize_project_graph()
refresh_graph()
get_node()
find_related_components()
find_dependencies()
find_callers()
find_callees()
find_path()
query_graph()
get_graph_status()
```

The exact API will be designed separately.

---

## 6. Graph provider abstraction

Graphify is the first provider, not a hard-coded dependency of the entire Orchestrator.

Possible configuration:

```yaml
project_knowledge:
  enabled: true

  graph:
    provider: graphify

    storage:
      mode: local

    transport:
      type: mcp
      mode: stdio
```

Future providers could be introduced without changing Development Workflow contracts.

---

## 7. Initial Load

When AI Orchestrator is connected to a project for the first time, the graph must be initialized.

```text
Project Onboarding
      ↓
Knowledge Graph enabled?
      ↓ yes
Initial Load
      ↓
Scan project source
      ↓
Build graph
      ↓
Persist graph locally
      ↓
Record source revision
```

The Initial Load should normally happen once per project or when the graph is missing / invalid.

The resulting graph becomes the baseline for future incremental updates.

---

## 8. Incremental graph updates

After Initial Load, the graph should not be rebuilt from scratch for every Task.

Preferred model:

```text
Existing graph
      ↓
Task execution changes source code
      ↓
Incremental graph refresh
      ↓
Graph updated only for affected areas
```

The update should happen near the end of the Development Workflow.

Preferred position:

```text
Implementation
    ↓
Code Review
    ↓
Testing
    ↓
Documentation
    ↓
Knowledge Graph Refresh
    ↓
Final Validation
    ↓
Commit
```

This gives Final Validation access to the graph corresponding to the implementation candidate.

---

## 9. Source revision tracking

The Knowledge Graph must know which source revision it represents.

Example metadata:

```yaml
knowledge_graph:
  provider: graphify
  source_revision: abc123
  updated_at: 2026-09-17T20:00:00Z
  status: fresh
```

The Orchestrator can compare:

```text
graph.source_revision
vs
repository current revision
```

Possible states:

```text
fresh
stale
missing
refreshing
failed
```

This enables deterministic freshness checks.

---

## 10. When to refresh the graph

The graph should not be refreshed continuously by default.

Recommended controlled refresh points:

### Project onboarding

```text
Initial Load
```

### Before context gathering

If the graph revision is behind the current project revision:

```text
check freshness
→ refresh if required
```

### Near the end of a Task

After code and documentation changes:

```text
incremental refresh
```

### Before final commit / completion

Verify:

```text
graph reflects current implementation candidate
```

This gives us predictable graph lifecycle management.

---

## 11. Graph usage during Task preparation

The graph is primarily useful during Context Gathering.

```text
User Request
    ↓
Task Creator
    ↓
Context Subgraph
    ↓
Project Knowledge Service
    ↓
Graphify
```

The Context node can ask questions such as:

```text
What components are related to this class/module?
Who calls this function?
What depends on this API?
What files participate in this subsystem?
What is the dependency path between A and B?
Which components may be affected by this change?
```

This reduces blind repository scanning and gives the agent a structured map of the codebase.

---

## 12. Graph vs Orchestrator Memory

The Knowledge Graph and Orchestrator Memory are different concepts.

### Graphify / Project Knowledge Graph

Represents mainly structural knowledge derived from the project:

```text
files
modules
classes
functions
imports
calls
inheritance
dependencies
interfaces
components
```

### Orchestrator Memory

Represents development knowledge accumulated over time:

```text
architectural decisions
task decisions
important findings
project conventions
known constraints
previous incidents
user decisions
```

These should remain separate stores.

```text
Project Knowledge Service
        ↓
 ┌───────────────┐
 │ Code Graph    │
 │ Graphify      │
 └───────────────┘
        +
 ┌───────────────┐
 │ Project Memory│
 │ Orchestrator  │
 └───────────────┘
        ↓
Context Gathering
```

The Context Subgraph can combine both sources.

---

## 13. Knowledge enrichment

The graph should not remain limited to raw parser output forever.

Over time, the Orchestrator may enrich it with higher-level project semantics.

Examples:

```text
module → belongs_to → subsystem
endpoint → implemented_by → service
service → reads → database model
feature → touches → components
component → documented_by → architecture document
```

However, enrichment should preserve provenance.

We should distinguish:

```text
directly extracted fact
inferred relation
manually configured relation
AI-enriched relation
```

This prevents inferred information from being confused with deterministic source-code facts.

---

## 14. SAP / ABAP future extension

ABAP support is deferred until after the Python / frontend integration is stable.

The future SAP layer should enrich the graph with SAP-specific objects.

Possible node types:

```text
ABAP Class
Interface
Function Module
CDS View
CDS Entity
Behavior Definition
Behavior Implementation
Service Definition
Service Binding
DDIC Table
Structure
Domain
Data Element
BAdI
Enhancement
Package
Transport Object
```

Possible relations:

```text
inherits
implements
calls
uses
reads
writes
selects_from
behavior_for
implemented_by
exposes
associated_with
depends_on
contained_in_package
```

The important architectural decision is that ABAP support should extend the same Project Knowledge Service rather than introduce a separate SAP-specific graph architecture.

---

## 15. Development Workflow integration

Target Development Workflow:

```text
Request Router
    ↓
Task Creator
    ↓
Task = preparing
    ↓
Context
    │
    └── Project Knowledge Service
            ↓
          Graphify
    ↓
Analysis
    ↓
Specification
    ↓
Planning
    ↓
Plan Review
    ↓
Task = ready
    ↓
Execution
    ↓
Implementation
    ↓
Code Review
    ↓
Testing
    ↓
Documentation
    ↓
Knowledge Graph Refresh
    ↓
Final Validation
    ↓
Commit / Complete
```

---

## 16. Recommended configuration

Candidate Project Profile:

```yaml
project_knowledge:
  enabled: true

  graph:
    enabled: true
    provider: graphify

    lifecycle:
      initial_load: true
      refresh_before_context_if_stale: true
      refresh_after_implementation: true
      full_rebuild_on_error: false

    revision_tracking:
      enabled: true

    transport:
      type: mcp
      mode: stdio

    storage:
      mode: local

  memory:
    enabled: true
```

The exact Graphify CLI / MCP configuration should be finalized during implementation after validating the concrete Graphify version and interfaces we choose.

---

## 17. Key architectural decisions

1. Do not build a generic Knowledge Graph engine from scratch for v1.
2. Use Graphify as the first graph backend.
3. Keep Graphify behind `Project Knowledge Service`.
4. Store the graph locally.
5. Use MCP as the integration boundary.
6. Perform a full Initial Load during project onboarding.
7. Use incremental updates after Initial Load.
8. Track the source revision represented by the graph.
9. Use the graph primarily during Context Gathering and impact analysis.
10. Refresh the graph near the end of Task execution before final validation.
11. Keep Code Graph and Orchestrator Memory separate.
12. Allow Project Knowledge Service to combine graph + memory when building context.
13. Preserve provenance for deterministic and inferred relationships.
14. Start with Python + React / Vue.
15. Add SAP / ABAP support later as an additional extractor / semantic extension.
16. Keep the architecture provider-independent so Graphify can be replaced if required.

---

## 18. Next design steps

```text
Project Knowledge Service contract
        ↓
Graph Provider Adapter contract
        ↓
Graphify Adapter
        ↓
Knowledge Graph lifecycle
        ↓
Context Subgraph integration
```

After that, implementation can begin with the Python / React / Vue project and Graphify as the first provider.
