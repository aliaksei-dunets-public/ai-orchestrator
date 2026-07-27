---
name: project-onboarding
description: Collect evidence-based project facts, propose a complete Project Context diff, preserve manual ownership blocks, and exclude secrets and generated trees.
---

# Project Onboarding

1. Collect facts with `orchestrator.onboarding.collect_facts`; do not read ignored secret files or generated trees.
2. Render the owned generated section and preserve the exact manual block.
3. Run `onboard(..., dry_run=True)` and present the complete diff for approval.
4. Refuse writes when ownership markers conflict.
5. After approval, apply once and verify that a second dry run is empty.
