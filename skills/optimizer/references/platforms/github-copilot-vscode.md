---
platform: github-copilot
surface: vscode
checked_at: 2026-07-14
verification_required_for:
  - current VS Code instruction precedence
  - current Agent Skills support
  - current custom agent format
  - current Copilot CLI parity with VS Code
---

# GitHub Copilot in VS Code

Load with `platforms/common.md` when auditing Copilot Chat or agent workflows in
VS Code.

## Instruction and Agent Surfaces

- `.github/copilot-instructions.md` contains repository-wide instructions.
- `.github/instructions/*.instructions.md` can apply rules only to matching
  paths through `applyTo` globs.
- `AGENTS.md` may also be recognized; audit precedence and avoid maintaining
  equivalent rules in several files.
- Agent Skills can be stored in `.github/skills`, `.agents/skills`, or another
  supported compatibility location. Choose one canonical project location.
- Custom agents can be defined under `.github/agents/*.agent.md` with bounded
  tools, model, and role instructions.
- Prompt files are a separate IDE-oriented mechanism and should not become a
  second canonical copy of permanent policy.

## Audit Checks

Check for:

- the same rule in Copilot instructions, `AGENTS.md`, path rules, skills, and
  custom agents;
- large conditional procedures in always-on repository instructions;
- `applyTo` globs that are too broad, too narrow, or never match;
- custom agents with unrestricted tools despite a narrow responsibility;
- `allowed-tools` or shell preapproval in untrusted skills;
- prompt injection through repositories, issues, web content, or generated
  files reaching preapproved commands;
- an IDE behavior claim validated only with Copilot CLI;
- missing verification through the VS Code References list or equivalent UI.

## Eval Adapter

The included automated adapter uses Copilot CLI as a regression proxy with a
bounded AI-credit limit. It does not prove identical VS Code extension behavior.

After CLI regression tests, run an IDE smoke test and record:

- active custom instructions and path-specific rules;
- selected custom agent and model;
- detected optimizer skill;
- referenced files;
- requested approvals and tools;
- final output mode and schema compliance.

See `evals/platforms/github-copilot-vscode.json`.

## Installation

Recommended repository path for this platform-specific installation:

```text
.github/skills/optimizer/
```

Keep simple broadly relevant rules in Copilot instructions. Keep optimizer's
conditional audit procedure in the skill.
