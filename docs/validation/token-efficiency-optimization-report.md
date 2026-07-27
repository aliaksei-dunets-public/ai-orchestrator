# Token-Efficiency Optimization Report

Date: 2026-07-28<br>
Baseline commit: `f0d4e42`<br>
Mode: `$optimizer` `optimize`

## Applied findings

| Finding | Applied control | Direct evidence |
| --- | --- | --- |
| OPT-001 | Platform-neutral numeric telemetry, optional JSONL sink and CLI summary | `orchestrator/telemetry.py`, `orchestrator telemetry --json` |
| OPT-002 | Default canonical-source retrieval excludes release snapshots | `.rgignore`, `config/defaults.yaml` |
| OPT-003 | Task mode/risk/impact selects the smallest execution route | `orchestrator/workflow.py`, `workflows/task-execution.yaml` |
| OPT-004 | Python review uses a thin router and bounded subagent admission | `skills/python-code-review/SKILL.md` |
| OPT-005 | Checkpoint evidence has a deterministic bound, tail, digest and optional pointer | `orchestrator/execution.py` |

## Static before/after metrics

| Metric | Baseline | Candidate | Change |
| --- | ---: | ---: | ---: |
| Python review entrypoint | 20,978 bytes | 3,478 bytes | -17,500 bytes (-83.4%) |
| Quick low-risk execution route | 9 steps | 4 steps | -5 steps (-55.6%) |
| Release files visible to default `rg --files` | 167 | 0 | -167 duplicate entries |
| Release files visible to explicit `rg --files releases` | 167 | 167 | release validation preserved |
| Stored evidence per attempt | unbounded | at most 2,048 characters | deterministic bound |
| Runtime usage dimensions | none | 8 token fields plus duration/tool/handoff/retry counters | measurable when provider reports usage |
| Full test discovery | 110 tests | 129 tests | +19 focused contracts/scenarios |

The frozen 1.0.0 release snapshot is not rewritten by this Unreleased
optimization. Its manifest and 16-cell matrix remain independently verifiable.

## Validation

- 129 full-discovery tests pass.
- Workspace and release acceptance matrices pass 16/16.
- Every quick/standard/deep and low/medium/high/critical route retains Security Review.
- Telemetry rejects invalid counters/unknown fields and never stores prompt or evidence payload.
- Oversized evidence retains a diagnostic tail, original length, digest and source pointer.
- Workspace skill projection has zero drift.
- Health Check is `ok: true`; Audit has zero findings.
- Documentation links, optimizer fixtures and the frozen release manifest pass.

Exact tokens per successful task cannot be compared retroactively because the
baseline had no runtime counters. The new telemetry contract is the measurement
baseline for subsequent controlled comparisons; missing provider counters remain
unknown rather than estimated.
