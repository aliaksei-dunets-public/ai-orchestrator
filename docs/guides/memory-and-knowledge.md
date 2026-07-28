---
language: en
translation_of: docs/guides/memory-and-knowledge-ru.md
---

# Orchestrator Memory and Knowledge Graph

Project Memory stores observations, decisions, lessons, and explicitly
approved instructions. Knowledge Graph stores structured project entities and
relations. Retrieval selects relevant current data and builds a bounded Context
Pack for the agent.

The architecture contract is in [core architecture](../architecture/orchestrator-core.md),
the task workflow is in [the Task Layer contract](../architecture/task-layer.md),
and the design decision is in [ADR-0002](../adr/0002-project-memory-knowledge-lifecycle.md).

## 1. Task creation comes first

The orchestrator does not modify code directly from a request. Task Creation
Workflow builds a Task Context with the goal, behavior, scope, affected
components, constraints, risks, acceptance criteria, plan, and open questions.
`quick`, `standard`, and `deep` modes use bounded context budgets of 2048,
6144, and 12288 characters. A deep task requires explicit approval of its
selected approach.

## 2. Fresh Context Pack

Before task creation and task execution, retrieval rebuilds a fresh bounded
pack from these target-owned stores:

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

Retrieval excludes disabled, superseded, stale, secret-like, out-of-project,
Russian, mixed-language, and non-canonical sources. It is deterministic and
lexical: terms are normalized, records receive stable scores, related graph
nodes are traversed for at most two hops, and the result is bounded to the
selected budget and 32 records. No embeddings, external database, or
cross-project memory is used.

An empty or irrelevant store is a valid no-op; the orchestrator does not fill
missing evidence with guesses.

## 3. Knowledge source policy

Only English canonical documents with valid provenance are eligible for graph
proposals and writes. Russian companion files remain useful for readers but are
not graph sources. Mixed-language, unknown-language, metadata-less, generated,
release, and aliased sources are rejected before graph writes.

The `knowledge-curator` creates a proposal. Onboarding includes that proposal in
its preview and applies it only after hash-bound approval. Empty `nodes` and
`edges` are valid no-ops.

## 4. Finalization and promotion

Task finalization runs documentation, knowledge, and memory gates in that order.
Authoritative observations, decisions, and lessons may be promoted
automatically. Instructions and non-authoritative sources require approval
bound to proposal and source hashes. The graph remains navigation-only and is
never a second source of truth.

## 5. Source and proposal examples

```text
decision:
RBAC for the API uses the existing AuthorizationService.
source: docs/adr/0010-api-authorization.md
```

```text
component: reports-api
contract: report-contract
component: authorization-service

reports-api implements report-contract
reports-api depends_on authorization-service
```

```text
Scope:
- add /reports;
- use AuthorizationService;
- add unit and scenario tests.

Out of scope:
- change the role model;
- change the public authorization contract;
- add a new identity system.
```

```text
Acceptance:
- endpoint is available only to permitted roles;
- unauthorized requests receive the expected response;
- existing tests pass;
- new tests pass.
```

```text
claim task
→ read Task Context
→ validate freshness
→ retrieve fresh Context Pack
→ implement plan
→ run tests
→ task/code review when required
→ security review
→ documentation
→ Task Finalization
→ finalization receipt
→ commit
→ complete
```

```text
kind: lesson
content: Check RBAC before building the endpoint response.
confidence: 0.8
requires_approval: true
```

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/memory/approvals.jsonl
```

```text
.orchestrator/knowledge/ontology.json
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

```text
document
component
contract
decision
task
risk
```

```text
defined_by
depends_on
implements
affects
supersedes
produced_by
```

```text
.orchestrator/knowledge/indexes/
```

```text
decision: all API endpoints use AuthorizationService
component: reports-api
reports-api depends_on authorization-service
lesson: check RBAC before building the response
```

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/memory/approvals.jsonl
.orchestrator/knowledge/ontology.json
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

```text
.orchestrator/tasks/tasks.json
.orchestrator/tasks/checkpoints/
.orchestrator/memory/proposals/
.orchestrator/knowledge/indexes/
.orchestrator/migrations/backups/
.orchestrator/releases/
releases/
.agents/
```

```powershell
python -m orchestrator context --root . --mode standard --task-context "Add /reports endpoint" --path orchestrator/reports.py
```

```powershell
python -m orchestrator memory --root . propose --kind lesson --content "Check RBAC before building the response" --source reports/session.md --confidence 0.8
```

```powershell
python -m orchestrator memory --root . list
```

```powershell
python -m orchestrator knowledge --root . add-node --id reports-api --kind component --label "Reports API" --source docs/architecture/api-contract.md
```

```powershell
python -m orchestrator knowledge --root . rebuild
```
