---
language: en
translation_of: skills/optional/python-code-review/README.ru.md
---

# Python Code Review Skill

Platform-neutral review skill for Python coding agents. It reconstructs system
purpose, user flows, component dependencies, state, invariants, and failure
paths before applying focused review axes and the Python reference.

Use `SKILL.md` for routing and the `references/` directory for detailed
procedures. This skill reviews by default; it implements fixes only when the
user explicitly asks for them.

[Russian version](README.ru.md)

```text
python-code-review-skill/
├── SKILL.md
├── README.md
├── THIRD_PARTY_NOTICES.md
├── references/
├── reviewers/
└── templates/
```

```text
<project>/.agents/skills/python-code-review/
<project>/.claude/skills/python-code-review/
<project>/.github/skills/python-code-review/
~/.codex/skills/python-code-review/
```

```text
Use python-code-review in PROJECT_AUDIT mode.
Reconstruct architecture, flows, state ownership, resource lifecycle,
failure propagation, and critical invariants before checklist coverage.
Do not modify files.
```

```text
Use python-code-review in CHANGE_REVIEW mode for the current branch against
origin/main. Trace changed behavior end to end, run repository-native checks,
dispatch an independent reviewer, and return a merge verdict.
```
