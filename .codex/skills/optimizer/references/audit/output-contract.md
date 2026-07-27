# Output Contract and Response Efficiency Audit

Load this file when the target prompt, skill, agent, or subagent produces
verbose, repetitive, unstructured, or audience-inappropriate responses.

The goal is not the shortest possible answer. The goal is the smallest response
that preserves task completion, material evidence, validation, blockers, risks,
and required next actions.

## 1. Identify the Consumer

Classify each output surface:

- `user`: readable explanation or decision support;
- `orchestrator`: compact result for task coordination;
- `peer-agent`: evidence, findings, or changed state;
- `machine`: schema-valid structured data;
- `artifact`: durable document whose completeness may justify more detail.

Flag one response format reused for all consumers. A user-facing report and an
agent handoff usually need different contracts.

## 2. Audit the Report Language Contract

Check whether user-facing reports select language deterministically:

1. an explicit user language instruction has highest priority;
2. otherwise use the language of the latest substantive user request;
3. for mixed-language requests, infer from the dominant natural-language prose,
   excluding code, paths, identifiers, product names, and quoted content;
4. when the latest request is too short to classify, retain the most recent
   explicit user-facing language in the active context or use the configured
   user/environment default.

Flag:

- using the source artifact's language instead of the user's request language;
- switching languages between headings and report prose;
- translating code, file paths, commands, identifiers, schema keys, or exact
  evidence quotations without a request;
- asking the user to choose a language when the context already resolves it;
- applying language detection to internal machine schemas when only the
  user-facing report needs localization.

When an explicit report language conflicts with the request language, the
explicit instruction wins. Treat language choice as presentation behavior, not
as a reason to change technical content or evidence.

## 3. Audit the Information Contract

Check whether the target explicitly defines:

- default response mode;
- required information;
- information to omit by default;
- ordering of information;
- maximum or target scope;
- expansion conditions;
- handling of empty sections;
- behavior when previous state exists;
- whether a schema or runtime control should enforce the result.

A generic instruction such as `be concise` or `answer briefly` is weak because
it does not specify what must survive compression.

## 4. Required Information

For routine task completion, preserve applicable items:

1. result or status;
2. material findings, decisions, or changes;
3. validation outcome and relevant evidence;
4. blockers and significant risks;
5. only required next actions.

Do not require every field for every task. Empty sections create noise and may
encourage invented content.

## 5. Low-Value Output

Flag unnecessary:

- task restatement;
- greetings, acknowledgments, or closing filler;
- narration of routine tool calls;
- internal reasoning or chain-of-thought requests;
- repeated project context;
- unchanged findings from previous steps;
- successful logs without diagnostic value;
- full file contents when a path, patch, or summary is sufficient;
- many alternatives when one option is clearly preferable;
- speculative improvements outside scope;
- duplicate conclusions in summary and findings;
- empty headings or schema fields.

Do not remove explanations, evidence, or trade-offs that the consumer needs to
make a decision.

## 6. Response Modes

Prefer an explicit mode system when output needs vary:

- `compact`: agent handoffs and routine completion;
- `standard`: normal user-facing explanation;
- `detailed`: formal audits, architecture, incidents, migrations, or explicit request.

Audit whether the default mode is appropriate for the primary consumer and
whether mode selection is deterministic.

Token or word targets should be soft guidance, not hard safety limits. A target
may be exceeded for critical risk, failed validation, conflicting requirements,
insufficient evidence, backward incompatibility, or an unresolved blocker.

## 7. Analysis Depth Versus Output Length

Flag instructions that conflate concise output with shallow analysis, such as:

- `think briefly`;
- `do minimal analysis`;
- `skip reasoning to save tokens`.

Prefer a separation:

```text
Perform sufficient analysis to complete the task correctly.
Return only conclusions, material evidence, changes, validation, risks,
and required next actions.
```

Where the runtime supports separate reasoning and verbosity controls, audit them
independently. Do not duplicate a reliable runtime verbosity setting with long
prompt scaffolding unless evals show it is necessary.

## 8. Agent-to-Agent Handoffs

Check whether subagents return compact deltas rather than narrative history.
A handoff should normally contain only applicable fields:

```yaml
status: completed | partial | blocked | failed
summary: "One to three sentences."
findings:
  - location: "<file, symbol, or component>"
    finding: "<material finding>"
    severity: critical | high | medium | low
changes:
  - file: "<path>"
    description: "<concise change>"
validation:
  result: passed | failed | partial
  checks:
    - "<relevant check>"
risks:
  - "<significant remaining risk>"
blockers:
  - "<blocker and required input>"
next_actions:
  - "<only required action>"
```

Flag:

- full conversation history in handoffs;
- repeated assignment text;
- internal reasoning;
- unchanged state;
- raw tool output without filtering;
- a full user report from every subagent;
- fields populated only to satisfy a template.

## 9. Delta Communication

When prior task state exists, check whether the response returns only:

- new findings;
- changed assumptions;
- new modifications;
- new validation results;
- new blockers;
- remaining required work.

The state owner should consolidate deltas. Do not append an unbounded history to
every handoff.

## 10. Enforcement Layer

Recommend the smallest reliable layer:

| Need | Preferred layer |
|---|---|
| Behavioral selection and omission rules | prompt or skill |
| Machine-consumed shape and field types | Structured Outputs or schema |
| Output verbosity control | runtime setting when available |
| Maximum transport/storage size | application boundary |
| Redaction and secret removal | application/tool boundary |
| Agent handoff fields | shared schema or canonical contract |

Do not encode deterministic security, redaction, or transport limits only in
natural language.

## 11. Evaluation

Compare baseline and candidate on the same tasks. Record:

- task success and required information retained;
- output tokens by consumer type;
- repeated-information rate;
- schema validity;
- unsupported or invented fields;
- number of follow-up turns caused by missing information;
- retries caused by over-compression;
- tokens per successful task.

Include at least:

- routine success;
- failed validation;
- critical risk;
- no material findings;
- previous state with only one new delta;
- machine-consumed output;
- user explicitly requesting detail;
- source artifact in a different language from the user request;
- mixed-language request with code and identifiers;
- explicit report-language override.

A shorter answer is a regression when it causes missing evidence, extra turns,
incorrect decisions, retries, or failed task completion.

## 12. Finding Categories

Use one of these categories when applicable:

- `missing-output-contract`;
- `audience-mismatch`;
- `verbose-handoff`;
- `repeated-output`;
- `empty-section-noise`;
- `reasoning-verbosity-coupling`;
- `schema-prompt-duplication`;
- `unsafe-over-compression`;
- `missing-expansion-conditions`;
- `report-language-mismatch`.
