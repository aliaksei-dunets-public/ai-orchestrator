# Context Node — Knowledge Map Configuration

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted design v0.1  
**Scope:** Development Workflow / universal Context capability

## 1. Purpose

Project Knowledge Map support is optional.

The `Context` node must be able to operate in two modes:

```text
Knowledge Map enabled
Knowledge Map disabled
```

Disabling Knowledge Map usage must not disable the Context node itself.

When Knowledge Map usage is disabled, Context falls back to Direct Discovery.

## 2. Project-level configuration

Recommended configuration:

```yaml
context:
  knowledge_map:
    enabled: false
```

The setting belongs to the Project Profile because different target projects may choose different context strategies without changing the universal workflow.

Recommended default:

```yaml
enabled: false
```

Projects that want PKM-assisted Context explicitly enable it:

```yaml
context:
  knowledge_map:
    enabled: true
```

## 3. Context node configuration

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
    - task
    - project_profile

  outputs:
    - context_package
```

## 4. Routing behavior

### Knowledge Map disabled

```text
CONTEXT REQUEST
      ↓
knowledge_map.enabled = false
      ↓
DIRECT DISCOVERY
      ↓
CONTEXT PACKAGE
```

No PKM query, health check, or PKM dependency is required.

### Knowledge Map enabled

```text
CONTEXT REQUEST
      ↓
knowledge_map.enabled = true
      ↓
CONTEXT STRATEGY ROUTER
      │
      ├── PKM usable
      │      ↓
      │  Knowledge-Assisted Discovery
      │
      └── PKM unavailable / unsuitable
             ↓
         Direct Discovery
      ↓
CONTEXT PACKAGE
```

Enabling PKM means:

> Context is allowed to use the Project Knowledge Map.

It does not mean PKM must always be used.

Direct Discovery remains the fallback.

## 5. Decision table

| Config | PKM state | Context strategy |
|---|---|---|
| `enabled: false` | any | Direct Discovery |
| `enabled: true` | available and usable | Knowledge-Assisted / Hybrid |
| `enabled: true` | unavailable | Direct Discovery |
| `enabled: true` | unhealthy / unsuitable | Direct Discovery or Hybrid according to Context policy |

## 6. Scope of the switch

This configuration controls only:

```text
Context → Project Knowledge Map usage
```

It does not automatically control:

- PKM Bootstrap;
- PKM Refresh;
- PKM Audit;
- PKM persistence;
- other future workflows that may use PKM.

Those capabilities may receive their own independent configuration later.

## 7. Override support

The Project Profile provides the default.

A workflow or node may optionally override it when necessary.

Precedence:

```text
Node override
    ↓
Workflow override
    ↓
Project Profile
    ↓
Core default
```

## 8. Design principle

The Context contract remains identical regardless of strategy.

```text
Task / Context Request
        ↓
Context capability
        ↓
Context Package
```

Downstream nodes must not need to know whether the package was built through Direct Discovery, Knowledge-Assisted Discovery, or Hybrid discovery.

## 9. Accepted decision

The universal orchestrator treats Project Knowledge Map as an optional Context accelerator.

Canonical configuration:

```yaml
context:
  knowledge_map:
    enabled: true | false
```

`false` guarantees full operation through Direct Discovery.
