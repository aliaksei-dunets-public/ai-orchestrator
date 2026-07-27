---
name: test-designer
description: Design a focused validation matrix that maps every acceptance criterion to at least one executable check and requires regression tests only for fixed defects.
---

# Test Designer

1. Read the exact acceptance criteria from the Task Context baseline.
2. Create focused, contract, scenario, and applicable regression `TestCaseSpec` checks.
3. Map every check to one or more exact criteria; do not add unknown criteria.
4. Call `orchestrator.testing.validate_test_plan`.
5. If a defect was fixed, require a regression case; otherwise do not label ordinary checks as regression tests.
