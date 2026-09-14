---
language: en
---

# Component contracts

## Core

- Inputs: defaults, policies, registries, profiles, Project Context, and task instructions.
- Outputs: selected workflow, structured findings, and session result.
- Does not own: project business rules or platform-specific tool syntax.

## Task Creator

- Inputs: user request, Project Context, profiles, and repository evidence.
- Outputs: validated Task Context draft.
- Does not own: Task Registry or execution status.

## Task Manager

- Inputs: validated Task Context, legal transition, and a schema-valid finalization receipt for `complete`.
- Outputs: registry result, safe context/checkpoint paths, and terminal receipt digest.
- Owns safe path calculation, checkpoint deletion after `done`, and registry status.
- Does not own planning, implementation, semantic reviews, commits, documentation, graph curation, or memory content.
- In `serial` mode it preserves one active slot. In `isolated_parallel` it stores run, sequence, workspace, branch, base, and commit assignment.
- Registry mutations are serialized by `RegistryLock`; stale locks are recovered only after live-owner checks.

## Worktree Manager

- Inputs: Git repository root, validated worktree root, task ID, run ID, and full base commit.
- Outputs: task-owned branch/worktree assignment, ownership inspection, commit verification, integration, and guarded cleanup.
- Owns safe Git argument arrays, path/branch derivation, and ownership manifests.
- Does not own Task Registry status, automatic conflict resolution, or deletion of failed worktrees.

## Task Execution Workflow

- Inputs: claimed Task Context, capabilities, limits, and assigned workspace.
- Outputs: Execution Record, bounded evidence, optional telemetry, finalization receipt, and status request.
- Does not own Task Manager transition rules.
- Context and checkpoint must remain inside the assigned workspace; silent workspace switching is forbidden.

## Task Finalization Coordinator

- Inputs: task ID, context revision/baseline hash, completed checkpoint, changed paths, documentation dispositions, knowledge proposal, and memory candidates.
- Outputs: versioned receipt with digest bindings, gate statuses, store digests, promoted memory IDs, and pending approval hashes.
- Owns documentation → knowledge → memory ordering, deterministic validation, safe apply, and recovery.
- Does not own semantic content quality; each specialist remains the owner of its decision.
- Empty graph proposals and empty memory candidate lists are explicit valid no-ops. Missing disposition is not a no-op.

## Telemetry

- Inputs: numeric counters and identifiers without prompt, tool, or evidence payloads.
- Outputs: project-local JSONL events and CLI summaries.
- Does not own Task Registry status, Task Context, review verdicts, or permanent memory.

## Independent Reviewer

- Inputs: one bounded `ReviewerRequest` containing task scope, acceptance
  criteria, compact context, changed paths, diff summary, and test evidence.
- Outputs: structured `IndependentReviewerResult` findings and numeric token
  usage only; the request is read-only and grants no Core, Git, registry,
  memory, knowledge, approval, or finalization authority.
- Admission is limited to one reviewer for deep, high/critical, security,
  migration, persistence, public-API, irreversible, or challenged-blocking
  work. Unsupported native isolation uses the clean-context fallback.
- Native invocation is supplied by the active platform adapter; Core does not
  import a host API or store reviewer prompts, raw tool output, or evidence in
  telemetry.
- Does not own implementation writes, Git state, Task Registry transitions,
  approvals, finalization, memory, or Knowledge Graph content.

## Workflow Engine

- Inputs: declarative workflow, capability registry, and current workflow state.
- Outputs: next legal step, gate, or terminal result.
- Does not own domain logic in skills.

## Project Onboarding

- Inputs: onboarding skill, target root, repository evidence, and versioned answers.
- Outputs before approval: structured questions or a complete preview with `plan_hash`, fingerprint, validation steps, and rollback manifest.
- Outputs after approval: `completed`, `rolled_back`, or `rollback_failed` with a bounded report.
- Owns managed Project Context blocks, onboarding reports/backups, limited platform bootstrap, and Git ignore blocks.
- Does not own user text outside ownership markers, platform UI, core loading, global Python, or policy weakening.
- Apply is allowed only for an unchanged fingerprint and approved `plan_hash`; an `ERROR` or `CRITICAL` after write invokes the approved rollback.

## Skills

- Inputs and outputs are defined by each skill contract.
- Outputs: structured result, evidence, or a request for the next workflow step.
- Does not own orchestration state, Task Registry, or platform tool lifecycle.
- A coordinator may route atomic skills but must not duplicate their domain logic.
- Canonical sources are `skills/system`, `skills/bundled`, and `skills/optional`; project-owned sources are under `.orchestrator/project-skills`.
- Installer publishes projections atomically. Health Check detects missing selections, ID collisions, and drift.

## Memory and Knowledge

- Inputs: proposals, project-relative provenance, source digests, and hash-bound approval where required.
- Outputs: canonical entries/events/approvals, ontology/nodes/edges, and reproducible indexes.
- Does not own: business truth outside canonical sources or automatic instruction promotion.
- Target projects own canonical stores; Core owns runtime, schemas, immutable ontology, and policy.
- Effective state excludes disabled, superseded, stale, secret-like, Russian, mixed-language, and non-canonical sources.
- Retrieval is deterministic lexical selection and bounded graph traversal without embeddings or an external database.
- The graph is navigation-only and never a second source of truth.
- Task finalization promotes only authoritative observation/decision/lesson proposals automatically; instructions and non-authoritative sources require approval.
- Session Reporter runs once after the execution/backlog loop stops and emits proposals without changing task status.

`knowledge-curator` additionally owns read-only source inventory, onboarding
graph proposals, provenance/ontology validation, canonical merge, and index
rebuild. `project-onboarding` owns only target bootstrap, preview, approval,
apply, and rollback.
