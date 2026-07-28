# Implementation plan format

Use this format for each independent deliverable or roadmap phase.

```markdown
# <Title> Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using the repository's approved execution workflow.

**Goal:** One verifiable sentence.
**Architecture:** Two or three sentences describing boundaries and approach.
**Tech Stack:** Concrete languages, formats, libraries, and CLI.

## Global Constraints
- Compatibility, dependency, security, and scope constraints.

## Deliverables
- Exact artifacts and public interfaces.

## Dependencies
- Earlier phases, external tools, and launch conditions.

## Acceptance Criteria
- Observable, verifiable conditions.

## Testing Strategy
- Unit, contract, scenario, regression, and manual checks.

## Risks and Rollback
- Risk, detection signal, and safe rollback.

## Implementation Tasks
### Task 1: <Verifiable component>
**Files:**
- Create: `exact/path`
- Modify: `exact/path:symbol`
- Test: `exact/path`
**Interfaces:**
- Consumes: exact inputs.
- Produces: exact outputs and behavior.
**Acceptance:**
- Local criteria for this task.
**Tests:**
- Exact command and expected result.
- [ ] **Step 1:** Add a failing test or deterministic check.
- [ ] **Step 2:** Run it and confirm the expected failure.
- [ ] **Step 3:** Implement the smallest change.
- [ ] **Step 4:** Run focused and affected regression suites.
- [ ] **Step 5:** Update documentation/evidence and hand the task to review.
```

Rules: one task is one minimally reviewable deliverable; use exact existing or
planned paths; do not leave TBD/TODO/FIXME or vague steps; require regression
tests for fixed defects or explain why they do not apply; documentation phases
may use static structure, link, or contract checks instead of a failing test.
