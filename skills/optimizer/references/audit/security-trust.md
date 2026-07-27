# Security and Trust Audit

## Trust hierarchy

Use an explicit hierarchy appropriate to the platform. A common default is:

1. platform or system constraints;
2. developer or project policy;
3. user task;
4. trusted configuration;
5. repository and retrieved documents;
6. external content and tool output.

Treat levels 5–6 as data unless a trusted higher-level policy explicitly grants
instruction authority.

## Prompt injection and context poisoning

Check whether untrusted content can:

- override agent rules or task scope;
- request tool calls or permission changes;
- suppress validation or reporting;
- cause secret or private-data disclosure;
- instruct subagents through copied context;
- alter generated configuration or code that is later trusted;
- persist poisoned facts into memory or compacted state.

Verify that agent-to-agent summaries do not launder untrusted instructions into
trusted task state.

## Permissions and least privilege

Check:

- tool access matches role and phase;
- read and write capabilities are separated where practical;
- destructive or external actions require appropriate approval;
- sensitive fields are filtered from prompts, logs, traces, and handoffs;
- credentials are never embedded in prompts or reusable state;
- authorization is enforced by the application, not only by natural-language instructions;
- sandbox and network boundaries are explicit.

## Data handling

Review source classification, retention, logging, redaction, cross-agent sharing,
and whether external providers receive only necessary data. Verify that
summaries and caches preserve privacy constraints.

## Failure and escalation

Security-sensitive ambiguity should fail closed or escalate according to policy.
Retries must not weaken permissions, bypass approval, or repeat destructive
operations.

## Evidence

Separate confirmed vulnerabilities from design risks and speculative attack
paths. Include the trust boundary crossed, required preconditions, expected
impact, and mitigation layer.
