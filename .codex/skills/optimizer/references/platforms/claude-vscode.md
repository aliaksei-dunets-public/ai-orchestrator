---
platform: claude-code
surface: vscode
checked_at: 2026-07-14
verification_required_for:
  - current VS Code and CLI parity
  - current skill and subagent discovery paths
  - current hook and permission behavior
  - current headless CLI flags
---

# Claude Code for VS Code

Load with `platforms/common.md` when auditing the Claude Code VS Code extension
or its CLI execution surface.

## Instruction, Skill, and Enforcement Surfaces

- `CLAUDE.md` is loaded as persistent project context. Keep it concise and
  broadly relevant.
- `.claude/rules/` can modularize and path-scope project instructions.
- Project skills live under `.claude/skills/<skill-name>/SKILL.md` and load on
  demand when used.
- Project subagents live under `.claude/agents/`; preloading full skills into a
  subagent increases its startup context and should be justified.
- Hooks and application permissions are the correct layer for deterministic
  blocks. Natural-language context is not a security enforcement boundary.

## Audit Checks

Check for:

- multi-step workflows embedded in `CLAUDE.md` instead of a skill;
- rules duplicated between `CLAUDE.md`, `.claude/rules`, skills, and subagents;
- broad path rules that create unnecessary context;
- subagents preloading large skills they rarely need;
- output styles used for project policy, adding system-prompt overhead;
- hard safety requirements expressed only as instructions instead of hooks;
- persistent sessions or auto-memory contaminating baseline evals;
- permission bypass or unrestricted tools in automated tests;
- CLI results treated as proof of VS Code UI behavior without a smoke test.

## Eval Adapter

Use Claude CLI headless mode as the automated regression surface. Conservative
baseline characteristics:

- JSON output;
- plan permission mode;
- bounded turns and monetary budget;
- no session persistence;
- fixed workspace and repository revision.

The runner configuration is in `evals/platforms/claude-vscode.json`. A final VS
Code smoke test should confirm skill discovery, project rules, hooks, model,
and tool approvals.

## Installation

Recommended repository path:

```text
.claude/skills/optimizer/
```

Use `CLAUDE.md` only for the small set of facts and rules needed on most tasks.
