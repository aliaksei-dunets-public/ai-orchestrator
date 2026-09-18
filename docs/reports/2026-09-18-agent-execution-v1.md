# TASK-0016 — агентский preflight и work units

**Статус:** реализован AgentExecution v1; TASK-0016 принята пользователем и completed v19, без active run/claim. Общая TASK-0027 preparing v13, миграция не завершена. Принятая TASK-0030 completed v18.

## Что сделано

AgentExecution реализует утверждённую границу agent/deterministic: агент выбирает unit и меняет код, facade проверяет результат и сохраняет его. Нет executor callback, reasoning controller, LLM или нового SQLite. [Действующий контракт](../architecture/agent-execution.md), [исполняемый guide](../guides/agent-execution.md), [план и self-review](../plans/2026-09-18-agent-execution-plan-review.md).

До реализации TASK-0016 уточнена до definition v2 через публичный API, прошла plan/review/package/ready, получила собственный claim и active implementation run (v10). Этот implementation lifecycle не выдаётся за запуск ещё не построенного facade. Старый original_request сохранён как история. Рабочий opaque source ref этого bootstrap не является совместимым AgentExecution package; новые пользовательские задачи требуют fingerprint preparation.

| Код | Реализовано |
| --- | --- |
| execution_preflight.py | Read-only ready guards, bounded immutable package/plan/review verification, plan projection, definition/criteria binding, work-unit DAG/scopes, source fingerprint до claim |
| agent_execution.py | Explicit start/request/submit, выбранные units/dependencies, actual code delta, immutable implementation evidence, public claim/lease/run links, waits/new claims, handoff/cancel |
| task_effects.py | Общий pending/unknown protocol, cursor, conservative public-history reconciliation без повторного task effect |
| agent_preparation.py | Повторное использование общего effect protocol, контракт и 23 regression tests сохранены |
| __init__.py | Экспорт AgentExecution, ExecutionPreflight, ExecutionError |
| test_agent_execution.py | 33 предметных теста guards, lifecycle, deltas и faults |

Task Manager code/schema/API/resources/guards, Onboarding и obsolete не изменялись этим этапом. SQLite напрямую не читалась/не менялась. Пользовательские исходные документы сохранены. Новый design/code commit и PR не создавались; unrelated dirty changes сохранены.

## Что обнаружено и исправлено

1. Guard старого checkpoint до разбора success блокировал собственные физические изменения агента. Submit теперь отдельно проверяет CAS/task/package/lease, затем точную before/after delta; request и clean pause по-прежнему требуют прежний checkpoint.
2. Lost response после claim нельзя повторять как новый claim. Только single-successor public event подтверждает adoption; worker/package и claim identity проверяются.
3. Lost response после handoff уже снимает active_run_ref. Recovery допускает только доказанный собственный finished-link effect без повторной записи, не ослабляя обычные work guards.
4. Pending publication после принятого результата нельзя выполнять повторно как unit. Cursor продолжает только effects. Явная cancel может abandon известный pending; неизвестный эффект сначала требует сверки.
5. Cleanup после partial edits/expired lease не требует успешного source/lease preflight и не откатывает файлы. Чужие claim/run запрещены; active release в preparing инвалидирует package публичным API.
6. Success envelope строгий; failed validation/unresolved, scope escape, запрещённые obsolete/runtime scopes, opaque revisions, projection/hash tampering и duplicate/dependency-blocked units отвергаются.

Self-review не независимый аудит. Evidence/check labels остаются утверждениями агента; валидатор не доказывает смысловой успех, исполнение тестов или внешнее разрешение. Claims обеспечивают task ownership, не файловую изоляцию.

## Проверки

Полный повторный набор с `ORCHESTRATOR_GRAPHIFY_PYTHON=.tmp/graphify-0.9.63-venv/Scripts/python.exe`:

| Набор | Всего | Passed | Skipped |
| --- | ---: | ---: | ---: |
| Root | 149 | 148 | 1 |
| Onboarding | 19 | 18 | 1 |
| Task Manager | 73 | 73 | 0 |
| Всего | 241 | 239 | 2 |

Failures/errors = 0. Skips — прежние Windows file-symlink ограничения; реальный Graphify integration выполнен, не skipped. Новые execution tests — 33; preparation regression — 23, legacy preparation — 18. Исполнен Python-блок нового guide в отдельном временном проекте: `agent execution guide: ok`. Compileall успешен. Diff check успешен, возможны прежние LF/CRLF warnings. Это не внешний production Agent E2E, не cross-platform подтверждение и не независимый audit.

Fault injection покрывает repository publication; task mutations до commit и lost response после attach/claim/release/renew/resume claim/finished link; дополнительный successor запрещает автоматическое восстановление. Lifecycle проверяет no-op, rename, actual delta, CAS, dependency/replay, waits/resume, blocker resolution, expired lease, foreign claim, partial-edit cleanup, budget и known pending abandonment.

## Обновление графа знаний

После финального кода явно выполнен full rebuild уже существующего ProjectKnowledgeService и real MCP query `AgentExecution`: indexed/fresh/ok с citation на orchestrator/agent_execution.py. Selected roots: orchestrator/tests/packages/scripts. `obsolete/` исключён политикой и отсутствует в indexed snapshot/graph. Docs/config/memory не добавлены в code graph.

