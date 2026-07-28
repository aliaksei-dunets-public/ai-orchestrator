# Agent-led Project Onboarding Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** Deliver a complete agent-led, platform-neutral onboarding workflow that uses an in-place core, asks only necessary questions, applies one approved preview and automatically rolls back failed validation.

**Architecture:** A declarative workflow coordinates a platform-neutral state machine. The canonical onboarding skill invokes JSON-producing scripts, while platform profiles declare instruction and interaction adapters without platform-name branches in Core.

**Tech Stack:** Python 3.11+, Python standard library, JSON/JSON Schema draft 2020-12, YAML-compatible declarative assets, Markdown and `unittest`.

## Global Constraints

- Preserve unrelated user changes and content outside managed ownership markers.
- Do not copy an in-place core or require users to call internal Python APIs.
- Do not read ignored secret files or persist credential-like answers.
- Do not weaken immutable security or self-improvement policies.
- Bind approval to a deterministic preview hash and fail closed on stale input.
- Use atomic writes and a recoverable rollback manifest for project-owned files.
- Keep Core platform-neutral; adapter paths and interaction modes belong to profiles.

## Deliverables

- Registered `project-onboarding` workflow.
- Project config, interaction and onboarding session schemas.
- Platform onboarding metadata for all four profiles.
- Platform-neutral onboarding coordinator with inspect, plan, apply and rollback.
- Agent-invoked onboarding script in the canonical skill.
- Contract and scenario coverage.
- Updated specifications, component contracts and deployment guide.

## Dependencies

- Existing onboarding fact collection and Project Context renderer.
- Existing platform and technology profile loaders.
- Existing Health Check and Task Registry validation.
- Existing canonical skill projection installer.

## Acceptance Criteria

- AC1: An agent can locate Core from `skills/system/project-onboarding/SKILL.md` and inspect a target without writes.
- AC2: Unambiguous evidence produces no unnecessary questions; ambiguity returns structured choices with descriptions and a recommendation when safe.
- AC3: The preview includes every planned file diff, validation step, rollback entry and a deterministic approval hash.
- AC4: Apply rejects missing approval or a changed target fingerprint before writing.
- AC5: Apply writes `.orchestrator/config.json`, Project Context, platform bootstrap instructions and Git ignores while preserving user-owned content.
- AC6: Validation `ERROR` or `CRITICAL` triggers the approved automatic rollback and verifies restoration.
- AC7: A second onboarding run is idempotent and preserves manual Project Context and instruction content.
- AC8: Core contains no platform-name branching; all instruction and interaction routing comes from validated profiles.
- AC9: Sessions and reports contain no secret-file contents or credential-like answers.
- AC10: Canonical skill, workspace projection, registries, schemas, specifications and deployment guide agree.

## Testing Strategy

- Contract tests validate schemas, workflow registration and platform metadata.
- Unit tests validate questions, path safety, ownership markers, hashes and serialization.
- Scenario tests validate inspect/plan/apply, stale approval, cancellation, idempotency and rollback.
- Existing onboarding, profile, skill projection, documentation and Health Check suites provide affected regression coverage.
- No regression-labelled test is required because this is a new feature rather than a fixed defect.

## Risks and Rollback

- Risk: an instruction update overwrites user content. Detection: byte comparison outside markers. Rollback: restore the session backup.
- Risk: approval applies to changed inputs. Detection: fingerprint mismatch. Rollback: reject before writes.
- Risk: profile-specific branches enter Core. Detection: contract test. Rollback: move routing data back into profiles.
- Risk: session stores secrets. Detection: deterministic redaction/validation tests. Rollback: refuse serialization and delete only the failed temporary session file.

## Implementation Tasks

### Task 1: Declarative contracts and adapter metadata

**Files:**

- Create: `config/schemas/project-config.schema.json`
- Create: `config/schemas/onboarding-interaction.schema.json`
- Create: `config/schemas/onboarding-session.schema.json`
- Create: `workflows/project-onboarding.yaml`
- Modify: `registries/workflows.json`
- Modify: `config/schemas/platform-profile.schema.json`
- Modify: `profiles/platforms/codex.yaml`
- Modify: `profiles/platforms/google-antigravity.yaml`
- Modify: `profiles/platforms/github-copilot-vscode.yaml`
- Modify: `profiles/platforms/claude-vscode.yaml`
- Test: `tests/contracts/test_onboarding_workflow.py`

**Interfaces:**

