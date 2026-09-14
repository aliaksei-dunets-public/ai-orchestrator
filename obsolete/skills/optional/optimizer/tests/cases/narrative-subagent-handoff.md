# Case: Narrative Subagent Handoff

Mode: standard

Each subagent returns the full assignment, conversation history, internal
reasoning, raw tool output, unchanged project state, a complete user-facing
report, and several empty sections. The orchestrator appends every response to
shared state before invoking the next subagent.
