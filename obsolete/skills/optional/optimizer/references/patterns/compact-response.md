# Compact Response Patterns

Use these patterns only after an output-efficiency problem is established.
Preserve correctness, material evidence, validation, blockers, risks, and
required decisions.

## Pattern 1: Portable Compact Response Protocol

```markdown
## Response Policy

Use the shortest response that fully completes the task.

Include, when applicable:
1. result or status;
2. material findings, decisions, or changes;
3. validation outcome;
4. blockers and significant risks;
5. only required next actions.

Do not include task restatement, routine-action narration, repeated context,
unchanged findings, empty sections, or full logs without diagnostic value.

Perform sufficient analysis for correctness. Keep the returned answer compact;
do not reduce analysis depth merely to shorten the response.

Expand beyond the normal mode only for critical risk, failed validation,
conflicting requirements, insufficient evidence, incompatibility, or an
unresolved blocker.
```

## Pattern 2: Audience-Specific Modes

```yaml
output_contract:
  user:
    default_mode: standard
    required: [result, material_evidence, validation, risks]
  subagent:
    default_mode: compact
    required: [status, delta, validation, blockers]
  machine:
    default_mode: structured
    schema: "<schema identifier>"
```

Avoid copying the same full protocol into every agent. Keep one canonical
contract and reference it from platform adapters or subagent definitions.

## Pattern 3: Response Modes

### Compact

Use for routine completion and agent handoffs. Return status, a one-to-three
sentence summary, material deltas, validation, and blockers. Omit empty fields.

### Standard

Use for normal user-facing work. Return the result first, then only the evidence,
trade-offs, recommendations, validation, and risks required to understand or
act on it.

### Detailed

Use only when explicitly requested or required by the task type, such as a
formal audit, architecture document, incident analysis, migration plan, or
security review.

Do not force fixed token limits across task types. Use measured soft targets per
consumer and artifact category.

## Pattern 4: Delta Handoff

```yaml
schema_version: "1.0"
status: completed
summary: "Implemented the focused timezone fix."
changes:
  - file: src/time_service.py
    description: "Replaced naive UTC creation with timezone-aware UTC."
validation:
  result: passed
  checks:
    - "12 focused tests passed"
```

Rules:

- include only changes since the previous state;
- omit empty fields;
- link to evidence instead of copying large content;
- do not return internal reasoning;
- do not repeat the parent assignment;
- distinguish `partial` from `completed`.

## Pattern 5: Result-First User Response

```text
<Result or recommendation in the first paragraph.>

<Only the evidence or trade-offs needed to trust or act on it.>

<Validation, material risk, or one required next action when applicable.>
```

Use headings only when they improve navigation. Do not create a report template
for a response that fits in a few sentences.

## Pattern 6: Root-Finding Limits

For audit and review agents:

```text
Return only material root findings. Group related symptoms. Do not invent
findings to reach a count. Default maximum: 3 in compact mode and 7 in standard
mode, unless additional findings are critical or high severity.
```

A maximum is not a minimum.

## Pattern 7: Tool Result Compression

Before passing tool output to another agent:

1. retain errors, warnings, relevant values, and source pointers;
2. remove repeated successful lines and unrelated fields;
3. summarize large logs while preserving retrievable locations;
4. send raw output only when required for diagnosis or independent verification.

Application-side filtering is preferable when deterministic and safe.

## Pattern 8: Runtime/Prompt Split

When supported:

- use runtime verbosity for general answer length;
- use prompt rules for required/omitted information and expansion conditions;
- use schemas for machine-consumed structure;
- use application limits for transport size and redaction.

Do not ask the model to reveal chain-of-thought. Request concise conclusions and
material evidence instead.

## Pattern 9: Automatic Report Language

```text
Select the user-facing report language in this order:
1. explicit language requested by the user;
2. language of the latest substantive user request;
3. dominant natural-language prose in a mixed request;
4. most recent explicit user-facing language in context, then configured default.

Do not infer the report language from the audited source files. Preserve code,
paths, commands, identifiers, schema keys, and exact quotations unless the user
asks for translation. Keep headings and explanatory prose in one language.
```

Do not ask a language clarification when the request already provides a reliable
signal. For agent-to-agent or machine output, preserve the canonical schema and
localize only human-readable values when the consumer requires it.

## Validation Matrix

Test at least:

| Case | Expected behavior |
|---|---|
| Routine success | compact complete result |
| Validation failure | includes failure evidence and blocker |
| Critical risk | expands enough to explain the risk |
| No findings | states no material issue without invented sections |
| Existing state | returns delta only |
| User requests detail | switches to detailed mode |
| Machine consumer | schema-valid output, no prose wrapper |
| English artifact, Russian request | Russian report; technical tokens unchanged |
| Explicit language override | requested language wins over request/source language |

Measure output tokens and task success together. Track additional turns or
retries caused by missing information.

## Pattern 10: Compact Optimizer Report

Use this as the default report for audit and optimization agents:

```markdown
## Important Findings

1. **[High] <root problem>** — `<location>`.
   Impact: <material impact>. Action: <smallest effective action>.

## Recommended Changes | Applied Changes

- `<concrete action or changed file>`

## Questions

- `<only unresolved material or blocking decision>`

## Metrics

| Metric | Current | Before | After | Change |
|---|---:|---:|---:|---:|
| `<measured metric>` | ... | ... | ... | ... |

Validation: PASS | PARTIAL | FAILED — `<compact evidence>`.
```

Rules:

- omit `Questions` when none exist;
- omit unavailable metric columns rather than filling placeholders;
- use no more than 3 findings in quick mode and 5 in standard mode unless
  additional findings are critical or high severity;
- put evidence, impact, and action in the finding instead of repeating them in
  separate summary and recommendation sections;
- do not include execution models, scorecards, architecture, or implementation
  plans unless deep detail is explicitly requested;
- do not repeat unchanged capabilities, low-priority observations, or optional
  follow-up suggestions;
- label token values as estimates unless obtained from runtime usage data.
