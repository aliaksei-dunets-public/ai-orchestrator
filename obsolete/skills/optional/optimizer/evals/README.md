# Platform Eval Adapters

The platform configs and `scripts/run_platform_eval.py` provide a safe,
repeatable starting point for running optimizer fixtures through four coding
agent environments:

- OpenAI Codex;
- Google Antigravity;
- GitHub Copilot in VS Code, using Copilot CLI as an automated proxy;
- Claude Code for VS Code, using Claude CLI as an automated proxy.

## Safety Defaults

- audit fixtures only;
- temporary or explicitly supplied workspace;
- read-only or plan permission mode where supported;
- bounded turns, budget, or AI credits where supported;
- no shell interpolation;
- no destructive or external write cases;
- session persistence disabled where supported.

## Dry Run

```bash
python scripts/run_platform_eval.py --platform all --workspace ./fixture --dry-run
```

## Execute One Case

```bash
python scripts/run_platform_eval.py \
  --platform codex \
  --workspace ./fixture \
  --case monolithic-prompt \
  --out ./tests/runs
```

The runner records the exact command, prompt hash, duration, exit code, stdout,
and stderr. It does not grade semantic quality automatically. Compare the
result with the matching file under `tests/expected/` or connect an external
grader.

## IDE Smoke Tests

Copilot CLI and Claude CLI are regression proxies for their VS Code extensions.
Antigravity CLI may also differ from its IDE/standalone surface. Complete the
platform check by verifying skill discovery, references, tools, permissions,
and selected model in the target IDE.
