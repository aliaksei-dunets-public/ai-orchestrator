# Reference Routing Index

Load this file first. Open only references required by the observed artifact or
risk. Do not load every reference by default.

| Audit need | Load |
|---|---|
| Prompt hierarchy, duplication, context, retrieval, truncation | `audit/instructions-context.md` |
| Subagents, tool routing, side effects, idempotency, concurrency | `audit/orchestration-tools.md` |
| Trust hierarchy, prompt injection, permissions, secrets | `audit/security-trust.md` |
| Token/cost metrics, eval design, confidence, regressions | `audit/evaluation-metrics.md` |
| Response length, output contracts, audience, delta handoffs | `audit/output-contract.md` |
| Context state, compaction, caching patterns | `patterns/context-state.md` |
| Delegation, handoff, fan-out, validation patterns | `patterns/orchestration.md` |
| Runtime controls, experiments, migration patterns | `patterns/runtime-evaluation.md` |
| Compact user responses and agent handoff patterns | `patterns/compact-response.md` |
| OpenAI common guidance | `providers/openai/common.md` |
| OpenAI GPT-5.4 only | `providers/openai/gpt-5.4.md` |
| OpenAI GPT-5.5 only | `providers/openai/gpt-5.5.md` |
| OpenAI GPT-5.6 only | `providers/openai/gpt-5.6.md` |
| Any IDE/CLI coding-agent platform | `platforms/common.md` |
| OpenAI Codex | `platforms/codex.md` |
| Google Antigravity | `platforms/google-antigravity.md` |
| GitHub Copilot in VS Code | `platforms/github-copilot-vscode.md` |
| Claude Code for VS Code | `platforms/claude-vscode.md` |

## Routing rules

1. Select by concrete audit question, not by curiosity.
2. Load the provider common file plus only the active model file.
3. Load `platforms/common.md` plus only the active platform/surface file.
4. Do not apply model- or platform-specific advice elsewhere without evidence.
5. Treat IDE and CLI as separate surfaces unless parity is verified.
6. Prefer project/runtime evidence over generic patterns.
7. Stop loading references when sufficient evidence exists.

## Extension

Register new provider or platform files in this table. Keep them independent of
the universal skill core and include source/freshness metadata when guidance can
change over time.
