# TASK-0030 — Project Knowledge Service v1

**Статус:** TASK-0030 принята пользователем и completed v18, без active run/claim; [основание](#user-acceptance). Это исторический отчёт о реализованном code-only срезе и его не следует читать как полный документный Graphify pipeline. Историческая регистрация кандидата ниже сохраняет состояние awaiting_acceptance v17 до приёмки. Общая TASK-0027 открыта; следующий этап — [TASK-0016](2026-09-18-agent-execution-v1.md). Для актуального host-agent документационного решения см. [TASK-0031 PoC](2026-09-18-single-project-knowledge-graph-v1.md).

## Результат этапа

Реализован локальный ProjectKnowledgeService с выбранным Graphify-Labs/graphify. Это уже не только compatibility probe: реальный adapter строит граф из разрешённого корпуса, проверяет extraction, публикует immutable graph/index, определяет freshness по исходникам и получает bounded context через MCP. Task Manager, его схема/API/resources/guards и Onboarding не изменены. Исходные пользовательские документы и obsolete сохранены.

Работа начата по подтверждённому migration design: TASK-0030 прошла plan, фактический [self-review плана](../plans/2026-09-18-knowledge-service-plan-review.md), Execution Package, ready, claim и active run до кодовых изменений. Brainstorming использован для проверки границ уже одобренного поэтапного дизайна. Для lifecycle использован проектный Task Manager skill и публичный API; прямого SQL нет.

## Изменения в коде

| Область | Изменение |
| --- | --- |
| knowledge_contracts.py | ProviderIdentity/Capabilities, CorpusPolicy, SourceSnapshot, GraphStatus, query/refresh results и KnowledgeError |
| knowledge_snapshot.py | Bounded выбранный корпус, exclusion policy, project-relative paths, SHA-256 fingerprint, reparse guards и повторная проверка bytes |
| knowledge_process.py | shell=false, environment whitelist, combined output budget, bounded stdio MCP, session deadline и ограниченная запись requests |
| graphify_provider.py | Pin graphifyy 0.9.63, real code-only CLI extraction, query_graph-only MCP, isolated graph.json без memory sidecars |
| knowledge_service.py | Explicit snapshot/status/refresh/query, writer lock, extraction validation, immutable versions и atomic current pointer |
| artifact_repository.py | Backward-compatible optional max_bytes для get/verify, bounded manifest и regular-file guards; старые вызовы сохранены |
| __init__.py / .gitignore | Экспорты нового API; локальное knowledge state не попадает в Git |
| Tests | 21 knowledge test, включая настоящий Graphify integration; дополнительная bounded repository regression |

Нет собственного code parser, graph database, LLM client или semantic orchestrator. Структуру извлекает Graphify; сервис проверяет contract, paths, hashes и freshness, не качество смысловых решений.

## Нюансы, выявленные реальной интеграцией

1. Graphify MCP отвергает путь без .json. Repository payload.bin нельзя передать напрямую. Adapter создаёт ограниченную временную graph.json, удаляет её после query и не подмешивает sidecars.
2. Некоторые upstream ошибки возвращаются обычным text content без isError. Распознаются Error executing/ Error:/Unknown tool:, чтобы failed query не выглядел успешным.
3. Raw graph содержит AST placeholders внешних типов без source_file, а внешние imports могут иметь target без отдельного node. Они учитываются явно и не получают выдуманные citations. Все чужие непустые paths и другие dangling edges остаются ошибкой.
4. У upstream manifest ast_hash — MD5 исходных bytes. Проверяем его для совместимости; security/freshness snapshot использует SHA-256.
5. Blank files не всегда представлены в AST manifest/graph. Они входят в fingerprint, но coverage явно допускает пустое AST-покрытие. Для непустых файлов отсутствие manifest/node блокирует публикацию.
6. Размер по manifest нельзя проверить лишь после read_bytes. Добавлены реальные bounded reads repository, чтобы повреждённый index/graph не приводил к неограниченной загрузке.

## Реальный initial load текущего проекта

Interpreter provider: `.tmp/graphify-0.9.63-venv/Scripts/python.exe`, graphifyy 0.9.63, Python 3.12. Основная .venv использует public root API, Graphify запускается отдельным subprocess. Новых установок, global hooks/config, semantic passes и моделей этим этапом не выполнялось.

Разрешённые roots: orchestrator, tests, packages, scripts. Выбрано и представлено **47 файлов, 554651 bytes**, raw graph **882 nodes / 2889 edges**. Coverage: blank_files=[], unresolved_nodes=46, external_import_edges=286. MCP при загрузке создаёт дополнительные external target nodes: его 923 nodes не равны raw node count и не доказывают дополнительное покрытие исходников.

Snapshot: `693863469969c57b1415ecd125961015f1e7631a0f0dc676809effceb2e47a42`.

Policy digest: `66214e0e515e8caac85af41774a5d58e5449d7e9ff35e1b76e657e310eaf3a2b`.

Первый успешно опубликованный graph: `project-knowledge:graph:v38a0fccaa7fb491e8c75b9d915609da5`, 1505397 bytes, SHA-256 `750fb570905913c4c1fbaf9cccb2b76118c22fe2561574772b41269095e97645`. Исполнение guide создало ещё одну immutable version того же корпуса; current выбирает последнюю успешную, предыдущая сохранена. Version не является content hash.

Query AgentPreparation вернул ok/fresh, настоящий context и citations на agent_preparation.py, agent_runtime.py, preparation_primitives.py и другие indexed files. Проверен hard content budget и явное upstream truncation. Guide исполнен с assertions после initial load. Final status — fresh по выбранному корпусу; документация не индексируется и не меняет этот code fingerprint.

## Проверки

После final review добавлен strict integer MCP response ID guard (bool не принимается как 1) и regular-file guard current pointer. Финальный refresh: 47 files / 554999 bytes, 882 raw nodes / 2890 edges, external_import_edges=287, unresolved_nodes=46. Финальный snapshot `c877a4f393dda95fb4a7e0cf4752a160f6dabda9812231dd4364b72322fd6b84`; current graph `v878a560086174a3caa6d853f517a13b8`, SHA-256 `c9d06a5754a1bbda9d7253b9774c062bea9ee16dc2641899f29e402a646aa66f`, 1505719 bytes. Final query ok/fresh, 35 indexed-path citations; предыдущие versions сохранены. Числа initial load выше относятся к первому успешному snapshot, не подменяют финальную проверку.

| Проверка | Результат |
| --- | --- |
| Root suite с ORCHESTRATOR_GRAPHIFY_PYTHON | 116 tests, 115 passed, 1 Windows file-symlink skip, 9.663 s |
| Knowledge suite в составе root | 21 tests; real Graphify test включён, не skipped |
| Onboarding | 19 tests, 18 passed, 1 Windows skip, 0.594 s |
| Task Manager | 73/73, 17.927 s |
| Всего unittest | 208 tests, 206 passed, 2 skipped, 0 failures |
| Реальный provider | Python/TSX/Vue, Unicode, rename/delete, restart MCP, initial load проекта и query |
| Fault injection | partial/foreign extraction, wrong hashes/endpoints, source drift, pointer failure, timeout/output overflow, malformed MCP, wrong ID, stale lock, corrupted graph/pointer |
| Guide | Python example исполнен; refresh/query assertions успешны |

Без provider env реальный integration test намеренно skipped. Два итоговых skips выше — ограничения Windows file-symlink privileges, не замена Graphify теста mocks. Это Windows проверка, не независимый аудит и не полный внешний Agent E2E.

Финальный повтор root suite после всех source guards: 116 tests, 115 passed/1 skipped, 13.855 s, failures=0. Compileall успешен; diff check — только LF/CRLF предупреждения. Проверены 430 local Markdown targets, missing=0; suffix :line учтён, anchors/remote URLs отдельно не проверялись.

## Ревизия кандидата

`project-knowledge-v1:d184e24f9040b89fd54529867c80b79878337d0e1a14aef90afa4b003690b13b`

SHA-256 UTF-8 записей relative/path:lowercase_sha256 + newline в порядке таблицы. Это конкретный code/test slice в dirty worktree, не Git commit всей миграции. Исторические candidate hashes предыдущих срезов не переписываются при добавлении новых exports.

| Файл | SHA-256 |
| --- | --- |
| .gitignore | a1edae9dfac63fc4afeaec382ea4aaeb172953575aaacc071014868924f12639 |
| orchestrator/__init__.py | 2643596f46771177ac447e36961f02c51c6c681e02cc5e1d07213fe6681ea017 |
| orchestrator/artifact_repository.py | a741011c6bcd01120cbf7dc5b86bd2511daad9985924d887d1d29ed80e5b26b6 |
| orchestrator/graphify_provider.py | 511d837cce87c0b5f73f22310ffb033ffff88ae8b2264d0379174e62be1100e1 |
| orchestrator/knowledge_contracts.py | 559a81ac98ce07b0bd509d4082ff8f385634c303e633b62e01d7b051ec9f85f5 |
| orchestrator/knowledge_process.py | 185d21089ecfe0131e2f3d51df0c22166943ef657da6bbb263987bacc84985ed |
| orchestrator/knowledge_service.py | 8b03e2f330ae03ae1a001154054a5013ac1d58f6b7b22a38ded323a0f4049353 |
| orchestrator/knowledge_snapshot.py | 7b87e2f372b88a6c081ca8ac3e27277ac62f11d38b4a867bbc5f3b0b11eba092 |
| tests/test_artifact_repository.py | 14e9c08c06a3f335d2257d590cccb2d97660e90cb9a4222140e23669e0d7e8b1 |
| tests/test_knowledge_service.py | d274799a2814082a17ac309604ad03bdfa5e912de60ca6d4928fa5628f45698a |

## Общая архитектурная оценка после этого этапа

Публичным API зарегистрированы implementation/testing/code_review/documentation/readiness и immutable `TASK-0030:acceptance_package:v1`, SHA-256 `afd01095925dc241937d3cfc27c6c3fbd00abcf7f7c33c72694edc95d126ab40`, 9378 bytes. Package содержит candidate file manifest, provider, indexed snapshot, graph metadata/coverage, tests и ограничения. Active run закрыт, mark_awaiting_acceptance очистил claim. Parent documentation обновлена, TASK-0027 preparing v12. После регистрации health_check=[], knowledge status=fresh. Подтверждение TASK-0029 не использовано как приёмка TASK-0030.

| Подсистема | Есть | Не хватает |
| --- | --- | --- |
| Task lifecycle | SQLite Task Manager, canonical definition, ready/claim/acceptance guards | Новая схема не нужна; пакет сохраняется неизменным |
| Agent process | AgentGraphRuntime, explicit results/actions, revision/definition/wait guards, bounded cycles | Durable checkpoints, host permissions, external process facade |
| Preparation | AgentPreparation до ready, immutable artifacts, projection, pending/history reconciliation | Installed agent instructions, автоматическое подключение context service |
| Code knowledge | Реальный ProjectKnowledgeService/Graphify adapter, selected snapshot, immutable refresh, MCP query/provenance | Onboarding profile, service MCP facade, execution final-validation integration |
| Execution | Отдельные public claim/Task Manager transitions | Agent execution graph, preflight/source/package guards, work units, review/tests/docs/refresh/final validation |
| Delivery | Onboarding и Task Manager packages | Core/Agent bundle, portable installation/update protocol, внешний task lifecycle E2E |
| Memory | Архитектурно отделена | Отдельный memory service; не блокирует code-only v1 |

Новый подход уменьшает дублирование reasoning в Python: смысловой выбор принадлежит агенту, код проверяет процесс и artifacts. Но это перенос ответственности, не автоматическая гарантия качества агента. Current implementation доказывает отдельные primitives и локальный service; сквозная управляемая поставка ещё отсутствует.

## Ограничения и остаточные риски

- Граф advisory. Отсутствие связи не доказывает отсутствие зависимости; fresh — только code corpus identity. Docs, runtime/dependency changes, dynamic calls и semantic correctness не охвачены.
- Citations подтверждены только по indexed paths, не по строкам/current source/relevance. Textual confidence tags не являются независимой аттестацией.
- Secret-name exclusion — эвристика. Нет OS network sandbox, package-wheel attestation или защиты от вредоносного trusted Python caller. Environment filtering и query-only allowlist снижают поверхность, но не заменяют host permissions.
- Writer lock не имеет recovery lease; после crash возможны stale lock и orphan immutable versions. Нет автоматического GC, incremental refresh или общей транзакции с tasks/runtime. Durable current pointer не восстанавливает потерянный Agent workflow.
- Непустой source, который upstream не представляет, блокирует refresh вместо ложного success. Поддержка произвольных языков, Unicode-normalization variants и всех framework patterns не обещается.
- Самостоятельный review проверил contract/paths/freshness/publication и negative cases; независимый reviewer не запускался. Ранее независимый аудит Artifact Repository не является аудитом новых bounded-read изменений.
- Реализация остаётся в рабочем дереве. Нового code commit/PR не создано; unrelated user edits сохранены. Единственный ранее созданный design commit f881dda — отдельный артефакт.

## План дальнейшей миграции

<a id="user-acceptance"></a>
Пользовательская приёмка TASK-0030: «принято. продолжай дальше миграцию. не забывай обновлять задачи». Принимается показанный Knowledge Service slice, включая подтверждённое исключение obsolete; это не приёмка будущего execution или всей TASK-0027. Перед accept публичным API повторно сверяются immutable acceptance package и code manifest.

1. Принять этот проверяемый knowledge slice отдельно от общей миграции. После приёмки обновить task status публичным API, не считать подтверждение прежнего этапа приёмкой нового.
2. По roadmap перейти к agent execution: уточнить TASK-0016–0017, спроектировать minimal explicit execution process с preflight/current task-definition/package/source guards и existing claim. Не возвращать controller reasoning callbacks.
3. В execution добавить проверяемые work-unit/review/tests/documentation results, explicit knowledge refresh и final validation. Свежесть code graph должна проверяться для конкретного final candidate, а не по старому task plan hash.
4. Уточнить TASK-0019–0020 под service/provider integration, а TASK-0021–0022 под portable Agent/core delivery и внешний E2E. Эти старые карточки этим этапом не переопределены автоматически и не закрыты по наличию нового кода.
5. После доставки и compatibility E2E мигрировать внешних callers с legacy callbacks. Не переносить активный callback run посередине выполнения; закрыть его явно и начать новый agent path с актуальными guards.
6. Durable journal/checkpoints и memory — отдельные последующие срезы; не помещать process state в Task Manager SQLite и не обещать recovery по одному active_run_ref.

Действующие материалы: [контракт знаний](../architecture/project-knowledge-service.md), [guide](../guides/project-knowledge.md), [актуальный снимок](../project-status.md), [roadmap](../roadmap.md). Исходная [оценка](2026-09-17-agent-centric-graphify-assessment.md) остаётся baseline до реализации, не переписывается задним числом.
