# Пауза и возобновление агентского процесса

**Статус:** действующий протокол, актуализирован в TASK-0034, 2026-09-18. Единственный runtime — AgentGraphRuntime; callback resume/step удалены.

## Процесс

Needs_input требует WaitState с непустым question, kind=user_input и новым wait_id; blocked — kind=blocker и конкретную reason. Оба исхода сохраняют текущий узел и останавливают submit. Target из формально обязательного transitions для этих исходов не используется. Нельзя автоматически угадывать причину или снимать blocker.

После реального ответа caller подаёт resume_wait с актуальными expected_revision/task_definition_version, точными wait_id/node_id и явным JSON answer. Для blocker передаётся resolution без answer после устранения причины. Принятие response — отдельный action: revision растёт, state=running, wait очищается, resumed_wait/history сохраняют ответ. Узел не выполняется; агент отдельно делает работу и подаёт новый NodeResult. Rejected result не стирает response.

Каждый accepted result, включая вопрос/blocker, расходует общий/per-node budget. Resume не расходует и не восстанавливает бюджет. Последний slot может быть потрачен на wait: после resume новый result недоступен, cancel остаётся доступен. Это политика лимитов, не дедлок. Budget должен включать вопросы и итоговые outputs.

## Связывание с задачей

Generic runtime не меняет Task Manager. AgentPreparation и AgentExecution отдельно выполняют lifecycle effects через публичный API с актуальной expected_version: ожидание закрывает active run link, execution освобождает claim, resume регистрирует clarification или разрешает собственный blocker. Preparation возвращается в preparing без claim; execution требует нового preflight/claim по своему контракту. Definition drift не разрешает продолжать старый план.

Принятый runtime action и task/files effects не являются общей транзакцией. Пока sync_pending=true, следующий action запрещён. Исправимая publication/projection ошибка требует устранения причины и synchronize; unknown task mutation требует inspect/history/reconcile_effect с фактическими свидетельствами. Не повторяйте effect вслепую.

## Потеря сессии

Task Manager run link не сохраняет current_node или response. После остановки процесса runtime память потеряна; автоматического restart recovery нет. Агент проверяет принадлежащие задаче ссылки/claim/артефакты и реальные изменения через публичный API; нельзя создавать фиктивный continuation потерянного run.

Проверки: [runtime](../../tests/test_agent_runtime.py), [preparation](../../tests/test_agent_preparation.py), [execution](../../tests/test_agent_execution.py). Действующие [runtime contract](agent-runtime-contract.md), [preparation](agent-preparation.md), [execution](agent-execution.md).
