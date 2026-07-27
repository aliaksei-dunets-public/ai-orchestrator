# Evaluation and Metrics Audit

## Measurement objective

Optimize tokens, cost, latency, or complexity only under explicit quality and
safety constraints. The preferred economic metric is cost or tokens per
successful task, not raw average tokens.

## Baseline protocol

1. Preserve the working baseline.
2. Define representative cases and acceptance criteria.
3. Hold model, tools, runtime, and data constant unless one is the variable under test.
4. Apply one independent change.
5. Rerun identical cases.
6. Compare quality, safety, usage, latency, and variance.
7. Keep, revise, or roll back the change.

## Per-case metrics

```yaml
quality:
  task_success: true
  critical_requirements_met: "8/8"
  evidence_complete: true
  output_schema_valid: true
  safety_violations: 0
usage:
  static_prompt_tokens: 0
  dynamic_context_tokens: 0
  retrieved_context_tokens: 0
  tool_result_tokens: 0
  subagent_input_tokens: 0
  subagent_output_tokens: 0
  final_output_tokens: 0
  total_tokens: 0
execution:
  tool_calls: 0
  agent_handoffs: 0
  retries: 0
  turns: 0
  latency_ms: 0
  estimated_cost: 0
```

When exact token attribution is unavailable, mark estimates and preserve the
same estimation method across baseline and candidate.

## Aggregate metrics

Compare median, p90 or p95, worst case, success rate, regression count, retries,
tokens per successful task, cost per successful task, and latency per successful
task. Means alone may hide expensive or unstable tails.

## Eval-set coverage

Include applicable cases:

- typical and complex tasks;
- ambiguous requirements;
- missing or stale context;
- conflicting instructions;
- tool failure and partial result;
- prompt injection and malicious retrieved content;
- context-limit pressure and truncation;
- excessive tool use or premature stopping;
- overly verbose and overly compressed output;
- side-effect retry and concurrency;
- model or runtime migration.

Avoid tuning only to a few examples. Keep baseline and candidate conditions
comparable, define blocking regressions, and use human review for subjective or
high-impact cases.

## Confidence and evidence

- `high`: direct static, runtime, or metric evidence;
- `medium`: strong structural inference without runtime confirmation;
- `low`: hypothesis requiring additional evidence.

Use evidence types: `static`, `runtime`, `metric`, `external-guidance`, and
`inference`. External guidance supports a recommendation but does not prove the
artifact exhibits the problem.

## Reporting savings

Do not promise exact savings without measurement. Otherwise use qualitative
ranges: minimal, low, moderate, high, or very high, and state assumptions.
