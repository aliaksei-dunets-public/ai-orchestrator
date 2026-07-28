# AI Orchestrator workspace instructions

## Sources of truth

1. Follow `docs/specifications/orchestrator-specification.md` for architecture and roadmap.
2. Follow `docs/specifications/task-layer-specification.md` for task contracts and state transitions.
3. Treat `docs/plans/2026-07-27-roadmap-index.md` as the ordered implementation plan set.

## Development workflow

- Implement phases in dependency order.
- Keep runtime platform-neutral; place platform behavior in profiles/adapters.
- Use Python 3.11+ and the standard library for Task Manager runtime paths.
- Add focused tests before or with implementation and run affected regression tests.
- Never weaken immutable security policies through local configuration.
- Do not edit generated platform skill projections after canonical `skills/` sources exist.
- Do not commit `.orchestrator/tasks/tasks.json`, temporary files or lock files.
- Search canonical sources by default; `releases/` is excluded through `.rgignore` and must be searched explicitly for release validation.
- Preserve unrelated user changes and avoid destructive Git operations.
- Canonical project artifacts use English; user-facing guides may have Russian companions, which are not Knowledge Graph sources.
- Apply `config/language-policy.json` when classifying documentation language or graph provenance.

## Python environment

- Use the workspace-local `.venv` for Python development and validation.
- Do not depend on a global `python` command being available in `PATH`.
- For setup, package installation and test commands, follow [the development environment guide](docs/guides/development-environment-ru.md).

## Completion evidence

A phase is complete only when its plan deliverables exist, acceptance criteria have direct evidence, relevant tests pass, specifications and registries agree, and Health Check has no `ERROR` or `CRITICAL`.
