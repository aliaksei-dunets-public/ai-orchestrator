# Documentation Policy

**Status:** Accepted policy draft v0.1

## 1. Default

```yaml
documentation:
  enabled: true

  impact_check:
    required: true

  update_only_when_impacted: true
```

Documentation stage is always evaluated for managed Development work, but actual edits are conditional.

---

## 2. Project configuration

Candidate configuration:

```yaml
documentation:
  enabled: true

  targets:
    domain_business: true
    architecture: true
    technical: true
    api: true
    developer_guides: true
    inline_source_docs: true

  source_adjacent:
    require_delta_code_review: true
    require_targeted_validation: true

  drift:
    fix_unrelated: false
```

Project Profile defines real documentation sources and validation tools.

---

## 3. Impact policy

Update documentation when implementation changes one or more:

```text
public behavior
public/internal contract that developers rely on
configuration
architecture
developer usage
operational procedure
migration behavior
error/recovery behavior
```

Normally skip updates for:

```text
pure internal refactor with unchanged contracts/behavior
formatting
mechanical cleanup
test-only internal changes
```

unless project policy requires otherwise.

---


## 3A. Domain / Business documentation policy

Domain documentation should be updated when the task changes:

```text
business behavior
business rule
validation
state/lifecycle transition
business workflow
invariant
edge-case semantics
business terminology
```

Domain documentation should describe:

```text
what is allowed
what is prohibited
under which conditions
what state changes occur
what state changes must not occur
how the business process behaves
```

It should avoid implementation-specific details unless those details are themselves part of the business contract.

For example, prefer:

```text
A settled payment cannot be cancelled.
```

over:

```text
PaymentService.cancel checks SETTLEMENT_STATUS before calling repository.save().
```


## 4. Scope policy

Documentation should update the smallest authoritative set of documents.

Avoid:

```text
duplicating the same explanation in many docs
creating new docs without need
rewriting unrelated sections
```

Prefer updating existing sources of truth.

---

## 5. Post-testing modification safety

Because Documentation follows Testing:

### external_doc

```text
update → validate → Final Validation
```

### source_adjacent_doc

```text
update → delta Code Review → targeted validation → continue
```

### runtime_affecting_contract

```text
do not edit here
→ Implementation/Planning
→ Code Review
→ Testing
```

This policy prevents bypassing earlier quality gates.

---

## 6. Documentation validation policy

Run available deterministic checks.

Examples:

```text
markdown lint
link validation
docs build
code sample compilation
reference validation
generated-doc consistency
```

Use AI for semantic consistency only where needed.

---

## 7. ADR policy

Create/update ADR only when:

```text
architecture decision exists
decision is materially important
project policy calls for an ADR
```

Do not generate ADRs for routine implementation details.

---

## 8. Inline/source documentation

Source-adjacent documentation should be updated when:

```text
public symbol behavior changed
contract changed
existing source doc becomes false
project convention requires it
```

Do not flood code with comments explaining obvious implementation.

---

## 9. Drift policy

Default:

```yaml
fix_unrelated: false
```

Unrelated documentation drift becomes a maintenance finding.

Exception:

```text
direct contradiction in the same touched documentation area
```

may be fixed if small and safe.

---

## 10. Failure policy

Documentation failure blocks completion when:

- mandatory external/API/migration docs are missing;
- project policy marks documentation as required;
- changed behavior would otherwise be undocumented in an authoritative source.

Noncritical optional documentation tooling failures may yield:

```text
success_with_warning / maintenance candidate
```

according to project policy.

---

## 11. Reuse policy

`documentation-impact` should be reusable across workflows.

The full Documentation subgraph can be reused whenever a workflow produces project changes requiring synchronized documentation.

---

## 12. Recommended v1

```yaml
documentation:
  enabled: true
  impact_check:
    required: true
  update_only_when_impacted: true
  source_adjacent:
    require_delta_code_review: true
    require_targeted_validation: true
  drift:
    fix_unrelated: false
```

---

## 13. Accepted decisions

1. Documentation impact is always evaluated.
2. Documentation is updated only when impacted.
3. External and source-adjacent documentation are treated differently.
4. Runtime-affecting contracts return upstream.
5. Unrelated documentation debt does not expand the current task.
6. Documentation must describe the actual tested implementation, not merely the plan.
