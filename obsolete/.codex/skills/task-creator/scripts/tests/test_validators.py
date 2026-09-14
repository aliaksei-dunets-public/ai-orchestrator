from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


plan_validator = load_module("validate_plan", "validate_plan.py")
context_validator = load_module("validate_task_context", "validate_task_context.py")


VALID_PLAN = """# Phase 0 Implementation Plan

**Goal:** Create contracts.
**Architecture:** Keep schemas separate. Validate them with standard tooling.
**Tech Stack:** Markdown and JSON Schema.

## Global Constraints
- No runtime dependency.
## Deliverables
- `config/schemas/task.json`.
## Dependencies
- None.
## Acceptance Criteria
- Schema validates fixtures.
## Testing Strategy
- Run the contract suite.
## Risks and Rollback
- Revert the schema commit.
## Implementation Tasks
### Task 1: Registry schema
**Files:**
- Create: `config/schemas/task.json`
**Interfaces:**
- Consumes: Task specification.
- Produces: JSON Schema.
**Acceptance:**
- Valid fixture passes.
**Tests:**
- `python -m unittest tests.contracts`
- [ ] **Step 1:** Add invalid and valid fixtures.
"""

VALID_CONTEXT = """---
schema_version: 1
id: null
title: Create contracts
type: feature
mode: quick
risk: low
created_by: task-creation-workflow
---
# Create contracts
## User Request
Create it.
## Goal
Provide contracts.
## Scope
Bounded work.
### In Scope
- Schema.
### Out of Scope
- CLI.
## Acceptance Criteria
- Fixture passes.
## Implementation Plan
- Add schema.
## Open Questions
- None.
"""


class PlanValidatorTests(unittest.TestCase):
    def test_valid_plan_passes(self) -> None:
        self.assertEqual(plan_validator.validate_text(VALID_PLAN), [])

    def test_missing_task_tests_fails(self) -> None:
        errors = plan_validator.validate_text(VALID_PLAN.replace("**Tests:**", "**Checks:**"))
        self.assertTrue(any("missing **Tests:**" in error for error in errors))

    def test_placeholder_fails(self) -> None:
        errors = plan_validator.validate_text(VALID_PLAN + "\nTODO\n")
        self.assertTrue(any("placeholder" in error for error in errors))


class ContextValidatorTests(unittest.TestCase):
    def test_valid_quick_draft_passes(self) -> None:
        self.assertEqual(context_validator.validate_text(VALID_CONTEXT, "draft"), [])

    def test_status_is_rejected(self) -> None:
        invalid = VALID_CONTEXT.replace("risk: low", "risk: low\nstatus: backlog")
        errors = context_validator.validate_text(invalid, "draft")
        self.assertIn("status is forbidden in Task Context", errors)

    def test_registered_context_requires_revision_and_execution_record(self) -> None:
        invalid = VALID_CONTEXT.replace("id: null", "id: TASK-0001")
        errors = context_validator.validate_text(invalid, "registered")
        self.assertTrue(any("revision" in error for error in errors))
        self.assertTrue(any("Execution Record" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
