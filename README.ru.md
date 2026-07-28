---
language: ru
translation_of: README.md
---

# AI Orchestrator

Переносимый настраиваемый оркестратор навыков, workflow, задач, памяти и
проектного контекста для агентных платформ и технологических стеков.

## Документация

- [Архитектура orchestrator на английском](docs/architecture/orchestrator-core.md)
- [Контракт Task Layer на английском](docs/architecture/task-layer.md)
- [Индекс документации](docs/INDEX.md)
- [Политика документации](docs/documentation-policy.md)
- [English README](README.md)

English README является каноническим пользовательским документом. Эта версия
сохраняется как русское пояснение и не используется Knowledge Graph.

```powershell
python -m orchestrator telemetry --json
python -m orchestrator context --root . --mode standard --term task-manager
python -m orchestrator memory --root . list
python -m orchestrator knowledge --root . list
```
