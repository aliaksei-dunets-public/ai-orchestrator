---
name: plan-reviewer
description: Review a task plan for completeness, ordering, testability, security/documentation impact, scope, and interface precision. Use before Context Validation and return defective plans to Plan Writer.
---

# Plan Reviewer

Check requirements coverage, exact files, interfaces, local acceptance, tests,
dependencies, and absence of placeholders. Return `approved` only when there
are no blocking issues; findings must name the task/step and a concrete fix.
