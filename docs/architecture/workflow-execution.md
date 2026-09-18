# Исполнение конфигурируемых workflow

**Статус:** реализованный Python in-process контракт TASK-0037, 2026-09-18; кандидат для отдельной пользовательской приёмки.

## Граница ответственности

[WorkflowBuilder](workflow-builder.md) проверяет и компилирует определение. `WorkflowExecutor` из `orchestrator.workflow_execution` исполняет **один узел на явный step** через доверенные host adapters. `AgentGraphRuntime` хранит CAS, outcomes, waits, budgets и history; executor в него не добавлен. Task Manager Service и его SQLite/API не изменены.

Реестры адаптеров и handlers создаёт host-код. TOML не импортирует Python, не определяет shell-команду и не разрешает физический эффект сам по себе. Effects описывают ожидаемое поведение; файлового sandbox и автоматического rollback нет. Adapter обязан соблюдать instruction/skill, capability и запреты своего host-а. Режим single_agent: один вызов на шаг, без автоматических subagents, parallel dispatch и эскалации по качеству.

## Исполнители и модели

`ExecutorRegistry.register_model(ModelAdapter(executor_ref, provider, available, invoke))` регистрирует один adapter на provider. `available(profile)` возвращает bool для точного provider/model/requested reasoning. Отсутствующий adapter или false означает model_unavailable; ошибка probe означает availability_failed. Автоматической подстановки current agent нет.

`invoke(request)` получает effective execution/config/effects, входные payload, immutable input references, output schemas, outcomes и selected_executor. Agent transport возвращает `{provider, model, result}`; provider/model обязаны совпасть с выбором. Result содержит outcome, outputs и необязательный wait. Несовпадение identity отклоняется как executor_mismatch. Receipt записывает executor_ref, requested/executed profile, provider/model, requested reasoning и fallback_reason. Подтверждение модели — заявление доверенного host transport, не независимое криптографическое доказательство провайдера.

Fallback задаётся явно при создании executor: `fallbacks={"expert": ["standard"]}`. Список фиксируется для run, копируется и публикуется с inputs. Используется первый доступный профиль; fallback не рекурсивный, не срабатывает при timeout/probe failure и не меняется по оценке качества. Model profiles закреплены в snapshot, но подключение transport и разрешение fallback остаются отдельной доверенной host policy; credentials и внешние SDK snapshot не покрывает.

`register_capability(name, invoke, executor_ref=...)` задаёт tool/deterministic executor. Он получает тот же request, возвращает result без model wrapper; модель не выбирается.

`orchestrator.model_process_adapter.process_model_adapter(...)` — отдельный платформенный transport. Host задаёт argv, timeout и предел ответа (по умолчанию 2 MiB), shell=False; на Windows процесс скрыт. stdin/stdout содержат один UTF-8 JSON. Probe: `{operation:"probe", profile}` → `{available, provider, model}`. Invoke: `{operation:"invoke", request}` → `{provider, model, result}`. Ошибка/timeout не вызывают повтор или fallback после возможного эффекта. Wrapper отвечает за реальный CLI/SDK вызов, identity и очистку своих дочерних процессов. Прямой adapter конкретного LLM-провайдера и новые API-ключи этой задачей не настраиваются.

## Передача артефактов

`start(inputs, task_ref=None, task_definition_version=None)` проверяет ровно объявленные входы и публикует definition/inputs/policy. Snapshot digest и соответствие Graph проверяются; payload/snapshot/node evidence ограничены 2 MiB. Один executor связан с одним in-memory run.

`request()` материализует bindings из текущего scope и проверяет schemas, SHA и immutable record. Каждый accepted step публикует node_evidence с входными refs, outputs, receipt и outcome; runtime получает портовые references/value. Exit подграфа возвращает объявленные aliases caller-у, root exit формирует `inspect()["result"]` даже при failed workflow. Новый вызов подграфа создаёт чистый scope; новый результат производителя удаляет прежние optional ports. Snapshot и inspect/request возвращают отделённые контейнеры.

