---
language: en
translation_of: docs/guides/deployment-to-target-project-ru.md
---

# Deploy AI Orchestrator to a target project

**Guide version:** 2.0
**Target orchestrator version:** 1.2.0
**Primary flow:** agent-led onboarding with the core attached in place

## 1. Result

Attach AI Orchestrator as a Git submodule or copy the package into a separate
directory. That directory becomes the active core; onboarding does not copy the
core to `.orchestrator/core` and does not require a global Python install.

Point the agent to `skills/system/project-onboarding/SKILL.md`. The agent reads
the core and target project, asks only necessary questions, shows one complete
preview, requests approval immediately before writing, applies the approved
plan, validates configuration and Health Check, rolls back on `ERROR` or
`CRITICAL`, and reports the result.

Platform differences are declared by profiles for OpenAI Codex, Google
Antigravity, GitHub Copilot VS Code, and Claude VS Code; they are not encoded as
platform branches in the Python core.

## 2. Prerequisites

- a target project and write permission;
- Python 3.11 or newer;
- Git when using a submodule;
- a local AI Orchestrator checkout;
- an agent that can read the skill and run a local Python command.

Check the starting state:

```powershell
git status --short
python --version
```

Uncommitted user changes may exist and must be preserved. Ownership conflicts
block writes instead of being resolved automatically.

## 3. Attach the core

Recommended Git submodule flow:

```powershell
git submodule add <ORCHESTRATOR_REPOSITORY_URL> tools/ai-orchestrator
git submodule update --init --recursive
```

The skill is then at:

```text
tools/ai-orchestrator/skills/system/project-onboarding/SKILL.md
```

Alternatively copy the complete repository or release package into a separate
directory such as `target-project/tools/ai-orchestrator/`. Do not merge core
directories with same-named target directories. An external absolute core path
requires explicit confirmation.

## 4. Run onboarding through the agent

Send the agent:

```text
Onboard this project using:
tools/ai-orchestrator/skills/system/project-onboarding/SKILL.md
```

The user does not need to invoke internal Python APIs, modify `PYTHONPATH`, or
install the core globally. The deterministic script is
`skills/system/project-onboarding/scripts/onboard_project.py`; it returns JSON
and never uses interactive `input()`.

## 5. Approval and rollback

Onboarding is read-only until approval. The preview contains target files,
managed blocks, `plan_hash`, source fingerprint, validation steps, rollback
manifest, and the selected language policy. Approval applies only to that
preview. A changed fingerprint produces `stale_preview` and requires a new
preview. A failed `ERROR` or `CRITICAL` invokes the approved rollback and keeps
the report for diagnosis.

## 6. After onboarding

Run `orchestrator health --strict --json`, inspect the generated projection,
and verify that canonical English sources are used for graph onboarding and
retrieval. Russian guide companions remain available to users but are never
ingested as Knowledge Graph sources.

## 7. Operational command reference

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py inspect --target .
```

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py apply `
  --target . `
  --answers .orchestrator/onboarding-answers.json `
  --approved-plan-hash <PLAN_HASH>
```

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py rollback --target .
```

```text
target-project/
├── AGENTS.md
├── .gitignore
├── .orchestrator/
│   ├── config.json
│   ├── project-context.md
│   ├── skills.json
│   ├── project-skills/
│   └── tasks/
└── tools/ai-orchestrator/
```

```gitignore
# AI Orchestrator operational state: start
.orchestrator/onboarding/session.json
.orchestrator/onboarding/backups/
.orchestrator/tasks/tasks.json
.orchestrator/tasks/*.tmp
.orchestrator/tasks/checkpoints/
.orchestrator/telemetry/
# AI Orchestrator operational state: end
```

```powershell
git status --short
git diff
```

```powershell
git -C tools/ai-orchestrator fetch
git -C tools/ai-orchestrator checkout <APPROVED_VERSION_OR_COMMIT>
```

```text
Before apply: inspect → preview → approve
After apply: validate → health → idempotency
On failure: restore backup manifest → report rollback
```

```powershell
orchestrator health --strict --json
```
