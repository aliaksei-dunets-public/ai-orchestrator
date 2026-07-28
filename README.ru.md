---
language: ru
translation_of: README.md
---

# AI Orchestrator

Переносимый настраиваемый оркестратор навыков, workflow, задач, памяти и
проектного контекста для агентных платформ и технологических стеков.

## Документация

- [Архитектурная спецификация на английском](docs/specifications/orchestrator-specification.md)
- [Спецификация Task Layer на английском](docs/specifications/task-layer-specification.md)
- [Русская версия архитектурной спецификации](docs/specifications/orchestrator-specification-ru.md)
- [Русская версия спецификации Task Layer](docs/specifications/task-layer-specification-ru.md)
- [English README](README.md)

English README является каноническим пользовательским документом. Эта версия
сохраняется как русское пояснение и не используется Knowledge Graph.

```powershell
python -m orchestrator telemetry --json
python -m orchestrator context --root . --mode standard --term task-manager
python -m orchestrator memory --root . list
python -m orchestrator knowledge --root . list
```
