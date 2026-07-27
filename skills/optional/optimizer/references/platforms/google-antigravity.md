---
platform: google-antigravity
surface: ide-standalone-cli
checked_at: 2026-07-14
verification_required_for:
  - current skill discovery paths
  - current standalone and CLI feature parity
  - current non-interactive CLI flags
  - current model and subagent availability
---

# Google Antigravity

Load with `platforms/common.md` when auditing Antigravity IDE, standalone agent
manager, or Antigravity CLI.

## Instruction and Skill Surfaces

- Antigravity supports Agent Skills, but IDE/standalone and CLI discovery paths
  are not necessarily identical.
- For a repository-scoped CLI skill, use `.agent/skills/<skill-name>/SKILL.md`.
- Global CLI skills may live under the Antigravity CLI user skill directory.
- Do not assume a skill visible to the standalone product is automatically
  visible to the CLI; verify the active surface and discovery path.
- Record enabled models, MCP servers, security/execution mode, and available
  subagents because these materially change behavior and cost.

## Audit Checks

Check for:

- confusion between `.agent/skills` and other cross-platform skill folders;
- IDE-only capabilities assumed to exist in CLI automation;
- broad autonomous execution without bounded permissions or approval policy;
- several background agents duplicating the same discovery work;
- MCP/tool results passed unfiltered between agents;
- model switching without a fresh baseline;
- platform workflows embedded in the universal skill core;
- security mode treated as a prompt instruction rather than runtime policy.

## Eval Adapter

The included automated adapter uses the Antigravity CLI non-interactive prompt
mode when available. Because structured output and IDE/CLI parity can change,
record the installed version and treat text parsing as best effort.

A complete validation has two stages:

1. CLI regression cases in a temporary read-only fixture workspace;
2. IDE or standalone smoke test confirming skill discovery, selected model,
   tool permissions, and the references actually used.

See `evals/platforms/google-antigravity.json`.

## Installation

Recommended repository path for Antigravity CLI:

```text
.agent/skills/optimizer/
```

For another Antigravity surface, verify its current discovery path rather than
copying the skill into several directories without a canonical source.
