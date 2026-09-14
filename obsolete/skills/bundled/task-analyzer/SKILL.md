---
name: task-analyzer
description: Analyze repository evidence for a task, separate symptom from cause, and identify affected components, constraints, risks, and unknowns. Use inside the standard/deep Task Creation Workflow before selecting an approach.
---

# Task Analyzer

Build or receive a fresh bounded context pack before analysis. Provenance in the
pack is navigation evidence, not a replacement for canonical sources. Empty or
irrelevant stores are a valid no-op.

1. Read Project Context, profiles, code, tests, ADRs, and related decisions.
2. Separate verified facts from hypotheses.
3. Return problem, current/expected behavior, affected components, constraints, risks, and evidence paths.
4. Do not select an implementation or change Task Registry.
