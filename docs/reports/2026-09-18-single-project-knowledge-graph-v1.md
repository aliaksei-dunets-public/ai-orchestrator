# TASK-0031 — Graphify skill / host-agent PoC

**Статус:** возможность варианта A подтверждена на двух действующих Markdown-документах; рабочий pipeline/current pointer не заменены. TASK-0031 не завершена. Вариант B — будущая TASK-0032.

## Что поддерживается из коробки

В установленном `graphifyy==0.9.63` bundled `skill-codex.md` прямо разделяет deterministic AST и semantic extraction текущим host-agent по `skills/codex/references/extraction-spec.md`. Skill не требует отдельного API-ключа; headless `graphify extract` для Markdown требует semantic backend. **Предыдущий вывод о невозможности документной индексации без нового backend относился только к headless и был ошибочно обобщён.**

## Проверенный PoC

Документы: `docs/architecture/agent-runtime-contract.md` и `docs/architecture/project-knowledge-service.md`. Upstream detect/cache → host semantic extraction → AST-first merge с проверенным существующим immutable code graph → upstream build/cluster/export/save_manifest → прежний Graphify MCP `query_graph`.

Первый upstream prompt вернул 22 doc/concept nodes и 24 semantic edges. Кандидат: 1052 nodes / 3235 edges, но **0 прямых document→code edges**. Совместное хранение и одновременное присутствие code/doc nodes в ответе не доказывают связи.

Вторая проверка передала host-agent три проверенных canonical AST IDs; он извлёк только явные документальные упоминания. AST-first merge сохранил кодовые IDs/source evidence. Итог: 1052 nodes / 3238 edges, 22 doc-sourced nodes и три `references [EXTRACTED, 1.0]`:

- `agent-runtime-contract.md` → `AgentGraphRuntime`.
- `project-knowledge-service.md` → `ProjectKnowledgeService`.
- `project-knowledge-service.md` → `GraphifyProvider`.

Это host semantic extraction с AST vocabulary, **не автоматическое связывание Graphify по labels**, не собственный Markdown extractor и не подтверждение реализации контрактов.

Прежний raw code snapshot: 989 nodes / 3324 edges; после upstream build — 1030 / 3211. Поэтому нельзя сравнивать raw и built counts как потерю кода при добавлении документов. Сохранение всех base-built IDs и code evidence проверено. Upstream diagnostics уже в baseline показывают 310 dangling-endpoint raw edges, 17 self-loops и 113 collapsed endpoint pairs; PoC эти counters не увеличил. Предупреждения сохранены, не выданы за clean graph.

## Пример MCP запроса

`GraphifyProvider.query(candidate_graph, project_root, question="явные действия агента", mode="bfs", depth=2, token_budget=4000)` вызывает существующий `query_graph`. Токены взяты из graph vocabulary. Ответ содержит `src=docs/architecture/agent-runtime-contract.md loc=None`; запрос `project knowledge service` содержит второй документ. Документные sources подтверждены обоими запросами.

Graphify token budget приблизительный: первый ответ превысил его, второй truncated. Это не hard output limit; service сохраняет отдельные byte/character budgets.

## Необходимые изменения и отбор

Новая инфраструктура, модели, credentials и backend конфиги не добавлены. Использованы bundled skill, host session и штатные Python API текущего Graphify; slash-command/project skill автоматически не устанавливался. Минимальный ранее отделённый compatibility fix подтверждён реальным manifest: у обоих документов `ast_hash=""`, `semantic_hash` совпадает с MD5 source. Код по-прежнему проверяется по ast_hash. Стоимость host semantic extraction не нулевая; actual token usage host tool не публикует, поэтому она отмечена unknown.

Включать только явно выбранные действующие architecture/ADR, актуальные product/technical docs и постоянные guides/specifications о текущем состоянии. Исключать tasks/plans/reports, временные specifications, весь `.orchestrator` (включая runs), scratch/working artifacts, архивы и устаревшие материалы. Никакой upstream save-result/work-memory/QA overlay не включён.

## Один граф, две refresh операции

Для v1 выбран вариант A. Целевой API: `refresh_code_graph()` — deterministic AST; `refresh_document_graph(host_extraction, expected_document_snapshot, expected_graph_version)` — admission semantic skill result. Это обновления двух частей **одного** graph/index/current pointer, не два графа.

Code/document freshness и source evidence учитывать раздельно. Свежие документы не делают старый AST snapshot свежим. Эти отдельные методы/composite index **ещё не реализованы**; текущий `refresh()` остаётся рабочим code-only pipeline.

## Артефакты и следующий шаг

Кандидатный единый code+docs graph: `.tmp/graphify-host-poc-0031/graphify-out/graph.json`. Рядом: `manifest.json`, `poc-result.json`, `poc-result-unbound.json`, `query-results.json`. Исходные host fragments и build/query helpers сохранены в том же PoC каталоге. Это изолированный кандидат, не второй documentation graph и не current version.

Current pointer SHA-256 до/после: `07cb3e94c50f267d1b662633ba28360092a9e5af47a7b549f6d3df708bb44134`. Code snapshot кандидатного графа — прежняя immutable версия и может быть stale; текущие архитектурные документы после уточнения контракта также отличаются от сохранённых PoC source copies. Никакой fresh/readiness claim не сделан.

Далее в TASK-0031: новая подготовка под вариант A; bounded admission host fragment, source/prompt/base-version bindings, формат export `links` против текущего raw `edges`, document citations с `loc=None`, раздельные freshness/refresh и atomic publication одного графа. Прежние workspace plan/review/package устарели. Рабочий pipeline менять после этих guards/tests, а не считать прототип production service. TASK-0032 остаётся created и отложена.
