---
platform: common
surface: ide-and-cli
checked_at: 2026-07-14
verification_required_for:
  - current instruction discovery behavior
  - current CLI flags
  - current agent and skill capabilities
---

# Cross-Platform Agent Audit Guidance

Load this file when the artifact targets an IDE agent, CLI coding agent, or both.
Then load only the matching platform file.

## Separate the Layers

Audit each instruction by its intended lifetime and enforcement level:

| Layer | Appropriate content |
|---|---|
| Always-on project instructions | short, durable facts and conventions needed for most tasks |
| Path-scoped rules | conventions that apply only to matching files or directories |
| Skill | conditional multi-step workflow or specialized knowledge |
| Custom agent/subagent | isolated role, tools, permissions, or independent review boundary |
| Hook/application policy | deterministic authorization, validation, or blocking control |
| Runtime configuration | model, reasoning, verbosity, budget, persistence, sandbox, and tool limits |

Flag long procedures copied into always-on files, platform-specific details mixed
into universal instructions, and hard security requirements implemented only as
natural-language guidance.

## Canonical Source Strategy

When one repository supports several platforms:

1. keep shared behavioral policy in one canonical source;
2. keep each platform adapter thin;
3. avoid copying complete workflows into `AGENTS.md`, `CLAUDE.md`, Copilot
   instructions, and platform skills simultaneously;
4. document precedence and discovery behavior;
5. test each platform because inheritance and automatic loading differ;
6. version adapters together with the canonical workflow.

Do not assume a file recognized by one platform is recognized by another.

## IDE Versus CLI

Treat the IDE extension and CLI as related but distinct execution surfaces.
Audit:

- instruction and skill discovery paths;
- model and tool availability;
- interactive approvals versus non-interactive permissions;
- persistence, user-level memory, and local configuration;
- output format and observability;
- whether CLI evaluation is a faithful proxy for IDE behavior.

When the CLI is only a proxy, require an IDE smoke test that verifies which
instructions and skills were actually used.

## Eval Isolation

A platform eval should record:

- platform and surface;
- executable and version;
- repository revision;
- installed skill path;
- model and runtime controls;
- user/global instructions that may be loaded;
- permission or sandbox mode;
- persistence mode;
- case, prompt, output, duration, exit status, and usage when available.

Use a temporary workspace and read-only or plan mode for audit fixtures. Never
run destructive or external write tools in baseline tests.

## Platform Comparison Rules

Compare platforms on task success and total system cost, not output brevity
alone. Account for:

- always-loaded instruction tokens;
- conditional skill loading;
- subagent startup and handoff cost;
- tool output volume;
- retries and approvals;
- persistence and cache reuse;
- differences between IDE and CLI execution.

Do not interpret one platform's token counters as directly equivalent to
another platform's counters without documenting what each metric includes.
