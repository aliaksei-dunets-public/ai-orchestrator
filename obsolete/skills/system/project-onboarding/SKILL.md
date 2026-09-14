---
name: project-onboarding
description: Collect evidence-based project facts, propose a complete Project Context diff, preserve manual ownership blocks, and exclude secrets and generated trees.
---

# Project Onboarding

Lead the user through platform-neutral onboarding. The Git submodule or copied
package containing this skill is the active Core in place; do not copy it into
the target project.

## Workflow

1. Resolve `scripts/onboard_project.py` relative to this `SKILL.md`. Never ask
   the user to import an internal Python API.
2. Run `inspect --target <project>` before writing anything.
3. When the result is `needs_input`, ask only the returned questions. Present
   every choice with its description and identify the recommended choice.
   Preserve the returned question IDs and choice IDs exactly.
4. Invoke the bundled `knowledge-curator` skill for a read-only source inventory.
   Ask it to produce a small evidence-based `knowledge_graph` proposal with
   project-relative source paths. It may return an empty proposal when evidence is
   insufficient. Do not let discovery write target files.
5. Add the proposal under `answers.knowledge_graph` without credentials,
   secret-like labels or agent-supplied source digests. The proposal is validated by
   Core and becomes part of the onboarding preview.
6. Run `plan` with the collected answers. If new questions appear, continue the
   dialogue one question at a time.
7. Present the complete preview: Core path and version, selected profiles,
   proposed graph nodes/edges and their sources,
   every file diff, validation steps, rollback paths and `plan_hash`.
8. Ask for one explicit approval bound to that exact `plan_hash`. Explain that
   approval includes graph writes and automatic rollback when validation reports
   `ERROR` or `CRITICAL`.
9. Only after approval, run `apply --approved-plan-hash <hash>` with the same
   answers.
10. Report `completed`, `rolled_back` or `rollback_failed`, including findings
   and the report path. Never describe a rolled-back installation as complete.
11. Verify that canonical memory entries/events/approvals and knowledge
   ontology/nodes/edges are tracked, while proposals, indexes, and migration
   backups are ignored.

## Script interface

```text
python scripts/onboard_project.py inspect --target <project>
python scripts/onboard_project.py plan --target <project> --answers <answers.json>
python scripts/onboard_project.py apply --target <project> --answers <answers.json> --approved-plan-hash <hash>
python scripts/onboard_project.py rollback --target <project>
```

`--answers-json` may be used instead of `--answers`. Answers contain only
question IDs and selected choice IDs; never put credentials or secret material
in them.

## Invariants

- Do not read ignored secret files or generated trees.
- Do not write before approval.
- Refuse conflicting ownership markers.
- Preserve the exact Project Context manual block and all instruction content
  outside AI Orchestrator markers.
- Treat a changed preview hash as stale approval and return to planning.
- Do not weaken immutable security policies or bypass failed validation.

## Optional skills

After technology profiles are confirmed, present their
`recommended_optional_skills` as a read-only proposal. Explain why each skill
matches the detected stack. Do not create `.orchestrator/skills.json` or
change a platform projection until the user approves the exact selection.
After approval, record only the approved IDs and synchronize the projection.
