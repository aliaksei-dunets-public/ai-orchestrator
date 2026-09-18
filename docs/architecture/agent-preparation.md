# Агентная подготовка задачи до ready

**Статус:** реализованный Python in-process контракт TASK-0029, 2026-09-18. Принят пользователем, TASK-0029 completed v18; [основание](../reports/2026-09-18-agent-preparation-v1.md#user-acceptance). Не MCP, не полный Executor Loop и не межсессионное recovery.

## Ответственность

`AgentPreparation(project_root, *, max_review_cycles=2, max_context_expansions=2, max_results=100)` создаёт Task Manager Service и Artifact Repository для одного проверенного root и собственный AgentGraphRuntime. Внешний агент выполняет осмотр, анализ, планирование и review и подаёт готовые envelopes. Нет adapters, step, executor или скрытого вызова LLM. Project profile — пользовательский JSON-контекст, не инструкции ядру.

Общие validators, publication, projection и sync находятся в [preparation_primitives.py](../../orchestrator/preparation_primitives.py). Callback PreparationWorkflow удалён в TASK-0034; primitives остаются общими для агентских facade. Общие модели процесса находятся в [runtime_contracts.py](../../orchestrator/runtime_contracts.py). Эквивалентность предметных контрактов не означает независимого semantic review.

В TASK-0016 pending/unknown task-effect protocol вынесен в общий [TaskEffectSync](../../orchestrator/task_effects.py) для AgentPreparation и [AgentExecution](agent-execution.md). Публичные preparation контракты не изменены; Предметные preparation regressions сохранены и расширены при удалении callback-пути.

Карточка SQLite Task Manager остаётся канонической; TaskML и отдельная specification не возвращаются. Код, схема, resources и API пакета Task Manager не менялись. Подготовка не делает claim и не начинает исполнение.

## Интерфейс

| Action | Обязательные аргументы и результат |
| --- | --- |
| `start(task_id, *, expected_task_version, prepared_source_revision, project_profile=None)` | Created/preparing без active run/claim; регистрирует реальный процесс, возвращает AgentWorkflowRun. При sync error run_id есть в details |
| `inspect(run_id)` | Run, актуальная task, artifacts, sync_pending/cursor/actions, unknown_effect |
| `available_actions(run_id)` | Допустимые facade actions, process revision, pinned definition и cached task_version; hints не заменяют guards |
| `request(run_id)` | Input contract, actions, актуальная task, profile, previous accepted results, resumed_wait, artifact records |
| `submit(run_id, envelope, *, expected_revision, expected_task_version)` | Принимает проверенный result, ставит effects, синхронизирует; возвращает run после принятия |
| `resume_wait(run_id, *, expected_revision, expected_task_version, wait_id, node_id, answer=…, resolution=None)` | Отдельный action без выполнения узла; user_input требует явный JSON answer, включая null; blocker — только непустой resolution |
| `cancel(run_id, *, expected_revision, expected_task_version, reason)` | Отменяет процесс и закрывает только собственную active link; не отменяет задачу/блокер и не откатывает artifacts |
| `synchronize(run_id)` | Продолжает незавершённые deterministic effects с сохранённого cursor; unknown task mutation запрещает retry |
| `reconcile(run_id, *, expected_version)` | Явная сверка после внешней мутации; не допускает definition drift, чужой run/claim и изменения preparation artifact bindings |
| `reconcile_effect(run_id, *, expected_task_version, applied)` | Явная сверка неизвестного результата task mutation; условия ниже |

Перед каждым action агент читает inspect/request и передаёт реальные версии. Общий lock сериализует facade actions в процессе. Он не защищает от других процессов или прямого вызова публичных `flow.runtime`/`flow.service`; host должен предоставлять бизнес-путь через facade. Фиксированный root изолирует проект, но не является OS sandbox.

## Workflow и envelopes

Graph: `agent-development-preparation-v1`, version 1. Context → Analysis → Planning → Plan Review → Package → Ready → succeeded. Analysis `needs_context` возвращает в Context; Review `changes_required` — в Planning. Target нельзя передать произвольно. На любом узле доступны needs_input/blocked/failure.

Envelope: `outcome`, `payload` для содержательного результата; `question` для needs_input; `reason` для blocked/failure. Неизвестные поля и не-JSON значения запрещены. Wait identity генерируется ядром. Artifact ref/version/hash также формирует primitive, агент не может подставить готовый чужой artifact вместо payload.

- Context success: непустой `summary`, список `evidence_refs`.
- Analysis success: `objective_interpretation`, списки `constraints`, `invariants`, `unknowns`. Needs_context: непустой список `requests`.
- Planning success: `goal`, `scope.in/out`, `global_constraints`, `global_validation`, непустые work_units с уникальными id, goal, files_objects, expected_result, validation, depends_on. DAG и сохранение task/analysis constraints/invariants проверяются программно.
- Review approved: findings, полный набор criterion_ids карточки, zero_context_executable=true, approved_binding с точными plan_sha256 и definition_version. Открытые major/critical запрещены; их findings требуют evidence_refs. Changes_required требует конкретных findings.
- Package/Ready success: только `{"outcome":"success"}`. Package создаётся из проверенных реальных Plan/Review и prepared_source_revision; Ready проверяет immutable Plan/Review/Package и актуальную plan projection. Проверки artifacts повторяются перед Task Manager mark_ready во время sync.

Перечисленные условия структурные. Они не доказывают истинность evidence, качество анализа, реальную исполнимость work units или актуальность произвольной строки source revision: это обязанность агента и будущего preflight. Репозиторий фиксирует байты, не их смысл.

## Effects и готовность

Принятый result → pending effects → completed effects. Сначала immutable publication, затем проекция Plan/регистрация Review/Package и guards Task Manager. Plan projection не перезаписывает посторонний или изменённый файл; замена прежней управляемой версии требует хеша и immutable основы. Готовность закрывает preparation link, затем вызывает mark_ready без claim.

Next submit/resume/cancel запрещён до окончания pending. Поэтому `run.state=succeeded` с `sync_pending=true` ещё не означает `task.status=ready`: result финального gate принят, внешний guard мог отказать. Task Manager и pending flag обязательно входят в проверку результата. Нет общей транзакции или обещания exactly-once.

Определённые repository/projection errors оставляют cursor для исправления причины и synchronize. Версионный конфликт требует inspect и explicit reconcile, не слепого чтения новой версии. Неожиданное исключение task mutation или TaskError repository_failure консервативно дают effect_outcome_unknown; synchronize заблокирован.

`reconcile_effect(applied=false)` требует точный неизменный task snapshot до операции. `applied=true` допускает только единственное successor event в публичной истории, version+1, совпадение типа/полного payload и definition; для attachment дополнительно проверяется полный binding, для созданного blocker — его полный snapshot. Затем текущий closure завершается без повторной task mutation; остальные effects выполняются обычным образом. Дополнительные события или несовпадающая evidence не восстанавливаются автоматически. Проверка версии повторяется после сверки, перед continuation.

Это ограниченный in-memory recovery обычных ошибок, не durable journal. При сложной неоднозначности, definition drift во время pending или потере процесса нужен ручной аудит Task Manager history/files и закрытие реально принадлежащей preparation link через публичный API; нельзя выдавать новый результат за continuation потерянного run. Автоматическое снятие чужих блокеров и обход guards отсутствуют.

## Waits и limits

Wait приостанавливает процесс, переводит задачу в awaiting_input/blocked и закрывает active link. Resume сохраняет реальный clarification/разрешает собственный blocker, возвращает preparing и открывает ссылку; узел не выполняется. Ответ хранится в resumed_wait до следующего принятого submit; отвергнутый result его не теряет.

Context expansions и review cycles ограничены правилами подготовки: превышение превращает результат в owned blocker; последний review payload сохраняется. Max_results ограничивает общее число принятых results, включая waits/failure. Resume/cancel не списывают result budget. Повтор resume не сбрасывает исчерпанные смысловые бюджеты; новый цикл требует диагностики и новой подготовки, а не бесконечного retry.

## Пределы

Нет автоматической интеграции с отдельным [Knowledge Service/Graphify](project-knowledge-service.md), knowledge freshness gate, memory, installed Agent skill, MCP process transport, checkpoint/restart recovery, source verification, permissions enforcement, execution claim/preflight и независимого code review. [Guide](../guides/agent-preparation.md), [отчёт](../reports/2026-09-18-agent-preparation-v1.md).
