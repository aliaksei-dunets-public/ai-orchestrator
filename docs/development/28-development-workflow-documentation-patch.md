# Development Workflow — Documentation Patch

**Status:** Accepted patch v0.1

Updated tail of Development Workflow:

```text
CODE REVIEW
      ↓ approved
TESTING
      ↓ passed
DOCUMENTATION SUBGRAPH
      │
      ├── no_change
      │      ↓
      │  FINAL VALIDATION
      │
      ├── external docs updated
      │      ↓
      │  FINAL VALIDATION
      │
      ├── source-adjacent docs updated
      │      ↓
      │  DELTA CODE REVIEW
      │      ↓
      │  TARGETED VALIDATION
      │      ↓
      │  FINAL VALIDATION
      │
      └── runtime-affecting change discovered
             ↓
      IMPLEMENTATION / PLANNING
```

Current reusable subgraph library:

```text
context
analysis
impact-analysis
planning
implementation
testing
documentation
documentation-impact
```

`documentation-impact` is extracted as a reusable inner capability/subgraph because it can be useful outside the Development Workflow.


---

## Documentation domains included

The Documentation Subgraph evaluates impact across:

```text
Domain / Business documentation
Technical documentation
Architecture documentation
API / Contract documentation
Developer documentation
Operational documentation
```

Domain / Business documentation explicitly covers:

```text
business rules
validations
state transitions
workflows
invariants
edge cases
terminology
```
