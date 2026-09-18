# Материалы `docs/graph/`

Новое [агент-центричное направление](../architecture/agent-centric-orchestration.md) от 2026-09-17 заменяет controller-centric развитие: агент выбирает допустимое действие, Workflow Graph задаёт политику, сервисы проверяют состояние. Python Executor Loop не становится основным оркестратором. Task Manager с SQLite и его guards сохраняются без изменений. Материалы этого каталога переносятся предметно по [новому roadmap](../roadmap.md), не как прежний controller design целиком.

Каталог содержит импортированные проектные материалы графового подхода. Они используются как исходники для сверки, но не являются автоматическим доказательством реализованной функциональности.

Действующие решения v1 находятся в русскоязычных документах `docs/architecture/` и `docs/guides/`:

- [состояние и хранение](../architecture/state-and-storage.md) закрепляет SQLite как источник истины задач;
- [Workflow Run](../architecture/workflow-run.md) описывает одну real-time сессию агента;
- [пауза и продолжение](../architecture/workflow-pause-resume.md) описывают `awaiting_input` в той же сессии;
- [Task Manager](../architecture/task-manager.md) описывает границу сервиса;
- [Request Router → Task Creator](../guides/request-flow.md) — реализованный входной срез.

Упоминания `task.yaml`, `events.jsonl`, файлового репозитория и коммитов состояния задач в этих материалах являются историческими. Task Executor Loop и конкурирующие workers — варианты будущего расширения; для текущего v1 они не реализуются.

Перед реализацией сверяйся с [текущим статусом проекта](../project-status.md) и [roadmap](../roadmap.md), а не с отдельным импортированным фрагментом.
