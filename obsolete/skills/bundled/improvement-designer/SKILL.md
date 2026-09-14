---
name: improvement-designer
description: Convert an audit finding into an exact, revision-bound improvement proposal with rollback and regression evidence, without changing the repository or bypassing Task Manager approval.
---

# Improvement Designer

1. Read one evidenced audit finding.
2. Produce an exact proposed diff, baseline revision, rollback instructions, and regression test.
3. Call `orchestrator.improvement.design_improvement`; do not apply the diff.
4. Create and register a normal Task Context through Task Manager.
5. Require approval for the exact diff hash and revision; fail closed on mismatch or local override.
