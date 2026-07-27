---
platform: openai-codex
surface: desktop-cli-ide
checked_at: 2026-07-14
verification_required_for:
  - current skill discovery paths
  - current AGENTS.md precedence
  - current subagent capabilities
  - current codex exec flags
---

# OpenAI Codex

Load with `platforms/common.md` when auditing Codex Desktop, CLI, or IDE use.

## Instruction and Skill Surfaces

- `AGENTS.md` is the always-on repository instruction surface. Keep it short,
  durable, and broadly relevant.
- Use an Agent Skill for conditional, specialized, or multi-step procedures.
- Repository skills can live under `.agents/skills/<skill-name>/SKILL.md`.
- User and administrator skill locations may also contribute instructions;
  record them during reproducible evals.
- Codex discovers skill metadata first and loads the complete skill only when
  selected, so accurate `name` and `description` fields are important.
- Optional agent metadata can control presentation and implicit invocation.

## Audit Checks

Check for:

- large workflows copied into `AGENTS.md` instead of a routed skill;
- overlapping `AGENTS.md` files with unclear precedence;
- a skill description so broad that it loads on unrelated tasks;
- hidden user/admin skills affecting reproducibility;
- subagents used for small sequential tasks despite their extra token cost;
- parent and subagent repeating repository analysis;
- oversized tool output when a configured output token limit or filtering would
  be more appropriate;
- write access granted to audit-only tasks.

## Eval Adapter

Use `codex exec` for repeatable non-interactive cases. Recommended audit
baseline characteristics:

- ephemeral session;
- JSONL event output;
- explicit working directory;
- read-only sandbox;
- fixed prompt and repository revision;
- recorded model/config overrides.

The included runner uses the conservative command template in
`evals/platforms/codex.json`. Structured output may be added when the installed
Codex version supports the configured schema flag.

## Installation

Recommended repository path:

```text
.agents/skills/optimizer/
```

Keep project-wide facts in `AGENTS.md`; do not duplicate the complete optimizer
workflow there.
