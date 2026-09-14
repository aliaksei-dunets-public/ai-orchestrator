# Development TDD Policy

**Status:** Recommended v1 policy

## 1. Default

```yaml
development:
  tdd:
    mode: auto

    require_regression_test_for_bugfix: true
```

---

## 2. Selection rules

### Prefer TDD

```text
bugfix
domain/business rule
validation behavior
state transition
algorithm
regression-prone service logic
```

### Prefer characterization-first

```text
behavior-preserving refactoring
legacy code without sufficient tests
```

### Usually normal implementation + validation

```text
documentation
mechanical config
generated files
formatting
simple metadata
UI layout-only changes
```

---

## 3. Planning integration

Each implementation-relevant plan step may define:

```yaml
testing_strategy:
  mode:
    tdd | characterization | test_after | existing_tests | not_applicable

  level:
    unit | component | integration | contract | e2e

  behaviors: []
```

---

## 4. Plan Review integration

Plan Review checks:

- appropriate strategy selected;
- bugfix has regression protection;
- critical behavior has meaningful verification;
- selected test level can actually prove the behavior.

---

## 5. Implementation integration

`mode: tdd`:

```text
RED
→ GREEN
→ REFACTOR
```

`mode: characterization`:

```text
BASELINE / CHARACTERIZE
→ REFACTOR
→ VERIFY
```

---

## 6. Testing integration

Downstream Testing remains mandatory according to project policy.

TDD does not mean:

```text
new tests passed
therefore skip integration/regression testing
```

---

## 7. Exceptions

If TDD is selected but cannot be performed:

```yaml
tdd_exception:
  reason: string
  evidence: []
  fallback:
    test_after | integration_verification | manual_validation
```

A required-mode exception should be visible to Code Review.

---

## 8. Accepted recommendation

For v1 use:

```yaml
mode: auto
```

This provides TDD where it has high value without forcing it onto unsuitable work.
