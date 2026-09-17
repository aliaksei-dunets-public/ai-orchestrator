# Development Workflow — Context Node Patch

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted patch v0.1

The Development Workflow `context` node should use the following configuration contract:

```yaml
context:
  type: subgraph
  ref: context

  config:
    knowledge_map:
      enabled: ${project_profile.context.knowledge_map.enabled}

  execution:
    model_profile: cheap
    escalation_profile: standard

  inputs:
    required:
      - task
      - project_profile

  outputs:
    artifact: context_package

  transitions:
    success: analysis
    failure: development_failed
```

Project Profile example:

```yaml
project_profile:
  context:
    knowledge_map:
      enabled: false
```

Behavior:

```text
false → Direct Discovery only

true  → PKM-assisted Context is allowed;
        Direct Discovery remains fallback
```

The `Context Package` output contract is unchanged.
