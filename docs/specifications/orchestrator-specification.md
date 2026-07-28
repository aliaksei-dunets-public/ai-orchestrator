---
language: en
---

# Universal AI Orchestrator

## Architecture specification and roadmap

**Version:** 0.5
**Status:** normative architecture specification
**Language:** English

## 1. Purpose

AI Orchestrator is a portable, configurable core for development tasks,
skills, workflows, quality checks, documentation, memory, and knowledge. It is
distributed as a separate Git repository and attached to target projects
without a hard dependency on a particular technology or agent platform.

The product supports managed mode (a Git submodule with controlled core
updates) and standalone mode (an independently evolved copy).

## 2. Principles

1. The core does not know a target project's business domain.
2. Project behavior is defined by profiles, Project Context, and permitted
   overrides.
3. Every skill has one primary responsibility and an explicit contract.
4. Workflows compose skills and approval gates; a coordinator does not copy
   the responsibilities of atomic skills.
5. Task Manager is a small state machine, not an implementation engine.
6. Small tasks use a reduced workflow with the same immutable safety gates.
7. Autonomous work is bounded by limits and stop conditions.
8. Self-improvement is proposal- and approval-driven.
9. Every capability has documentation and a test scenario.
10. Immutable security policies cannot be weakened by local overrides.

### 2.1. Normative sources of truth

This document defines architecture boundaries, the product lifecycle, and the
roadmap. `task-layer-specification.md` is the source of truth for Task Context,
Task Registry, statuses, transitions, and the Task Manager CLI. When the two
documents overlap, the narrower Task Layer contract governs its own interfaces.

The terms **MUST**, **MUST NOT**, and **SHOULD** are normative. Examples and
target commands are not implemented capabilities until their roadmap phase is
complete.

## 3. Architecture layers

### 3.1. Core

Loads configuration, profiles, registries, and policies; selects workflows;
enforces mandatory checks; and produces a session result.

### 3.2. Task Layer

Contains Task Creator, Task Context, Task Manager, and Task Execution Workflow.
The detailed contract is in `task-layer-specification.md`. Serial execution
uses the primary workspace and the user-selected current branch; task-owned
branch, worktree, integration, and cleanup lifecycle require an explicit
isolated assignment.

### 3.3. Workflow Engine

Runs declarative scenarios, transitions, retries, errors, fallbacks, and user
approval gates.

### 3.4. Skills

`skills/` is the canonical source for portable skills. Skills are distributed
as `system`, `bundled`, or explicitly approved `optional` packages. Generated
platform projections such as `.codex/skills/` and `.agents/skills/` MUST be
rebuilt from canonical sources and MUST NOT be edited manually.

The `task-creator` skill coordinates classification, analysis, specification,
planning, review, and validation. Atomic skills include task management,
analysis, plan writing, implementation, testing, review, security,
documentation, memory, knowledge, health, audit, and improvement design.

### 3.5. Registries

Skills, workflows, capabilities, platform profiles, technology profiles,
templates, and policies are described by registries. A skills registry records
release-level availability and distribution; project configuration records the
selected optional skills.

### 3.6. Platform Profiles

Profiles describe shell, Git, MCP, virtual URI, sub-agent, parallelism,
interaction, memory, commit, and pull-request capabilities. Profiles declare
`stable` or `experimental` maturity and provide both contract-matrix and
native-smoke evidence before claiming stable support. The initial target
profiles are OpenAI Codex, Google Antigravity, GitHub Copilot VS Code, and
Claude VS Code.

### 3.7. Technology Profiles

Technology profiles describe repository layout, build and test commands,
review rules, security tools, documentation conventions, and technology
overrides. Detection is read-only and does not install optional skills.

### 3.8. Project Context

Project Context records purpose, architecture, modules, business rules,
conventions, ADRs, commands, critical areas, security constraints, and local
documentation. It is the project-owned source of context.

### 3.9. Project Overrides

Overrides may select optional skills, permitted providers, templates, workflow
steps, quality gates, and platform fallbacks. They MUST NOT edit the core or
weaken system skills and immutable security policies.

### 3.10. Memory and Knowledge

Session Reports provide evidence for Project Memory and Orchestrator Memory.
Knowledge Graph records navigation entities and relations with source
provenance and supersede history. English canonical documents are the only
graph sources; Russian user-document companions are never graph sources. Empty
or irrelevant stores are valid no-ops.

## 4. Configuration hierarchy

Configuration is loaded in this order:

1. core defaults;
2. core policies;
3. platform profile;
4. technology profiles;
5. Project Context;
6. project overrides;
7. task-specific instructions;
8. current-session user instructions.

Each layer can override only permitted settings. Immutable security policies
have unconditional priority.

## 5. Repository structure

```text
ai-orchestrator/
├── README.md
├── AGENTS.md
├── CHANGELOG.md
├── ROADMAP.md
├── docs/{architecture,adr,guides,migrations,plans,specifications,validation}/
├── orchestrator/
├── config/schemas/
├── registries/
├── capabilities/
├── skills/
├── workflows/
├── profiles/{platforms,technologies}/
├── templates/
├── memory/
├── knowledge/
├── tests/{unit,contracts,scenarios,regression,sandbox-projects}/
├── examples/
└── releases/
```