- 51 selected/represented files, 613435 байт исходников; 989 raw nodes, 3324 edges.
- Coverage: 50 sourceless unresolved AST nodes, 310 external-import edges; это явно отражено index, не обещание полного семантического графа.
- Snapshot SHA-256: `64ffca2dadd244093e0d818cb5ba33e4f6d29cae7efb7b61f5b5fed743a2a4c5`.
- Version: `v673911d8ff29485ea54cf5f6da3e2fdb`; graph SHA-256 `1a60a7d4a52f131bc2c237e2a79f8e3c67f8fb2df84bd1be0e985a394c4a4569`, 1708156 байт.
- Current pointer: `.orchestrator/knowledge/current.json`; immutable graph: `.orchestrator/artifacts/project-knowledge/graph/v673911d8ff29485ea54cf5f6da3e2fdb/payload.bin` (JSON). Temporary staging/MCP directories удалены service/provider; HTML viewer этим этапом не создавался.

Это manual refresh после работы агента, не уже реализованная automatic execution gate. Изменение кода после этого snapshot вновь делает knowledge stale.

## Оценка состояния и дальнейшая миграция

| Область | Что есть | Что ещё требуется |
| --- | --- | --- |
| Task Manager | Frozen SQLite service, public guards/history/claim/acceptance | Ничего не менять в этом migration scope |
| Agent runtime/preparation | Принятые TASK-0028/0029, explicit results и ready | Host facade/instructions delivery |
| Knowledge | Принятая TASK-0030, real Graphify service | Workflow contracts и callers TASK-0019/0020 |
| Execution | TASK-0016 preflight/work units candidate | Пользовательская приёмка; full gates TASK-0017 |
| Quality/acceptance | Ручные реальные tests/docs/refresh и immutable handoff этого изменения | Агентские explicit review/tests/docs/knowledge/final-validation/readiness primitives TASK-0017 |
| Delivery | Исходный Python API, отдельные существующие пакеты | Core/Agent bundle и host-neutral adapters TASK-0021 |
| E2E | Temp guide, regression, real Graphify | Внешний clean-install/onboarding/full lifecycle TASK-0022 |
| Durable runtime/memory | Архитектурная граница | Отдельные будущие checkpoints/memory slices; не включены скрыто |

Публичным API уточнены TASK-0016–0017 и TASK-0019–0022, без удаления original_request. Финальные карточки: TASK-0017/0019/0021 created definition v2; TASK-0020/0022 created definition v4. TASK-0018 optional tracker не менялась. Приоритет: принять TASK-0016 → реализовать TASK-0017 → формализовать/подключить существующий knowledge service через TASK-0019/0020 → delivery TASK-0021 → внешний E2E TASK-0022. Не строить второй parser/graph storage, не возвращать TaskML/specification и не развивать callback controller как новое направление.

Риски до следующих этапов: in-memory sessions/cursor теряются при crash; task/physical edits/artifacts не единая транзакция; TOCTOU между snapshot/действием; docs/config/dependency freshness отсутствует; source fingerprint не semantic review; handoff сохраняет claim и требует управления lease следующими gates; Graphify provider — доверенный subprocess без OS sandbox; validation/evidence labels не независимая attestation. При изменённом baseline нужен reprepare, при partial edits — завершение проверяемого unit либо cleanup/reprepare, при unknown effect — точная public-history сверка, не слепой replay.

## Кандидат на приёмку

`agent-execution-v1:625b6d2c66ef06541fe732d247ea14f3370e23ed16ad9bdeb5447989ccbdf3d0`

Это SHA-256 canonical JSON ordered manifest шести кодовых/тестовых файлов: __init__, agent_preparation, task_effects, execution_preflight, agent_execution и test_agent_execution. Это не Git commit, не весь dirty worktree и не docs fingerprint. Полные file hashes и результаты сохраняются в immutable acceptance package. Package/readiness относится только к TASK-0016 definition v2; приёмка пользователя зарегистрирована атомарно, общая миграция остаётся открытой.

Фактическая регистрация проверена: TASK-0016 awaiting_acceptance v18, затем пользовательский `accept_task` завершил её в completed v19; TASK-0027 preparing v13, health_check=[]. Зарегистрирован immutable `TASK-0016:acceptance_package:v2`, SHA-256 `b8106137e0f3dec8ff4ccc783003679e36898c3b472cdb98606a0d450b0cd13b`, 4220 байт. Первичная публикация v1 имела неподдерживаемые labels reviews/tests: public API отверг регистрацию reviews после успешного implementation attach. Карточка/история перечитаны; продолжение использовало существующие code_review/testing, без изменения Task Manager. Unregistered immutable v1 сохранена, не перезаписана. Run link закрыт, awaiting_acceptance снял claim; приёмка зарегистрирована ровно по текущей candidate revision.

Финальная read-only сверка подтверждает все candidate file hashes, repository records, свежесть knowledge и последние события attach v16 → finished run v17 → awaiting_acceptance v18. Проверен 461 local Markdown target (line suffix учтён), missing=0; anchors отдельно не проверялись.
