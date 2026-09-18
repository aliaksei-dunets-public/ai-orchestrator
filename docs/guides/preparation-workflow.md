# Миграция подготовки на AgentPreparation

**Статус:** действующая инструкция миграции TASK-0034, 2026-09-18. PreparationWorkflow с callbacks удалён; прежние adapters/step/resume_blocked не поддерживаются.

Начните с [исполнимого примера AgentPreparation](agent-preparation.md). Facade создаётся с явным project_root и сам использует публичный Task Manager и ArtifactRepository данного проекта.

1. Прочитайте карточку и передайте актуальную expected_task_version и проверяемую prepared_source_revision в start.
2. Читайте request/available_actions; агент выполняет текущую смысловую работу и передаёт Context/Analysis/Plan/Review envelope в submit с process revision и task version.
3. Package/Ready принимают только outcome=success; реальные payload и guards формируют deterministic primitives. Готовность не начинает исполнение.
4. Для вопроса подайте needs_input/question, для blocker — blocked/reason. После реального ответа или устранения причины используйте resume_wait с точными wait_id/node_id/версиями, answer либо resolution. Затем отдельно подайте новый результат того же узла.
5. Pending publication/projection требует synchronize; неизвестный task effect — inspect/history и reconcile_effect. Не повторяйте semantic submit и не перезаписывайте пользовательский plan.md ради обхода ошибки.

Plan/review/package сохраняют definition и SHA-256 bindings. Definition drift требует новой подготовки, а версия task не заменяет process revision. Исполнение начинается через [preflight и claim](agent-execution.md). При потере процесса continuation по одной ссылке Task Manager невозможен.

Проверки: `python -m unittest tests.test_agent_preparation`. [Отчёт миграции и удаления](../reports/2026-09-18-task-0034-callback-removal.md).
