# Удаление callback GraphRuntime

**Статус:** исходные границы TASK-0034, уточнённые пользователем 2026-09-18; удаление выполнено и проверено следующим этапом. Этот документ сохраняет основание подготовки; текущие результаты — в отчёте кандидата, plan/review/Execution Package — в карточке Task Manager.

> **Результат следующего этапа:** удаление выполнено и проверено после разрешения пользователя приступить к исполнению. [Отчёт кандидата](../reports/2026-09-18-task-0034-callback-removal.md). Ниже сохранены исходные границы и зависимости на момент подготовки; текущие модели находятся в runtime_contracts, а callback-модули удалены.

Пользователь после разбора аудита указал: «GraphRuntime я думаю нужно удалить и обновить документацию об этом». TASK-0034 переориентирована с ремонта callback-runtime на его удаление из активного ядра. Единственным runtime процесса должен остаться `AgentGraphRuntime`, который принимает явные результаты агента. Предыдущее требование сохранять callback API снимается для этой задачи.

## Подтверждённые зависимости

- `orchestrator/preparation_workflow.py` создаёт GraphRuntime и выполняет callbacks; заменяющий агентский facade — `AgentPreparation`.
- `orchestrator/__init__.py` экспортирует оба runtime и оба preparation facade; callback exports подлежат удалению.
- `workflow_runtime.py` одновременно содержит общий Graph/Node/NodeResult/WaitState/WorkflowRun, RuntimeError, терминальные константы и validator. Их используют AgentGraphRuntime, AgentPreparation, AgentExecution, PreparationPrimitives и KnowledgeRefreshNode. Общие контракты требуется сохранить и отделить от удаляемого исполнителя; имя нового модуля определяется при подготовке.
- `preparation_primitives.py` импортирует GraphRuntime, хотя основная общая логика уже вынесена из callback facade; импорт и реально ненужные callback-ветви требуется убрать после проверки использования агентским путём.
- `tests/test_workflow_runtime.py`, `tests/test_preparation_workflow.py` проверяют удаляемый путь; `tests/test_agent_runtime.py` отдельно закрепляет legacy compatibility. Нужные структурные, storage/sync и ready-guard проверки следует сохранить или перенести, а проверки существования удалённого API заменить.

## Результат задачи

Удалить класс GraphRuntime, callback PreparationWorkflow, их exports и активные зависимости. Не оставлять alias GraphRuntime на AgentGraphRuntime: их сигнатуры и семантика различаются. Общие модели, структурная валидация, артефакты, ready/claim guards, process revisions, ожидания и бюджеты сохраняются. Переименовывать AgentGraphRuntime в рамках этого решения не требуется.

Документация должна описывать агентский путь как единственный поддерживаемый. Существующие callback guides либо заменить инструкцией миграции, либо явно пометить историческими с переходом к действующим материалам. Исторические отчёты о выполненных этапах сохраняют факты на дату проверки; они не являются обещанием поддержки callback API после удаления. Ссылки должны оставаться рабочими. До реализации project-status продолжает честно указывать, что callback-код ещё присутствует.

Ремонт legacy concurrency/cancel reason и сохранение его API исключены из новых критериев: их устраняет удаление пути. Оценка копирования history/payload AgentGraphRuntime остаётся оправданной частью аудита. Не вводятся durable runtime, schema registry, новые внешние сервисы или обход лимитов. Task Manager и `obsolete/` не изменяются.

Основание: [разбор аудита](../reports/2026-09-18-graph-runtime-audit-triage.md), [контракт агентского runtime](../architecture/agent-runtime-contract.md), [AgentPreparation](../architecture/agent-preparation.md), [AgentExecution](../architecture/agent-execution.md).