`step(expected_revision=...)` проверяет revision/actions/общий и per-node budget до вызова. Перед и после вызова выполняется optional guard host-а. Ошибки ответа/schema, timeout, owner drift или публикации оставляют pending_effect; transport повторно не вызывается. `recover_result(response, expected_revision=..., resolution_ref=...)` принимает сверенный результат без нового physical effect. Immutable записи не переписываются: при повторной публикации используется новая версия; неподтверждённые orphan evidence могут остаться в repository.

Needs_input/blocked требуют объявленных outcomes и WaitState; `resume_wait(expected_revision, wait_id, answer/resolution)` — отдельный action. Историю и pending состояние executor хранит в памяти, persistent nested runtime и восстановление после перезапуска отсутствуют.

## Plan/Review/Package и preflight

`WorkflowSource(definition, libraries, overlay=None)` нормализует доверенные host paths и перечитывает файлы при load. `AgentPreparation(..., workflow_source=source)` сохраняет immutable snapshot и добавляет `{digest, snapshot, source}` в structured Plan и Execution Package. Approved Review требует тот же workflow_digest вместе с plan_sha256/definition_version. Ready проверяет snapshot и текущие источники. Подложить binding через произвольный planning payload нельзя.

`ExecutionPreflight(..., workflow_source=source)` требует тот же source и digest перед claim. Изменение effective TOML/overlay/component/schema, отсутствие snapshot или источника отклоняется. Пути из package сами по себе не читаются: текущую конфигурацию предоставляет host. Комментарий TOML, не меняющий snapshot, не обязан менять digest. Loaded schemas/provenance участвуют в digest, как в контракте builder.

`AgentExecution(..., workflow_source=source)` использует этот preflight. После claim `_integrity` проверяет immutable binding; текущие TOML не перечитываются для изменения активной политики. Компоненты строятся из закреплённого snapshot. Code-corpus checkpoint/source guards сохранены. Остальные docs/config/dependencies, внешние adapters и credentials этим binding не покрыты; filesystem TOCTOU сохраняется.

Legacy подготовка/исполнение без workflow_source продолжают работать с прежними envelopes. Config-bound package без WorkflowSource не может silently запуститься как legacy.

## Заменяемые роли фасадов

`WorkflowRoleRegistry.register(ComponentRole(role, phase, instance_id, inputs, outputs, outcomes, handler))` закрепляет trusted handler и внешний role contract. Qualified instance берётся из snapshot; compatible project replacement используется автоматически. Проверяется точное равенство inputs/outputs/outcomes. Один parent activation допускает один компонент.

Preparation roles: context, analysis, planning, plan_review. Execution gate roles: code_review, testing, documentation, final_validation. Package/ready/knowledge_refresh не заменяются. Компоненты с writes_task_manager запрещены; task effects принадлежат фасаду.

`facade.start_component(parent_id, roles=..., executors=..., inputs=..., expected_revision=..., expected_task_version=..., fallbacks=None)` проверяет owned phase, состояние, versions, snapshot и создаёт standalone slice. Дочерний executor перед/после эффекта проверяет parent guard. Gates дополнительно проверяют claim/lease, blockers и package integrity. Caller выполняет explicit child steps, затем `submit_component(...)`: completed result/evidence передаётся handler-у, его envelope проходит обычный submit/submit_gate validator, publication и sync. Summary не обходит ready/claim/final validation/приёмку. Изменение parent revision/task version делает старый компонент stale; новая активация создаёт новый компонент. Автоматического пересвязывания child после внешней мутации нет.

Inner wait остаётся в child runtime и автоматически не меняет Task Manager status/decisions. Для публичного ожидания используйте штатный facade action. Live viewer child state, durable recovery и automatic input mapping между отдельными facade roles не реализованы; inputs start_component предоставляет caller. Передача внутри одного workflow и composite exit aliases реализована executor-ом.

`testing_gate_handler(repository)` связывает учебный core/testing@1 с полным gate: totals берутся из immutable tool execution_record, пустые проверки/противоречивый summary отклоняются. `documentation_gate_handler(repository, source_adjacent_changed=...)` требует явный bool от caller, проверяет impact/no_change и формирует source/candidate-bound evidence. Эти handlers не добавляют все статусы полного Testing/Documentation контракта в учебную библиотеку. Final validation/AC coverage и решение пользователя остаются явными.

[Guide](../guides/workflow-execution.md), [дизайн](../plans/2026-09-18-workflow-execution-design.md).
