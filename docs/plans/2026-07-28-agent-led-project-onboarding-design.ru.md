# Agent-led Project Onboarding Design

**Date:** 2026-07-28
**Status:** approved by the user
**Mode:** deep
**Core placement:** in-place Git submodule or copied package

## Problem

The current onboarding implementation can collect repository facts and render a
Project Context, but it does not provide a complete agent-led workflow. The
deployment guide therefore exposes internal Python APIs and asks the user to
coordinate installation, profile selection, preview, approval, validation and
rollback manually.

The desired experience starts when the user adds AI Orchestrator as a Git
submodule or copies the package into or next to the target project, then gives
the agent the path to `skills/system/project-onboarding/SKILL.md`. The agent must lead
the entire onboarding conversation and invoke deterministic scripts for
inspection, planning, application and rollback.

## Approved decisions

1. The workflow is platform-neutral and agent-led.
2. The Git submodule or copied package is the active core in place; onboarding
   does not copy it into `.orchestrator/core`.
3. The agent asks questions only when evidence is ambiguous and immediately
   before the first write.
4. Every question contains explicit choices, descriptions and one recommended
   option when a safe recommendation exists.
5. The user receives one complete preview before approval.
6. Approval includes authorization for automatic rollback when validation
   returns `ERROR` or `CRITICAL`.
7. Project integration is persisted in `.orchestrator/config.json` and a short
   managed bootstrap block in the active platform instruction surface.
8. Full workflow instructions remain in the canonical skill; they are not
   copied into always-loaded platform instruction files.

## Architecture

The declarative `project-onboarding` workflow coordinates deterministic
operations and interaction gates:

```text
discover-core
→ inspect-target
→ resolve-platform
→ resolve-technologies
→ collect-project-context
→ prepare-preview
→ request-approval
→ apply-project-integration
→ validate-health
→ validate-idempotency
→ finalize-report
```

The Python implementation is split into two layers:

- `orchestrator.onboarding` retains evidence collection and Project Context
  rendering;
- `orchestrator.onboarding_workflow` owns structured questions, planning,
  stale-preview protection, managed instruction blocks, atomic publication,
  validation and rollback.

The canonical `project-onboarding` skill invokes a repository-local script. The
script resolves core root relative to its own `SKILL.md` location and exposes
machine-readable `inspect`, `plan`, `apply` and `rollback` operations. It does
not call `input()` and does not render platform UI.

## Interaction contract

When information is missing or ambiguous, the workflow returns
`status: needs_input` and structured questions:

```json
{
  "id": "platform_profile",
  "prompt": "Which platform profile should be activated?",
  "choices": [
    {
      "id": "codex",
      "label": "OpenAI Codex",
      "description": "Use the stable Codex adapter.",
      "recommended": true
    }
  ]
}
```

The agent adapter presents the question using native host capabilities and
passes the selected choice back to the planning script. Headless callers may
provide the same answers as versioned JSON. Unknown question IDs, unknown
choice IDs, duplicate choices and credential-like values fail closed.

## In-place core discovery

The skill derives core root from:

```text
<core>/skills/system/project-onboarding/SKILL.md
```

The workflow validates that core contains:

- `orchestrator/`;
- `config/`;
- `profiles/`;
- `registries/`;
- `skills/`;
- `workflows/`.

The project config stores a relative `core_path` whenever core can be expressed
relative to the target project. An external absolute path requires an explicit
portability answer. The config records core version, mode `in_place`, active
platform profile and technology profiles.

## Platform adapters

Platform profiles declare onboarding metadata rather than forcing Core to
branch on platform names:

- instruction target;
- repository skill projection target;
- interaction adapter;
- approval adapter.

Expected instruction targets are `AGENTS.md` for Codex,
`.github/copilot-instructions.md` for GitHub Copilot and `CLAUDE.md` for
Claude. Google Antigravity uses its repository skill projection while its
persistent instruction target remains unverified.

Instruction updates are bounded by ownership markers:

```markdown
<!-- ai-orchestrator:start -->
AI Orchestrator core: `tools/ai-orchestrator`
Load `.orchestrator/config.json` before task routing.
Use `skills/system/project-onboarding/SKILL.md` for onboarding.
<!-- ai-orchestrator:end -->
```

Existing user content is preserved byte-for-byte outside the managed block.
Missing or conflicting ownership markers block application.

## Project-owned and operational state

Tracked project integration:

```text
.orchestrator/config.json
.orchestrator/project-context.md
.orchestrator/onboarding/report.json
```

Operational state:

```text
.orchestrator/onboarding/session.json
.orchestrator/onboarding/backups/
.orchestrator/tasks/tasks.json
.orchestrator/telemetry/
```

Onboarding previews required `.gitignore` additions before applying them.
Sessions contain paths, hashes, answers and statuses, but never prompts,
credentials, secret-file contents or complete tool output.

## Preview and stale approval

The plan contains:

- selected core and profiles;
- every file to create or update;
- complete Project Context diff;
- complete instruction-file diff;
- `.gitignore` diff;
- validation commands;
- rollback manifest;
- a deterministic `plan_hash`.

Approval is tied to `plan_hash` and a target fingerprint. If any planned input
changes after preview, `apply` returns `stale_preview` without writing and the
agent must produce a new preview.

## Apply and rollback

Before publication, onboarding stores recoverable copies of every existing file
it owns or plans to update. New content is written to temporary files in the
same directory, flushed and published with `os.replace`.

After publication the workflow validates:

1. project config contract;
2. managed instruction block;
3. Project Context ownership markers;
4. core Health Check;
5. project Task Registry health;
6. second onboarding dry-run is empty.

An `ERROR` or `CRITICAL` result triggers the pre-approved rollback. Rollback
restores previous files, removes only files created by the same session and
verifies the restoration hashes. The terminal result is `completed`,
`rolled_back` or `rollback_failed`.

## Testing

The validation matrix covers:

- contract validation for workflow, profiles, project config, interaction and
  session schemas;
- unambiguous inspection without unnecessary questions;
- platform and technology ambiguity;
- complete preview and approval hash;
- user cancellation before writes;
- instruction content preservation;
- stale-preview rejection;
- idempotent second onboarding;
- automatic rollback on health failure;
- secret-safe session serialization;
- agent script JSON interfaces;
- Codex, Antigravity, Copilot and Claude adapter metadata;
- canonical skill projection drift;
- documentation links and repository Health Check.

## Out of scope

- interactive `input()` prompts inside Core or scripts;
- a user-facing `orchestrator onboard` wizard;
- copying in-place core into `.orchestrator/core`;
- downloading releases or modifying global Python installations;
- vendor-specific UI automation;
- weakening immutable security policies;
- automatically resolving conflicting ownership markers.
