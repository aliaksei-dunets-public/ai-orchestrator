# Implementation Execution Policy

**Status:** Accepted policy v0.2  
**Scope:** v1 single-agent implementation

## 1. v1 execution policy

```yaml
implementation:
  strategy: single_agent
  multi_agent: false
  parallel_execution: false
```

The implementation agent executes the approved plan from start to finish.

---

## 2. No automatic segmentation

The runtime must not automatically split implementation by:

- plan step;
- module;
- file group;
- context size;
- component count.

If the task is too large for reliable single-agent execution, the correct v1 response is to improve task/planning decomposition rather than launch multiple implementation agents.

---

## 3. Agent context

The agent receives:

```text
Task
Approved Plan
Implementation Analysis
Context Package
Project Profile
relevant review feedback
```

The implementation agent may request Context expansion when necessary.

---

## 4. Plan compliance

Minor technical adjustments are allowed.

Material changes require upstream replanning.

Material examples:

```text
new public contract
new architecture
new major dependency
new migration
significant scope increase
significant risk increase
```

---

## 5. Local validation

The implementation agent should run relevant fast checks before handoff.

```yaml
local_validation:
  enabled: true
```

Actual checks depend on project capabilities.

---

## 6. Retry

Candidate default:

```yaml
max_retries: 1
```

Retries are for transient execution problems, not for plan/context/requirement defects.

---

## 7. Future evolution

The external Implementation contract should remain compatible with future execution modes.

Future policies may add:

```text
segmented_sequential
segmented_parallel
```

but v1 runtime supports only:

```text
single_agent
```

---

## 8. Accepted decision

Multi-agent implementation is intentionally deferred until practical experience shows a clear improvement in development quality, speed, or context handling.


---

## 9. TDD policy

Implementation remains single-agent.

Optional per-step test-first execution:

```yaml
development:
  tdd:
    mode: off | auto | required
```

Recommended:

```yaml
mode: auto
```

TDD changes the internal execution loop, not the Implementation topology.
