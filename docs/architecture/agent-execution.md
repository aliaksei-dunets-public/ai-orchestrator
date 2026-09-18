# Агентское исполнение: preflight и work units

**Статус:** реализованный Python-контракт TASK-0016, 2026-09-18; отдельная приёмка кандидата требуется. [Guide](../guides/agent-execution.md), [отчёт](../reports/2026-09-18-agent-execution-v1.md). Full review/test/documentation/knowledge/final-validation gates относятся к TASK-0017.

## Граница ответственности

Агент выбирает доступный work unit, изменяет файлы и выполняет проверки. `AgentExecution` не содержит executor callbacks, LLM, scheduler или решений о качестве реализации. `AgentGraphRuntime` принимает результат с process CAS/history; неизменяемый Task Manager хранит task versions, claim/lease, blockers и ссылки на runs. Runtime, sessions и effect cursor существуют только в памяти.

`ExecutionPreflight.check(task_id, expected_task_version=...)` не изменяет карточку и не делает claim. Он требует ready без run/claim/open blocking blockers, проверяет bounded immutable Plan/Review/Execution Package и SHA-256, соответствие plan projection, task/definition/criterion coverage и approved binding. Структурированный Plan должен содержать 1–100 work units с уникальными IDs, безопасными project-relative scopes и ациклическими dependencies. `obsolete/`, hidden/runtime paths, `.` и parent traversal недопустимы.

Baseline — `code-corpus/v1:<snapshot SHA-256>` с политикой и байтами выбранного code corpus, включая dirty/untracked/rename/delete. До подготовки получите `ExecutionPreflight(root).source_revision()`. Старые непрозрачные revisions и произвольные Markdown планы не мигрируют автоматически: требуется повторная подготовка через AgentPreparation. Config/docs/dependencies и смысловая актуальность этим fingerprint **не покрыты**. Между snapshot и физическим действием остаётся TOCTOU; файлового lock/sandbox нет.

## Явный API

- `start(..., expected_task_version, worker_ref, lease_seconds=900)` выполняет preflight, сохраняет immutable evidence, вызывает публичный claim и link active run. Lease 30–86400 секунд. Ошибка после создания session содержит `details.run_id` для дальнейшей сверки.
- `inspect`, `request`, `available_actions` возвращают копии process/task snapshots, доступные units, bindings, checkpoint и pending/unknown state. Возможные actions — подсказка; guards повторяются при мутации.
- `submit(run_id, envelope, expected_revision, expected_task_version)` принимает ровно один явный результат. Доступны `success`, `needs_input`, `blocked`, `failure`, `handoff`.
- `AgentExecution(..., knowledge_service=ProjectKnowledgeService(...))` может получить тот же Project Knowledge Service, который использует агент. `precommit_gate(run_id, expected_revision, expected_task_version, request=..., decision=...)` разрешён после всех work units и делегирует reusable `KnowledgeRefreshNode`. Совместимый default request выполняет strict incremental gate; `full` с `authorization=required` возвращает wait, а trusted `automatic` может выполнить full. Результат `knowledge-precommit-gate/v1` содержит `success`/`not_required`/`degraded` с `commit_allowed=true` только при fresh graph либо `stale`/`failed`/`fallback_required`/`awaiting_confirmation` с запретом commit. Метод не выполняет Git commit и не изменяет Task Manager.
- `renew_claim(..., expected_revision, expected_task_version, lease_seconds)` продлевает только действующий собственный claim; task version меняется, process revision нет.
- `resume_wait(..., wait_id, node_id, answer/resolution, expected_revision, expected_task_version)` отдельно возобновляет собственную pause; ответ `null` допустим и сохраняется.
- `cancel(..., reason, expected_revision, expected_task_version)` закрывает только собственные run/claim, допускает истёкший lease и partial edits. Active task возвращается в preparing с инвалидированием preparation bindings. Файлы не откатываются.

Success envelope: только `outcome` и `payload`. Payload содержит ровно `unit_id`, `summary`, `source_before`, `source_after`, `changed_files`, `evidence_refs`, `validation`, `unresolved`. Validation содержит `status="passed"`, непустой `checks_run` и пустой `failed`; `unresolved=[]`. Changed files должны точно совпадать с наблюдаемой code delta и входить в scope выбранного доступного unit. Add/delete/rename учитываются. No-op допустим с пустой delta и фактически выполненными проверками. Evidence/check labels являются заявлениями агента, не независимым доказательством тестов или разрешения пользователя.

Success сохраняет immutable `implementation` версии, checkpoint/completed IDs и ссылку через публичный attach. Агент может выбрать любой доступный unit: нет автоматического dispatch. Replay/completed unit, незавершённая dependency, чужой claim, истёкший lease, изменённые package/definition/version или неверная delta отклоняются.

## Паузы, эффекты и передача

Stop envelopes содержат только outcome и непустой question либо reason. Для pause/stop требуется неизменённый checkpoint: частичные кодовые изменения нельзя объявить clean pause. Сначала явно cancel/reprepare либо завершите проверяемый unit. `needs_input` переводит задачу в awaiting_input; `blocked` и `failure` создают собственный blocker. Затем закрывается run link и освобождается claim. Failure terminal; pause сохраняет WaitState в памяти. Resume фиксирует clarification либо resolve blocker, переводит в ready, получает **новый claim** и вновь связывает тот же process run. Source/package guards остаются обязательными.

После всех units агент должен вызвать `precommit_gate`, если изменение требует code commit, и передать физический commit только при `commit_allowed=true`. Затем `handoff` завершает process и закрывает run link, но **сохраняет active task и действующий claim** для TASK-0017 gates. Это не awaiting_acceptance/completed. До поставки gates caller обязан управлять lease/следующим run публичным API либо явно освободить claim. Facade после terminal handoff не продлевает его сама.

Runtime acceptance и repository/Task Manager не образуют общую транзакцию. Принятый результат с незавершёнными effects имеет pending barrier. `synchronize` продолжает с cursor, не выполняя unit повторно. Known pending можно явно abandon через cancel; terminal handoff с pending требует reconciliation/sync. Неопределённый outcome task mutation блокирует повтор: `reconcile_effect(expected_task_version, applied)` принимает только неизменённую карточку (false) либо точный single-successor public history event и bindings (true), затем sync делает adoption без повторной записи. Дополнительное внешнее событие не «угадывается». Обычный `reconcile(expected_version)` допускает только совместимое состояние того же task/package/claim.

Общий `TaskEffectSync` используется также AgentPreparation; callback PreparationWorkflow удалён в TASK-0034; общие детерминированные primitives сохранены. Restart recovery, persisted cursor, durable checkpoints, межагентская координация, automatic knowledge refresh, installed host skill/MCP facade и network/filesystem sandbox не реализованы.
