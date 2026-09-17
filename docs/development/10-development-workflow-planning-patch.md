# Development Workflow — Planning Patch

> **Актуализация 2026-09-17:** это импортированный проектный исходник. Реализованный минимальный срез TASK-0015 определяет [русский контракт Preparation Workflow](../architecture/preparation-workflow.md): canonical definition в карточке Task Manager, specification.md не обязательна, Review → Package → Ready без автоматического исполнения. Полные схемы, модельная эскалация и PKM из этого документа не означают наличие реализации; смысловые адаптеры предоставляет caller.

**Status:** Accepted patch v0.1

## Updated composition

```text
Development Workflow
│
├── Context Subgraph
│
├── Analysis Subgraph
│     └── Impact Analysis Subgraph
│
├── Planning Subgraph
│
├── Plan Review Gate
│
├── Implementation Node
│
├── Code Review Gate
│
├── Testing Subgraph
│
├── Documentation Subgraph
│
├── Final Validation Gate
│
└── Complete Action
```

## Analysis → Planning → Review

```text
IMPLEMENTATION ANALYSIS
        ↓
PLANNING SUBGRAPH
        ↓
IMPLEMENTATION PLAN
        ↓
PLAN REVIEW
   │             │
approved     changes_required
   │             │
   │             └────► PLANNING
   ▼
IMPLEMENTATION
```

## Reuse hierarchy

```text
Development Workflow
│
├── Context
│
├── Analysis
│     └── Impact Analysis
│
└── Planning
```

Current reusable subgraphs:

```text
context
analysis
impact-analysis
planning
testing
documentation
```

Plan Review remains a separate gate for now.

It may later become reusable if the same review contract proves useful across multiple workflows.
