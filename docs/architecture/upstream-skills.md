# Upstream Skills Compatibility

Source: `https://github.com/aliaksei-dunets-public/ai-agent-skills`<br>
Reviewed commit: `4a50ba135fc05e3e98418b0b9fd8f537337d0b0a`<br>
Reviewed on: 2026-07-27

## Integrated atomic skills

| Upstream skill | Orchestrator use | Coordinator |
| --- | --- | --- |
| `development/coding-discipline` | Caution-first source and test implementation | `implementation-runner` |
| `development/security-gate` | Scanner routing, exploit validation and security verdict | `security-reviewer` |
| `development/python-code-review` | Python-specific system and failure-flow review | `code-reviewer` and Python technology profile |
| `global-skills/optimizer` | Deep audit of instructions, skills and orchestration workflows | `orchestrator-auditor` |

The upstream directories retain their references, templates, evals and scripts. `python-code-review` has one documented orchestrator adaptation: its large upstream workflow is preserved in `references/review-workflow.md`, while the installed `SKILL.md` is a thin quick/standard/deep router with bounded independent-review admission and compact handoffs. Orchestrator-owned coordinator skills stay small and define routing, shared result schemas and workflow transitions.

## Reviewed but not integrated

| Upstream skill | Reason |
| --- | --- |
| `global-skills/task-manager` | Uses a legacy Markdown task state model that conflicts with Task Layer 0.3 JSON Task Registry and its source-of-truth rules. |
| `global-skills/development-orchestrator-installer` | Installs the same legacy task/memory layout and would create competing canonical state. |
| `global-skills/brainstorming` | Task Creator already owns quick/standard/deep analysis and plan approval; a second coordinator would duplicate responsibility. |
| `global-skills/prompter` | Useful as a standalone authoring aid but not required by the orchestration runtime or any phase acceptance criterion. |

Upstream updates require a new compatibility review, a recorded commit, reapplication or removal of documented adaptations, contract tests and regeneration of the release artifact; they are never pulled into runtime automatically.