- Consumes: schema version 1 registries and platform profiles.
- Produces: validated project configuration, interaction, session and declarative workflow contracts.

**Acceptance:**

- Covers AC2, AC8 and the declarative portion of AC10.

**Tests:**

- `python -m unittest tests.contracts.test_onboarding_workflow tests.contracts.test_platform_profiles -v` passes.

- [ ] **Step 1:** Add contract tests for the new schemas, registry entry and profile metadata.
- [ ] **Step 2:** Run the focused contract tests and confirm they fail before implementation.
- [ ] **Step 3:** Add the minimal schemas, workflow registration and profile metadata.
- [ ] **Step 4:** Run the focused contract tests and existing platform profile tests.
- [ ] **Step 5:** Review the contract diff for platform-name branches and unsafe paths.

### Task 2: Read-only inspection, questions and deterministic planning

**Files:**

- Create: `orchestrator/onboarding_workflow.py`
- Test: `tests/unit/test_onboarding_workflow.py`
- Test: `tests/scenarios/test_agent_led_onboarding.py`

**Interfaces:**

- Consumes: core root, target root, platform/technology profiles and optional versioned answers.
- Produces: `needs_input`, `preview_ready` or `blocked` results with deterministic plan and target hashes.

**Acceptance:**

- Covers AC1, AC2, AC3, AC4, AC8 and AC9 before the first write.

**Tests:**

- `python -m unittest tests.unit.test_onboarding_workflow tests.scenarios.test_agent_led_onboarding -v` passes for inspect and plan cases.

- [ ] **Step 1:** Add failing tests for core discovery, ambiguity, secret-safe answers, complete preview and stale fingerprints.
- [ ] **Step 2:** Run the focused tests and record the expected failures.
- [ ] **Step 3:** Implement immutable result models, inspection and deterministic planning.
- [ ] **Step 4:** Run focused tests and existing onboarding scenarios.
- [ ] **Step 5:** Review question generation and persisted fields for unnecessary or sensitive data.

### Task 3: Atomic apply, validation, rollback and agent script

**Files:**

- Modify: `orchestrator/onboarding_workflow.py`
- Modify: `skills/system/project-onboarding/SKILL.md`
- Create: `skills/system/project-onboarding/scripts/onboard_project.py`
- Modify through installer: `.codex/skills/project-onboarding/`
- Test: `tests/scenarios/test_agent_led_onboarding.py`
- Test: `tests/contracts/test_skill_installation.py`

**Interfaces:**

- Consumes: approved plan hash and unchanged target fingerprint.
- Produces: `completed`, `rolled_back` or `rollback_failed`, plus bounded report and restoration evidence.

**Acceptance:**

- Covers AC4, AC5, AC6, AC7, AC9 and the skill-projection portion of AC10.

**Tests:**

- `python -m unittest tests.scenarios.test_agent_led_onboarding tests.contracts.test_skill_installation -v` passes.

- [ ] **Step 1:** Add failing apply, preservation, idempotency and rollback scenarios.
- [ ] **Step 2:** Run focused scenarios and confirm expected failures.
- [ ] **Step 3:** Implement atomic file publication, backup manifest, validation and rollback.
- [ ] **Step 4:** Add the agent-facing JSON script and update the canonical skill.
- [ ] **Step 5:** Regenerate the Codex skill projection and run focused plus projection tests.

### Task 4: Canonical documentation and final acceptance

**Files:**

- Modify: `docs/specifications/orchestrator-specification.md`
- Modify: `docs/architecture/component-contracts.md`
- Modify: `docs/guides/deployment-to-target-project-ru.md`
- Test: `tests/unit/test_documentation.py`

**Interfaces:**

- Consumes: implemented workflow, schemas and script commands.
- Produces: an agent-first deployment guide and synchronized canonical contracts.

**Acceptance:**

- Covers AC10 and documents every user-visible behavior from AC1 through AC9.

**Tests:**

- Documentation links resolve; focused documentation tests, full discovery and strict Health Check pass.

- [ ] **Step 1:** Replace the manual installer-first guide with the approved agent-led bootstrap and interaction flow.
- [ ] **Step 2:** Update canonical Project Onboarding and component ownership contracts.
- [ ] **Step 3:** Validate local links and documentation ownership impact.
- [ ] **Step 4:** Run all affected tests and full `unittest` discovery.
- [ ] **Step 5:** Run Code Review, Security Review, Health Check and finalize evidence.
