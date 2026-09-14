# Graph Orchestrator

This repository is migrating to a graph-based AI development orchestrator. The previous implementation and its documentation are preserved under [`obsolete/`](obsolete/README.md). They are reference material, not the active runtime.

The new architecture is currently specified in [`docs/`](docs/README.md):

- [`docs/graph/`](docs/graph/) — request routing, task state, and executor loop.
- [`docs/development/`](docs/development/) — preparation and execution workflows.
- [`docs/context-knowledge/`](docs/context-knowledge/) — Project Knowledge Map.

Implementation will proceed incrementally. **No new graph runtime is shipped yet.** In particular, do not invoke code under `obsolete/` as if it implements the new contracts.

See [`docs/roadmap.md`](docs/roadmap.md) for the migration sequence.
