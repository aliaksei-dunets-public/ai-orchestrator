# Optimizer Guide

## What it audits

Optimizer reviews the design of existing prompts, skills, agents, subagent
workflows, tool policies, context pipelines, model/runtime configuration, and
platform-specific instruction layers. It does not perform the domain task of
the audited agent.

## Recommended requests

- `Audit this skill in standard mode. Focus on token usage and stability.`
- `Compare these two prompt versions using the supplied traces and metrics.`
- `Run a deep audit of this multi-agent workflow, including trust boundaries and write-tool safety.`
- `Audit this repository for Codex, Antigravity, Copilot VS Code, and Claude VS Code compatibility.`
- `Optimize this agent output contract: preserve evidence but reduce verbose user responses and subagent handoffs.`
- `Apply the approved recommendations and update the self-tests.`

## Evidence that improves results

Provide any available:

- folder structure and entry-point prompts;
- target platform and surface: IDE, CLI, or both;
- tool schemas and permissions;
- model and runtime configuration;
- representative task traces;
- token, latency, and cost usage;
- successful and failed examples;
- expected outputs or graders.

The skill can still perform a static audit without runtime evidence, but it must
label inferred behavior and lower confidence.

## Modes

- `quick`: compact report with up to three material findings.
- `standard`: default compact report with up to five material findings.
- `deep`: explicitly requested appendices for complex systems or formal reviews.
- `compare`: compact findings plus before/after metrics.
- `optimize`: compact findings, applied changes, questions, and resulting metrics.


## Report language

Optimizer automatically writes the user-facing report in:

1. the explicitly requested language; otherwise
2. the language of the latest substantive user request; otherwise
3. the most recent explicit user-facing language from the active context or the
   configured user/environment default.

For mixed-language requests, code, paths, commands, identifiers, product names,
and quoted source text do not determine the report language. These technical
elements remain unchanged unless translation is explicitly requested. The
language of the audited prompt or skill does not override the user's language.

## Default report

Optimizer returns only:

1. **Important Findings** — material root problems with short evidence, impact,
   and action;
2. **Recommended Changes** or **Applied Changes** — concrete actions or files;
3. **Questions** — only unresolved material or blocking decisions, omitted when
   none exist;
4. **Metrics** — measured current or before/after values plus one validation
   line.

The default report does not include a separate executive summary, execution
model, scorecard, recommendation section, target architecture, or implementation
plan. These are optional deep appendices and must not repeat the compact report.

Example:

```markdown
## Important Findings

1. **[High] Unconditional reference loading** — `SKILL.md:72`.
   Impact: high input-token cost. Action: add conditional routing.

## Applied Changes

- Added `references/index.md` and removed duplicated loading rules.

## Metrics

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Estimated core tokens | 2,600 | 1,800 | -31% |

Validation: PASS — 12 fixtures, 0 broken references.
```


## Compact response optimization

Optimizer treats answer length as an information-contract problem, not as a
simple `be concise` instruction. It audits:

- whether the consumer is a user, orchestrator, peer agent, machine, or durable artifact;
- required information versus low-value narration and repetition;
- `compact`, `standard`, and `detailed` response modes;
- expansion conditions for critical risk, failed validation, conflict, or insufficient evidence;
- delta-only handoffs when task state already exists;
- whether verbosity belongs in the prompt, runtime, schema, or application layer;
- whether shorter output causes missing evidence, extra turns, retries, or quality regression.

Load `references/audit/output-contract.md` for diagnosis and
`references/patterns/compact-response.md` only when implementing a confirmed
output-efficiency improvement.

## Supported platform adapters

| Platform | Recommended repository installation |
|---|---|
| OpenAI Codex | `.agents/skills/optimizer/` |
| Google Antigravity CLI | `.agent/skills/optimizer/` |
| GitHub Copilot in VS Code | `.github/skills/optimizer/` |
| Claude Code for VS Code | `.claude/skills/optimizer/` |

Install one or all adapters with:

```bash
python scripts/install_platform.py --repo /path/to/repository --platform codex
python scripts/install_platform.py --repo /path/to/repository --platform all
```

Copy mode is the default. Re-run the installer with `--force` when upgrading.
Use symlink mode only when the development environment and repository workflow
support it reliably. Keep this package as the canonical source rather than
editing several installed copies independently.

## Platform-specific audit behavior

Load `references/platforms/common.md` and only the matching platform file.
Always distinguish the IDE extension from a CLI proxy. Automated CLI regression
is useful, but Copilot VS Code, Claude VS Code, and Antigravity IDE still need a
smoke test that confirms discovered skills, references, model, tools, and
permissions.

## Platform eval runner

Inspect commands without executing agents:

```bash
python scripts/run_platform_eval.py \
  --platform all \
  --workspace /path/to/fixture \
  --dry-run
```

Run one fixture:

```bash
python scripts/run_platform_eval.py \
  --platform codex \
  --workspace /path/to/fixture \
  --case monolithic-prompt \
  --out tests/runs
```

The runner uses read-only or plan-oriented defaults where the platform exposes
them, disables persistence where supported, and bounds available turns, budget,
or credits. It captures execution evidence but does not replace semantic grading
or IDE smoke tests. See `evals/README.md`.

## Reference extension contract

Keep universal behavior in `SKILL.md`. Add provider- or platform-specific
knowledge below `references/providers/<provider>/` or `references/platforms/`
and register it in `references/index.md`.

Each changing source should declare:

```yaml
platform: claude-code
surface: vscode
checked_at: 2026-07-14
verification_required_for:
  - current feature availability
  - instruction discovery paths
```

When current verification is unavailable, treat version-specific guidance as
potentially stale rather than as a guaranteed current behavior.

## Validation

Run:

```bash
python scripts/validate_skill.py
```

The validator checks structure, frontmatter, references, code fences, size
limits, platform config safety, source freshness metadata, fixture completeness,
and unexpected binary files. LLM behavior tests require execution by a target
platform or an external grader.
