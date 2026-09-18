# Project Knowledge Service и Graphify

**Статус:** действующий контракт реализованного Python-среза TASK-0030 от 2026-09-18; принят пользователем, completed v18. [Guide](../guides/project-knowledge.md), [проверки, приёмка и ограничения](../reports/2026-09-18-project-knowledge-service-v1.md). Это отдельный advisory service, не автоматическая integration в AgentPreparation или execution workflow.

## Ответственность и backend

Orchestrator Agent выбирает, когда получить контекст и когда обновить знания. `ProjectKnowledgeService` вычисляет snapshot, проверяет freshness, публикует проверенную версию и возвращает bounded query result. `GraphifyProvider` запускает закреплённый indexer и read-only MCP query. Task Manager, process state и semantic decisions сервису не принадлежат.

Backend — Graphify-Labs/graphify, дистрибутив `graphifyy==0.9.63`, профиль `code-only/no-cluster`, schema identity `graphify-raw-json/0.9.63`. Совместимость проверена на установленной версии и Windows fixtures; [dependency snapshot](../../requirements/graphify-probe-windows-py312.txt) закрепляет пакеты, но не является wheel-hash attestation или cross-platform lockfile. Service не устанавливает provider, глобальные hooks или конфигурацию.

Graphify не является GraphQL. [Исходный документ](../development/01-graphify-integration-ai-orchestrator.md) задаёт Graphify через MCP; GraphQL API не включён. Project Memory — отдельный будущий сервис. `.md`, semantic documents и memory overlay не добавляются в code graph.

## Экспортируемые контракты

Классы доступны из `orchestrator`; dataclass сериализуются через `to_dict()`.

| Контракт | Реализованная форма |
| --- | --- |
| ProviderIdentity | upstream, package, version, extraction, schema |
| ProviderCapabilities | query=true, full_rebuild=true, incremental_refresh=false, textual_provenance=true, semantic_documents=false |
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

Raw bytes сохраняются без собственного parser/graph engine. Upstream AST placeholders с пустыми source_file/source_location и внешние imports/imports_from на отсутствующий target допускаются только в проверенной AST-форме. Они отдельно учитываются как unresolved_nodes/external_import_edges и не дают source evidence. Другие dangling endpoints и чужие непустые paths отклоняются. Blank/whitespace-only files остаются в snapshot, но допускаются без AST nodes и перечисляются в coverage. Частичная экстракция не объявляется успешной по exit code.

Артефакты `project-knowledge:graph:<version>` и `project-knowledge:index:<version>` находятся в `.orchestrator/artifacts/`. Index связывает provider, policy, snapshot, coverage, raw counts, indexed_at, graph metadata/hash. `.orchestrator/knowledge/current.json` выбирает успешный index record. Pointer ограничен 8 KiB, index — 2 MiB, graph/manifest provider — 32 MiB каждый. Repository чтение bounded, metadata и SHA-256 проверяются.

Failed refresh сохраняет старый current graph; источники могут стать stale относительно него. Непривязанные immutable versions после ошибки publication допустимы; GC нет. Atomic replace не является общей транзакцией файлов, Task Manager и process state. При crash lock может остаться: автоматический lease/steal отсутствует; требуется остановить writers и проверить конкретный lock перед восстановлением.

## Query и MCP

`query(question, mode="bfs", depth=2, token_budget=1000, max_chars=6000, allow_stale=False)` не индексирует. Missing/failed/stale дают degraded direct discovery; stale query разрешён лишь явно и остаётся degraded. Question ≤1024 UTF-8 bytes, mode bfs/dfs, depth 1–6, token budget 1–4000, max_chars 1–12000. Token budget приблизительный; свой character limit независим и отмечает truncation.

Каждый query запускает новый stdio MCP process с точной версией graph. Upstream требует .json, поэтому bounded graph bytes передаются в isolated temporary graph.json без work-memory sidecars. Initialize проверяет protocolVersion 2025-03-26 и наличие query_graph. Adapter вызывает только query_graph: public project_path, arbitrary tools, PR и mutating commands отсутствуют. Raw provider API — внутренняя доверенная граница Python caller; host ACL/sandbox он не заменяет.

Default budgets: combined stdout/stderr 1 MiB, index timeout 90 s, version check 25 s, MCP session 25 s, request 8 KiB, очередь 32 messages и максимум 100 notifications. Команды передаются массивом, shell=false. Environment whitelist сохраняет необходимые runtime/Windows paths, убирает inherited API credentials/provider settings; query logging выключен. Это не OS network sandbox: pinned provider и host environment должны быть доверенными; завершение дерева сторонних subprocesses отдельно не гарантируется.

Textual upstream errors, isError, malformed protocol, wrong ID, overflow и timeout дают structured failure/degraded. Content — недоверенные данные, не инструкции агенту. Citations извлекаются из NODE src/loc только для indexed paths, validation=indexed-path-only; строка и relevance непосредственно в коде не проверяются. EXTRACTED/INFERRED/AMBIGUOUS — обнаруженные textual tags, не независимая confidence attestation. После query повторно проверяются source snapshot и graph; source drift снимает fresh.

## Оставшаяся миграция

Caller может передать knowledge result как evidence в AgentPreparation, но автоматической context integration, required-knowledge final validation, installed Agent skill, MCP facade самого сервиса, onboarding profile и durable process checkpoints нет. Полное agent execution — следующий этап roadmap. Memory, incremental refresh, свой backend и глобальные hooks не входят в v1. [Отчёт](../reports/2026-09-18-project-knowledge-service-v1.md) отделяет реальные tests/initial load от будущего внешнего E2E.
