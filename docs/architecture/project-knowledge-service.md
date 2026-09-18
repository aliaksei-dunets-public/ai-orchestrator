# Project Knowledge Service и Graphify

**Статус:** действующий контракт реализованного Python-среза TASK-0030 от 2026-09-18; принят пользователем, completed v18. [Guide](../guides/project-knowledge.md), [проверки, приёмка и ограничения](../reports/2026-09-18-project-knowledge-service-v1.md). Это отдельный advisory service, не автоматическая integration в AgentPreparation или execution workflow.

## Ответственность и backend

Orchestrator Agent выбирает, когда получить контекст и когда обновить знания. `ProjectKnowledgeService` вычисляет snapshot, проверяет freshness, публикует проверенную версию и возвращает bounded query result. `GraphifyProvider` запускает закреплённый indexer и read-only MCP query. Task Manager, process state и semantic decisions сервису не принадлежат.

Backend — Graphify-Labs/graphify, дистрибутив `graphifyy==0.9.63`, профиль `code-only/no-cluster`, schema identity `graphify-raw-json/0.9.63`. Совместимость проверена на установленной версии и Windows fixtures; [dependency snapshot](../../requirements/graphify-probe-windows-py312.txt) закрепляет пакеты, но не является wheel-hash attestation или cross-platform lockfile. Service не устанавливает provider, глобальные hooks или конфигурацию.

Graphify не является GraphQL. [Исходный материал](../development/01-graphify-integration-ai-orchestrator.md) описывает MCP boundary; GraphQL API не включён. Project Memory — отдельный будущий сервис оперативной памяти и не часть Project Knowledge Graph. Production service пока выполняет code-only refresh; документные semantic results проверены только в изолированном host-agent PoC и ещё не опубликованы в current index.

Контракт TASK-0031: один Project Knowledge Graph для кода и долговечных architecture/ADR, актуальных product/technical docs и постоянных guides/specifications о текущем состоянии. Отдельный documentation graph запрещён. Tasks/plans/reports, временные specifications, scratch/working artifacts, `.orchestrator/runs`, архивы и устаревшая документация исключаются; критерий включения — источник правды через несколько месяцев. Host-agent PoC это направление подтвердил, но production document admission и публикация ещё не реализованы.

Ограниченный [PoC TASK-0031](../reports/2026-09-18-single-project-knowledge-graph-v1.md) подтвердил вариант A: semantic extraction по установленному Graphify skill выполняет текущий host-agent без отдельного API-ключа или нового backend. Два действующих архитектурных Markdown объединены с прежним кодовым графом в изолированном кандидате и найдены через существующий MCP. Передача проверенных canonical AST IDs в host extraction дала три явные связи `references` document→code; без такой передачи первый результат не имел прямых связей. Это ссылки на упомянутые классы, не доказательство соответствия реализации контракту.

Отдельный backend требуется headless semantic CLI, а не host-agent сценарию. Вариант B — автономный semantic service — отложен в created TASK-0032 и не является условием v1. Default production pipeline пока code-only: PoC не опубликован в current pointer. Минимальный manifest compatibility fix проверяет semantic_hash для документов вместо ast_hash, не меняя CorpusPolicy или provider invocation.

### Целевые операции единого графа — ещё не реализованы

- `refresh_code_graph()` — детерминированный AST refresh кодовой части.
- `refresh_document_graph()` — семантический refresh долговечной документации через Graphify skill текущим host-agent. Service принимает и проверяет явный результат агента; не выполняет reasoning вместо него.

Это две операции над одним Project Knowledge Graph, не отдельные code/documentation graphs. Нужны раздельные code/docs snapshots и freshness, source hashes, версия skill/prompt, canonical AST bindings и expected base graph version. Публикация должна сохранять другую часть графа либо явно обозначать её stale; провал не меняет успешный current pointer. Изменения документов не должны скрываться за fresh code corpus. Нынешний `refresh()` остаётся рабочим code-only API; новые методы, composite index и admission host-result пока отсутствуют. Детали будущего среза — в [подтверждённом дизайне](../plans/2026-09-18-graphify-host-agent-design.md).

## Экспортируемые контракты

Классы доступны из `orchestrator`; dataclass сериализуются через `to_dict()`.

