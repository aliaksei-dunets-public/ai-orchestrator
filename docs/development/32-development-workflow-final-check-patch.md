# Development Workflow — Final Check Patch

**Status:** Accepted patch v0.2

## Updated Development Workflow

```text
REQUEST ROUTER
      ↓
TASK
      ↓
CONTEXT
      ↓
ANALYSIS
      ↓
PLANNING
      ↓
PLAN REVIEW
      ↓
IMPLEMENTATION
      └── optional TDD
      ↓
CODE REVIEW
      ↓
TESTING
      ↓
DOCUMENTATION
      ↓
READINESS GATE
      │
      ├── not ready → owning stage
      │
      └── ready
              ↓
      ACCEPTANCE PACKAGE
              ↓
      AWAITING ACCEPTANCE
              ↓
      USER ACCEPTANCE
        │       │        │
        │       │        └── more validation → TESTING
        │       │
        │       └── rejected → classified remediation
        │
        └── approved
               ↓
            COMPLETE
```

## Important boundary

```text
Testing
= automated/system verification

User Acceptance
= user confirms the delivered behavior solves the intended problem
```

Integration/E2E tests remain part of Testing.

Final Check may request them but does not execute them itself.

## New Task Manager state

```text
Awaiting Acceptance
```

This state means:

```text
engineering gates complete
acceptance candidate prepared
user approval pending
```


---

## Task Manager Service integration

Final Check does not mutate Task files directly.

```text
Readiness ready
+ Acceptance Package
      ↓
TaskManagerService
      ↓
Task status = awaiting_acceptance
```

After user approval:

```text
User Acceptance = approved
      ↓
TaskManagerService.record_user_decision()
      ↓
TaskManagerService.complete_task()
      ↓
Task status = completed
```

After rejection or request for additional validation:

```text
Task status = active
```

and Graph Runtime resumes the appropriate remediation/testing path.

Task Manager stores lifecycle state; Graph Runtime stores the exact workflow node.
