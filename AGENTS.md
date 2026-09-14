# Graph Orchestrator workspace instructions

- Treat `docs/` as design input for the new graph-based orchestrator. Documents have their own draft/accepted statuses; none alone proves runtime delivery.
- Implement the migration in the order described by `docs/roadmap.md`.
- Keep task state in a deterministic Task Manager Service and workflow-run state in Graph Runtime.
- Preserve the preparation/`ready`/execution boundary and structured artifact contracts.
- Keep the runtime platform-neutral; isolate platform behavior in adapters.
- Keep `obsolete/` read-only as a reference. Do not import, execute, or edit it to implement the new system.
- The previous release artifacts and local `.orchestrator/` state are archived in `obsolete/`; do not treat them as active state. Preserve `.venv/`, temporary files, and unrelated user data.
- Add focused tests as capabilities are implemented; do not claim a phase complete without matching code, documentation, and test evidence.
