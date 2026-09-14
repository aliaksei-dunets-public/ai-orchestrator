---
name: test-runner
description: Run approved test commands with timeouts and preserve command, exit code, status, and concise output as evidence; report unavailable tools and timeouts as blockers.
---

# Test Runner

1. Accept only commands from an approved validation matrix.
2. Execute each check through `orchestrator.testing.run_test` with a finite timeout.
3. Preserve the command, exit code, status, and concise output.
4. Report non-zero exits as failures; report unavailable tools and timeouts as blocked evidence.
5. Do not convert blocked or failed checks into a passing result.
