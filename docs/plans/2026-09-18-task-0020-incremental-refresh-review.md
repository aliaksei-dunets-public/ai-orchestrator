# Self-review TASK-0020 — Incremental Refresh

**Статус:** внутренний review подготовки, 2026-09-18; не независимый аудит и не приёмка результата.

План использует только существующий Graphify 0.9.63 и `ProjectKnowledgeService`. Native `graphify update` остаётся provider-механикой; orchestrator не редактирует graph artifacts напрямую. Staging и atomic publication сохраняют текущие failure guarantees. Manifest становится частью immutable index, чтобы incremental path отличал unchanged от changed files. Legacy indexes без manifest не считаются доказанно incremental-ready.

Покрытие критериев TASK-0020: изменённые/добавленные/удалённые/переименованные files, dependency impact, source drift, provider failure, no-op и full fallback проверены предметными тестами и одним pinned real fixture. `AgentExecution.precommit_gate` возвращает orchestration result и `commit_allowed`, но не выполняет commit и не меняет Task Manager. Документы/semantic extraction не входят в этот срез; их обновление остаётся отдельным host-agent admission path TASK-0031.

Открытое ограничение: Graphify CLI update не обещает semantic document refresh и может сохранить upstream diagnostics (dangling imports/self-loops). Эти diagnostics должны быть видимы в coverage, а не скрыты.
