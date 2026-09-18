# Контракт Preparation Workflow v1

> **Совместимость от 2026-09-17:** это реализованный прежний callback workflow, не целевой главный оркестратор. В [новой архитектуре](agent-centric-orchestration.md) агент ведёт подготовку, а validation/publication/sync становятся primitives. Новый явный [AgentPreparation](agent-preparation.md) реализован отдельно в TASK-0029; общие deterministic primitives вынесены из controller. Этот legacy API сохраняется; Task Manager, SQLite, ready guards и необязательность specification не меняются.

**Статус:** действующий минимальный контракт реализации TASK-0015; TASK-0015 принята пользователем и завершена (version 18).

## Владельцы состояния

`orchestrator.preparation_workflow.PreparationWorkflow` связывает существующие компоненты, но не создаёт вторую FSM или базу. Graph Runtime владеет шагом/результатами/ожиданием в памяти. Artifact Repository — телами immutable-версий. Task Manager — canonical definition, lifecycle, blockers, user decisions и run refs; используется только публичный `TaskManagerService`. Внешние смысловые адаптеры выполняют Context, Analysis, Planning и Plan Review. Проект Task Manager и Artifact Repository должны совпадать; корректную инъекцию сервисов обеспечивает caller.

## Граф

Context → Analysis → Planning → Plan Review → Package → Ready. Review `changes_required` ведёт к Planning, Analysis `needs_context` — к Context. У всех узлов объявлены `needs_input`, `blocked`, `failure`; они не позволяют пропустить `mark_ready`. Review по умолчанию ограничен двумя циклами, расширение Context — двумя запросами. После исчерпания лимита workflow регистрирует blocker и останавливается, не выполняя слепой третий цикл. Повтор заблокированного шага требует явной remediation caller-а.

Узел `ready` закрывает активную ссылку подготовки, затем вызывает реальный `TaskManagerService.mark_ready`. Оба handoff-mode останавливаются на `ready`: claim, execution preflight и исполнение не входят в компонент. Core runtime поддерживает явный `phase="preparation"`; значение по умолчанию `request` сохранено.

## Envelope адаптера

Вход: `contract`, `task`, `project_profile`, `answer`, `previous`. Все значения копируются. Review получает план/предыдущий review, но не planner scratchpad или весь raw Context. Содержимое `previous` определяется этапом и является принятым Graph Runtime result, а не историей чата.

Выход — JSON-совместимый объект только с полями `outcome`, `payload`, `question`, `reason`. Произвольный `route` не допускается. Contract names: `context-request/v1`, `analysis-request/v1`, `planning-request/v1`, `plan-review-request/v1` и соответствующие `*-result/v1`.

| Этап/исход | Минимальные поля |
| --- | --- |
| Context success | `payload.summary` (строка), `evidence_refs` (список строк) |
| Analysis success | `objective_interpretation`, списки `constraints`, `invariants`, `unknowns` |
| Analysis needs_context | `payload.requests` — непустой список конкретных запросов |
| Planning success | `goal`, `scope.in/out`, `global_constraints`, `global_validation`, непустые `work_units` |
| Plan Review changes_required | `payload.findings` — непустой список предметных замечаний |
| Plan Review approved | `findings`, `approved_binding`, `criterion_ids`, `zero_context_executable=true` |
| needs_input | Непустая `question`; payload не требуется |
| blocked/failure | Непустая `reason`; payload не требуется |

Work Unit требует уникальный `id`, `goal`, непустые списки `files_objects`, `expected_result`, `validation`; необязательный `depends_on` содержит только существующие зависимости, граф зависимостей ацикличен. Plan переносит constraints карточки, constraints и invariants Analysis без потери. Domain-specific семантика и полнота анализа остаются у адаптеров — ядро не делает вывод о качестве плана по одной структуре.

Review binding содержит точный `plan_sha256` и целочисленный актуальный `definition_version`; criterion IDs должны покрывать все критерии карточки. Findings имеют непустой `summary`, severity `info/minor/major/critical` и status `open/resolved/accepted_risk/obsolete` (по умолчанию minor/open). Major/critical требуют непустых `evidence_refs`, открытые major/critical запрещают approved. Содержательное одобрение возвращает реальный reviewer adapter, ядро его не выдумывает.

## Артефакты и handoff

Context/Analysis публикуются только в Artifact Repository, новых ролей Task Manager для них нет. Plan хранится как Markdown с полным structured JSON; проверенная проекция имеет те же байты/SHA-256 под `.orchestrator/tasks/<TASK-ID>/plan.md`. Посторонний или вручную изменённый документ не перезаписывается; ранее зарегистрированная управляемая проекция заменяется только при подтверждённом старом хеше и immutable backing record. Если definition change удалил метаданные старой проекции, caller должен явно разрешить файловый конфликт, автоматического присвоения документа нет.

Review/Execution Package — canonical JSON. Ссылки Task Manager имеют однозначный формат `<repository-ref>:<role>:<version>`; эти сегменты не содержат `:`. Plan и approved review дополнительно хранят `metadata.repository` с полным record. Execution Package содержит task ref/definition version, records Plan/Review, `prepared_source_revision`, `entrypoint=execution_preflight`. Отдельная specification.md не обязательна.

## Ожидание и синхронизация

При вопросе Task Manager переходит в `awaiting_input`, активная run-link закрывается; runtime сохраняет WaitState в памяти. `resume` требует точные непустые `wait_id`/`node_id`, валидирует новый adapter result до регистрации user decision. Затем решение clarification фиксируется публичным API, статус возвращается в preparing, ссылка связывается снова. При blocker действует аналогичный порядок с разрешением только owned blocker; внешние blockers не снимаются автоматически.

Runtime-result принимается до файловых/Task Manager эффектов, общей транзакции нет. Если `synchronize` не завершён, `inspect.sync_pending=true`, а следующий `step/resume` запрещён. Очередь сохраняет cursor успешно выполненных действий; повторный `synchronize` не повторяет planner/reviewer и завершает только оставшиеся действия. Неопределённый commit outcome, аварийный перезапуск процесса и восстановление памяти не поддерживаются.

При внешней версии `task_version_conflict` требует чтения карточки и истории. `reconcile(expected_version=...)` допускает только явно прочитанную актуальную версию с тем же definition и подготовительными артефактами, без чужого run/claim. Изменённые требования или артефакты дают `stale_preparation`; нужна новая подготовка. Guard failure не чинится фиктивными хешами, одобрением или снятием blockers.

## Ограничения

Нет встроенного LLM, автоматического filesystem discovery, PKM реализации, synthesis требований без подтверждения, auto claim, фоновых workers, multiprocess/restart recovery и полного переноса импортированных draft-схем. Caller предоставляет адаптеры и подтверждённую source revision. `RuntimeError` сообщает core wait/state ошибки; `PreparationError` — adapter/contracts/sync ошибки с code/details. Предметные проверки: [tests](../../tests/test_preparation_workflow.py), [guide](../guides/preparation-workflow.md).