Target-project operational state lives in `.orchestrator/`. Task Registry,
temporary files, locks, proposals, indexes, and checkpoints are not portable
source and are excluded from Git. Contexts, plans, code, tests, and canonical
documentation are versioned.

## 6. Project Onboarding

Onboarding is a read-first, agent-led workflow. It discovers the active core,
examines platform, stack, repository structure, commands, conventions, ADRs,
and security constraints, then creates a Project Context and a complete write
preview. Approval is bound to the preview hash and source fingerprint.

After one explicit approval, onboarding atomically publishes project config,
context, platform bootstrap, skill projections, and Git ignores. It validates
schemas, registries, Health Check, Task Registry, and idempotency. A failed
`ERROR` or `CRITICAL` check restores the backup manifest. Manual edits outside
owned blocks are preserved.

## 7. Orchestrator Health Check

Health Check deterministically checks required files, schemas, registry links,
profile compatibility, Project Context, tools, Task Registry integrity, active
task limits, versions, and unknown settings. Findings are `INFO`, `WARNING`,
`ERROR`, or `CRITICAL`.

```bash
orchestrator health
orchestrator health --json
orchestrator health --strict
orchestrator health --scope tasks
```

Automatic repair is limited to safe, deterministic operations.

### 7.1. Execution telemetry

Runtime may write numeric events to `.orchestrator/telemetry/events.jsonl`.
Telemetry can include duration, attempts, retries, tool calls, handoffs, and
provider-reported usage, but MUST NOT contain prompts, tool output, or evidence
payloads. It is operational state and never replaces Task Context or the
Execution Record.

## 8. Orchestrator Audit

Audit is a semantic review separate from Health Check. It finds contradictory
instructions, duplicate skills, unreachable workflows, stale documentation,
architecture drift, test gaps, and recurring Session Report problems. Audit is
read-only and emits evidence-based improvement proposals.

## 9. Task lifecycle

```text
user request → task creation → context validation → registration → claim
→ freshness validation → implementation → tests → required reviews
→ security review → user review when required → documentation
→ task finalization → commit → done → session report
```

Freshness, implementation, tests, security review, and task finalization are
mandatory for every route. Quick low-risk work may use review fast paths;
standard work uses task and code review; deep or high-risk work requires
independent review. `done` is allowed only after a valid finalization receipt.

## 10. Memory and knowledge

Session Reports record work, decisions, issues, and recommendations. Project
Memory stores durable observations, decisions, and lessons. Knowledge Graph
stores structured entities and relations with provenance and supersede history.
Memory promotion and knowledge changes are approval-gated where required.
Observations do not become permanent instructions automatically.

## 11. Test strategy

The project uses unit, contract, scenario, regression, sandbox, cross-platform,
and dogfooding tests. Repository-wide retrieval uses canonical sources and
excludes `releases/` by default; release validation names a release path
explicitly.

## 12. Roadmap

The roadmap preserves phases 0–23 and their dependency order:

| Phase | Deliverable |
| --- | --- |
| 0 | Architecture foundation |
| 1 | Repository scaffold |
| 2 | Minimal Health Check |
| 3 | Session Reporter |
| 4 | Minimal Task Manager |
| 5 | Quick Task Creator |
| 6 | Standard Task Creator and Plan Review |
| 7 | Implementation Runner |
| 8 | Test Design and Runner |
| 9 | Task Review |
| 10 | Code Review |
| 11 | Security Review |
| 12 | User Review and approval gates |
| 13 | Documentation Manager |
| 14 | Project Onboarding |
| 15 | Platform Profiles |
| 16 | Technology Profiles |
| 17 | Project Memory |
| 18 | Knowledge Graph |
| 19 | Backlog Loop |
| 20 | Orchestrator Audit |
| 21 | Controlled Self-Improvement |
| 22 | Multi-Project Validation |
| 23 | Stable Release 1.0 |

Task Layer milestones T0–T9 refine these phases and are not a second backlog:
T0 contracts; T1–T3 Task Manager; T4 Quick Creator; T5–T6 Standard/Deep
Creator and validation; T7 execution integration; T8 backlog loop; T9 platform
validation.

## 13. Phase Definition of Done

A phase is complete when its scope, registries, schemas, documentation, tests,
demonstration scenario, applicable Health Check, constraints, and next backlog
are recorded. Releases also require a Session Report and release notes.

## 14. First practical release 0.1.0

The first practical release includes the repository scaffold, registries and
schemas, placeholder skills and workflows, Health Check, Session Reporter,
JSON Task Registry and CLI, Quick Task Creator, one execution workflow, a
sandbox project, and an end-to-end scenario.

## 15. Self-improvement policy

The orchestrator may collect observations and issue proposals. Changes to a
skill, workflow, policy, or core are ordinary development tasks requiring
approval, tests, release notes, and rollback instructions. Automatic mutation
of the core is forbidden.
