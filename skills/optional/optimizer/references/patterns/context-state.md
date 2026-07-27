# Context and State Patterns

Apply only to diagnosed problems.

## Progressive disclosure

Keep purpose, workflow, and routing in the entry point. Move detailed domain or
provider material into references loaded after task classification.

## Context gate

```text
classify -> identify required knowledge -> search -> load smallest sufficient evidence -> execute
```

## Search before read

List structure, search symbols or headings, inspect fragments, and open complete
files only when necessary.

## Canonical source

Keep one authoritative rule and replace copies with references. Define
precedence for unavoidable multiple layers.

## Compact task state

Store goal, phase, verified facts with sources, decisions, changed files,
validation, risks, blockers, and required next actions. Do not preserve full
conversation history as operational state.

## Delta update

Pass only new findings, changed assumptions, changes, validation results,
blockers, and remaining work.

## Invalidation

Invalidate summaries, retrieval results, and cached decisions when source files,
revision, configuration, permissions, model, or required evidence strength
changes.

## Compaction

Compact at meaningful phase boundaries or context pressure, not after every
message. Preserve decisions, evidence pointers, unresolved risks, and trust
labels. Test that compaction does not erase critical constraints.

## Prompt caching

Where supported, place stable reusable content before dynamic task content and
avoid incidental changes to the reusable prefix. Treat cache behavior as a
runtime optimization, not a reason to duplicate instructions.
