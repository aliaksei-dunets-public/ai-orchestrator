# TASK-0031: host-agent Graphify v1

**Статус:** архитектурное уточнение по запросу пользователя; результаты PoC фиксируются отдельно. Рабочий Task Context, не источник для Project Knowledge Graph. Не разрешает настройку новых backend.

## Выбор

Вариант A — Graphify skill и semantic extraction текущим development host-agent — выбран для v1. AST/code extraction остаётся на текущей установке Graphify. Вариант B — автономный headless semantic service — будущая TASK-0032, без выполнения или настройки сейчас.

Headless `graphify extract` требует semantic backend для Markdown; это не ограничение skill-режима. Bundled `skill-codex.md` 0.9.63 использует host semantic agent по `references/extraction-spec.md`, затем Graphify build/export/save_manifest. Собственный Markdown extractor, новая модель, credential propagation, API proxy и глобальная установка skill не требуются для PoC.

## Операции одного графа

Целевые операции Project Knowledge Service: `refresh_code_graph()` — deterministic AST; `refresh_document_graph(host_extraction, expected_document_snapshot, expected_graph_version)` — приём результата semantic skill, не скрытый LLM вызов. Названия обозначают разные способы обновления частей **одного** Project Knowledge Graph, не отдельные графы/пойнтеры.

Один graph/index/current pointer. Code/document snapshot и freshness учитываются раздельно; свежие документы не делают старый code snapshot свежим. Документный admission проверяет upstream schema, явный allow-list действующих документов, source hash, prompt/skill version, confidence/evidence и совпадение base graph version. Ошибка или source drift сохраняют прежний pointer. AST IDs и code source evidence не перезаписываются семантическими aliases.

Host-agent отвечает за semantic extraction; сервис — за детерминированный admission/publication. Extraction JSON — Graphify output, не собственный parser. Кодовые связи и семантические claims имеют разные основания и confidence. Токены оплачиваются текущей host-сессией; при отсутствии usage в host tool считать стоимость неизвестной, не нулевой.

## Ограниченный PoC

Два действующих architecture документа: `agent-runtime-contract.md`, `project-knowledge-service.md`. Upstream detect/cache → host semantic chunk → AST-first merge с существующим immutable code graph → upstream build/export → Graphify MCP query. Все writes в `.tmp/graphify-host-poc-0031`, без публикации current pointer и без второго documentation graph.

Проверять отдельно наличие обоих doc sources, документный запрос MCP, code IDs/source evidence и реальные document→code edges. Простое совпадение названий не считать доказательством связи. Не использовать upstream save-result/work-memory/reflect в Project Knowledge corpus: задачи, планы, промежуточные результаты и QA остаются Task Context.

Рабочий pipeline менять только после успешного PoC и новой подготовки TASK-0031. Раздельные refresh API и composite index — целевой контракт, не уже реализованные методы.
