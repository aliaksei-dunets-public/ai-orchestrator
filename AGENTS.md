# AI Orchestrator workspace instructions

## Sources of truth

1. Follow `docs/specifications/orchestrator-specification-ru.md` for architecture and roadmap.
2. Follow `docs/specifications/task-layer-specification-ru.md` for task contracts and state transitions.
3. Treat `docs/plans/2026-07-27-roadmap-index.md` as the ordered implementation plan set.

## Development workflow

- Implement phases in dependency order.
- Keep runtime platform-neutral; place platform behavior in profiles/adapters.
- Use Python 3.11+ and the standard library for Task Manager runtime paths.
- Add focused tests before or with implementation and run affected regression tests.
- Never weaken immutable security policies through local configuration.
- Do not edit generated platform skill projections after canonical `skills/` sources exist.
- Do not commit `.orchestrator/tasks/tasks.json`, temporary files or lock files.
- Preserve unrelated user changes and avoid destructive Git operations.

## Completion evidence

A phase is complete only when its plan deliverables exist, acceptance criteria have direct evidence, relevant tests pass, specifications and registries agree, and Health Check has no `ERROR` or `CRITICAL`.