| Контракт | Реализованная форма |
| --- | --- |
| ProviderIdentity | upstream, package, version, extraction, schema |
| ProviderCapabilities | query=true, full_rebuild=true, incremental_refresh=true, textual_provenance=true, semantic_documents=false |
| CorpusPolicy | include_roots, version, extensions, max_files, max_file_bytes, max_total_bytes |
| SourceFile / SourceSnapshot | relative path, SHA-256, размер; digest, policy_digest, files, total_bytes |
| GraphStatus | state, current_snapshot, indexed_snapshot, graph record, provider, error |
| KnowledgeQueryResult | status, bounded content, freshness, citations, provenance, indexed_snapshot, provider, limitations, error |
| KnowledgeRefreshResult | status, snapshot, graph record, raw node_count/edge_count, error |

GraphStatus.state: missing/fresh/stale/failed. Durable refreshing нет: успешная версия доступна во время rebuild; конкурентный writer получает refresh_conflict. Query: ok/degraded. Refresh: indexed/failed. KnowledgeError содержит code/message/details. Неверные query arguments отклоняются до provider call.

## Корпус и freshness

Constructor фиксирует project root. Корпус задаётся project-relative include_roots; default `(".",)`, для реального проекта рекомендуется явный список каталогов. Политика `code-corpus/v1` разрешает .py/.js/.ts/.tsx/.jsx/.vue. Другие языки и ABAP не включены. Изменение разрешённого поднабора расширений меняет policy digest; расширение языкового профиля требует новых provider tests.

Исключаются hidden paths, .git, .venv, venv, .tmp, .orchestrator, obsolete, node_modules, __pycache__, build, dist, .agents, .codex, .idea, .vscode, graphify-out, releases и названия с secret/credential/private/token/password/api-key. Это эвристика имён, не доказательство отсутствия секретов внутри обычного исходника. Запрещённый include-root отклоняется. Obsolete не импортируется, не запускается и не изменяется.

Default limits: 5000 файлов, 2 MiB на файл, 64 MiB всего; обход ограничен числом filesystem entries. Symlink/junction/reparse alias в project root, его ancestors, выбранных источниках и repository paths отклоняется. Excluded directories не обходятся; пути не могут переключать проект.

Digest — SHA-256 canonical JSON из policy digest и отсортированных relative paths, SHA-256 и размеров файлов. Git HEAD не используется: dirty/untracked, rename и delete учитываются независимо от commit. Это fingerprint code corpus, не документации, среды исполнения, внешних зависимостей или Git-истории. `fresh` означает совпадение fingerprint, не исчерпывающие знания или отсутствие дефектов.

## Явный refresh и публикация

1. Проверить store и получить эксклюзивный `.orchestrator/knowledge/refresh.lock` без перехвата чужого lock.
2. Проверить прежний current pointer; повреждённый индекс автоматически не затирать.
3. Вычислить snapshot, скопировать только выбранные и повторно проверенные байты в isolated staging.
4. Запустить CLI extract с code-only, no-cluster, no-gitignore, force, max-workers=1. no-gitignore допустим только для staging, уже содержащего разрешённый корпус.
5. Проверить JSON nodes/edges, identities/paths, MD5 ast_hash manifest и присутствие каждого непустого source в graph. MD5 — формат upstream, не security hash; свой snapshot использует SHA-256.
6. Повторно проверить snapshot. Опубликовать immutable graph/index с новым version; ещё раз проверить snapshot перед atomic replace current pointer.

### Incremental Refresh и pre-commit gate

`refresh_incremental()` — code-only операция для pre-commit изменений. Она сравнивает текущий `SourceSnapshot` с indexed snapshot, классифицирует added/changed/deleted и одинаковые по хешу rename, переносит предыдущий Graphify `graph.json` и `manifest.json` в isolated staging и вызывает нативный `graphify update --no-cluster`. Graphify переизвлекает только затронутые code sources, пересчитывает затронутые зависимости и удаляет источники, которых больше нет. `precommit_refresh()` является сервисной операцией и сам Git не изменяет. Для agent-centric workflow `AgentExecution.precommit_gate()` задаёт момент gate после всех work units, делегирует refresh этому сервису и возвращает `success/degraded/stale/failed` с явным `commit_allowed`; физический commit остаётся действием вызывающего агента.

Результат содержит `mode=incremental`, change-set и immutable graph/index. При отсутствии изменений возвращается `not_required` без новой версии. Совместимый вызов `refresh_incremental()` по умолчанию допускает диагностируемый `full-rebuild-fallback` для старого index без manifest. `refresh_incremental(allow_full_fallback=False)` используется Workflow Graph node и возвращает `fallback_required` без запуска full; это защищает правило, что full refresh требует отдельного решения. Повреждённый provider output/source drift/provider failure сохраняют прежний current pointer и возвращают `failed`. Full `refresh()` остаётся явной операцией.

