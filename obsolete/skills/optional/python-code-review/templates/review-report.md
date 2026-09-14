# Python Code Review Report

Use the shortest form that preserves evidence. Do not add empty sections.

## Verdict

**Decision:** `APPROVE | APPROVE WITH FOLLOW-UPS | REQUEST CHANGES | BLOCK | INCONCLUSIVE`

**Rationale:** One or two sentences describing the highest-impact technical
reason for the decision.

## Scope and Confidence

- **Review mode:** `CHANGE_REVIEW | COMPONENT_REVIEW | PROJECT_AUDIT`
- **Target scope:**
- **Context scope:**
- **System horizon:**
- **Base / head:**
- **Requirements / plan:**
- **Exclusions:**
- **Repository instructions consulted:**
- **Coverage:** inspected deeply / sampled / not inspected
- **Overall confidence:** `high | medium | low`

## Executive Summary

Summarize what the software or change does, whether the design is coherent, the
principal strengths, the highest-impact risks, and whether known requirements
are satisfied. Do not reduce this section to a count of findings.

## System Understanding

### Purpose and Primary Workflows

Describe the relevant system behavior in concise technical terms.

### Components and Boundaries

Describe the main components, dependency direction, external boundaries, and
where responsibilities are implemented.

### State, Resources, and Invariants

Describe important state ownership, lifecycle, irreversible side effects,
transactions, resource ownership, and correctness invariants.

### Failure and Recovery Model

Describe how expected failures, retries, partial success, cancellation,
cleanup, restart, and recovery behave.

## Change in System Context

For change reviews, explain:

- what changed semantically, not only textually;
- affected callers, contracts, data, configuration, persistence, and jobs;
- compatibility and deployment implications;
- why the actual blast radius is limited or broader than the diff.

For project audits, replace this section with the audit coverage strategy and
representative areas selected.

## Architectural Assessment

Assess:

- responsibility placement and cohesion;
- dependency direction and coupling;
- abstraction fitness and duplicated knowledge;
- state and lifecycle ownership;
- changeability and likely propagation of future changes;
- testability, diagnosability, and operational support.

Include both strengths and risks. Avoid generic architecture commentary.

## Scenarios Traced

| Scenario | Path or components | Observed outcome | Risk or conclusion |
|---|---|---|---|
| | | | |

Include at least one normal and one credible failure scenario for non-trivial
reviews.

## Findings

### Systemic Findings

Problems that arise from architecture, repeated patterns, shared abstractions,
or cross-cutting behavior.

#### SYS-1 — Concise title

- **Severity:** `Critical | Blocking | Important | Minor`
- **Boundary / representative locations:**
- **Evidence:**
- **Triggering scenario:**
- **Causal path:**
- **Impact:**
- **Recommended correction / acceptance criterion:**
- **Confidence:** `high | medium | low`

Write `None` when no systemic finding is confirmed.

### Localized Findings

#### LOC-1 — Concise title

- **Severity:** `Critical | Blocking | Important | Minor`
- **Location:** `path/to/file.py:line`
- **Evidence:**
- **Triggering scenario:**
- **Causal path:**
- **Impact:**
- **Recommended correction / acceptance criterion:**
- **Confidence:** `high | medium | low`

Write `None` when no localized finding is confirmed.

### Suggestions

Optional alternatives without a demonstrated defect. Keep them separate from
required work.

## Requirements and Contract Alignment

- Requirements satisfied:
- Missing or partially implemented requirements:
- Intentional deviations:
- Backward-compatibility impact:
- API/schema/migration/deployment implications:

## Verification Evidence

| Command or check | Scope | Result | What it proves | Limitations |
|---|---|---|---|---|
| | | | | |

State explicitly when checks were not run.

## Test Architecture and Confidence

- Contracts actually protected:
- Normal and failure-path coverage:
- Boundary and integration fidelity:
- Mock realism:
- Isolation and determinism:
- Structural test-suite risks:
- Missing high-value tests:

## Coverage Backstop

This section confirms coverage; it must not replace the system analysis above.

| Dimension | Assessment | Key evidence or residual risk |
|---|---|---|
| Behavior and correctness | | |
| Clarity and local design | | |
| Architecture and changeability | | |
| Security and data protection | | |
| Reliability, performance, and operations | | |
| Python-specific behavior | | |

## Independent Review

- **Mechanism:** fresh subagent, independent model/session, or isolated fallback
- **Independent verdict:**
- **Systemic insights discovered independently:**
- **Additional localized findings:**
- **Primary findings rejected or changed after challenge:**
- **Limitation:** disclose when no genuinely independent execution was available.

## Strengths

List specific qualities that materially improve correctness, simplicity,
changeability, testability, security, or operational reliability.

## Residual Risks and Unknowns

Document unavailable requirements, unexecuted environments, unknown external
contracts, sampled areas, assumptions, and operational risks that remain.

## Required Actions

1. Only actions required by Critical or Blocking findings.
2. Keep Important follow-ups and optional improvements separate.
