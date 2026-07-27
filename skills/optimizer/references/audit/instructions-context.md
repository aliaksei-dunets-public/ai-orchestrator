# Instructions and Context Audit

## Purpose and activation

Check that purpose, positive triggers, negative triggers, inputs, outputs, and
boundaries are explicit. Broad activation often loads irrelevant skills and
creates overlapping ownership.

## Instruction architecture

Check for:

- clear hierarchy among goals, invariants, decision rules, workflow, and examples;
- one canonical source for each rule;
- semantic as well as exact duplication;
- contradictory defaults or overloaded `always`, `never`, `must`, and `only`;
- examples that silently become rules;
- checklists that suppress global reasoning;
- process micromanagement where outcome criteria would be sufficient;
- configuration values embedded in invariant instructions.

Classify duplicated text as intentional reinforcement, harmless redundancy,
maintenance risk, behavioral conflict, or token-only waste.

## Context pipeline

Map:

```text
selection -> retrieval -> ranking -> ordering -> deduplication
          -> compression -> attribution -> invalidation
```

Check:

- task classification before large reads;
- search before full-file loading;
- relevant fragments rather than entire directories;
- stable prefix before dynamic context where caching applies;
- critical instructions not buried in the middle of long context;
- token-limit and truncation behavior;
- chunk size and overlap proportional to source structure;
- retrieval precision, recall, stale results, and contradictory sources;
- duplicate chunks and repeated file reads;
- source attribution for later verification;
- invalidation when source revision or configuration changes;
- large tool descriptions or schemas loaded when unused;
- conversation replay where compact state would suffice.

## Context quality risks

Look for lost-in-the-middle effects, stale summaries, context poisoning,
unbounded histories, raw successful logs, obsolete assumptions, and compressed
state that removed critical evidence.

## Recommended outputs

For material issues, identify:

- always-loaded context;
- conditionally loaded context;
- repeatedly loaded context;
- content to remove, split, summarize, index, or relocate;
- expected quality trade-offs and validation cases.