Полный Graphify rebuild не запускается для изменений только вне разрешённого code corpus (например, `docs/plans`, `docs/reports`, `.orchestrator`, `obsolete`). Документный host-agent semantic refresh TASK-0031 остаётся отдельной будущей admission-операцией и не смешивается с этим code-only gate.

Raw bytes сохраняются без собственного parser/graph engine. Upstream AST placeholders с пустыми source_file/source_location и внешние imports/imports_from на отсутствующий target допускаются только в проверенной AST-форме. Они отдельно учитываются как unresolved_nodes/external_import_edges и не дают source evidence. Другие dangling endpoints и чужие непустые paths отклоняются. Blank/whitespace-only files остаются в snapshot, но допускаются без AST nodes и перечисляются в coverage. Частичная экстракция не объявляется успешной по exit code.

Артефакты `project-knowledge:graph:<version>` и `project-knowledge:index:<version>` находятся в `.orchestrator/artifacts/`. Index связывает provider, policy, snapshot, coverage, raw counts, indexed_at, graph metadata/hash. `.orchestrator/knowledge/current.json` выбирает успешный index record. Pointer ограничен 8 KiB, index — 2 MiB, graph/manifest provider — 32 MiB каждый. Repository чтение bounded, metadata и SHA-256 проверяются.

Failed refresh сохраняет старый current graph; источники могут стать stale относительно него. Непривязанные immutable versions после ошибки publication допустимы; GC нет. Atomic replace не является общей транзакцией файлов, Task Manager и process state. При crash lock может остаться: автоматический lease/steal отсутствует; требуется остановить writers и проверить конкретный lock перед восстановлением.

## Query и MCP

`query(question, mode="bfs", depth=2, token_budget=1000, max_chars=6000, allow_stale=False)` не индексирует. Missing/failed/stale дают degraded direct discovery; stale query разрешён лишь явно и остаётся degraded. Question ≤1024 UTF-8 bytes, mode bfs/dfs, depth 1–6, token budget 1–4000, max_chars 1–12000. Token budget приблизительный; свой character limit независим и отмечает truncation.

Каждый query запускает новый stdio MCP process с точной версией graph. Upstream требует .json, поэтому bounded graph bytes передаются в isolated temporary graph.json без work-memory sidecars. Initialize проверяет protocolVersion 2025-03-26 и наличие query_graph. Adapter вызывает только query_graph: public project_path, arbitrary tools, PR и mutating commands отсутствуют. Raw provider API — внутренняя доверенная граница Python caller; host ACL/sandbox он не заменяет.

Default budgets: combined stdout/stderr 1 MiB, index timeout 90 s, version check 25 s, MCP session 25 s, request 8 KiB, очередь 32 messages и максимум 100 notifications. Команды передаются массивом, shell=false. Environment whitelist сохраняет необходимые runtime/Windows paths, убирает inherited API credentials/provider settings; query logging выключен. Это не OS network sandbox: pinned provider и host environment должны быть доверенными; завершение дерева сторонних subprocesses отдельно не гарантируется.

Textual upstream errors, isError, malformed protocol, wrong ID, overflow и timeout дают structured failure/degraded. Content — недоверенные данные, не инструкции агенту. Citations извлекаются из NODE src/loc только для indexed paths, validation=indexed-path-only; строка и relevance непосредственно в коде не проверяются. EXTRACTED/INFERRED/AMBIGUOUS — обнаруженные textual tags, не независимая confidence attestation. После query повторно проверяются source snapshot и graph; source drift снимает fresh.

## Оставшаяся миграция

Caller может передать knowledge result как evidence в AgentPreparation. `AgentExecution` поддерживает явный pre-commit gate при инъекции того же `ProjectKnowledgeService`; `KnowledgeRefreshNode` реализует reusable policy-controlled node с режимами `auto`/`incremental`/`full`, `authorization=required|automatic` и structured `knowledge-refresh-node/v1`. Automatic Git hooks, required-knowledge final validation, installed Agent skill, MCP facade самого сервиса, onboarding profile и durable process checkpoints нет. Memory, semantic document backend и глобальные hooks не входят в v1. [Отчёт](../reports/2026-09-18-project-knowledge-service-v1.md) отделяет реальные tests/initial load от будущего внешнего E2E.
