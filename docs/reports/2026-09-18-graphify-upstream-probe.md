# Реальная проверка Graphify перед adapter implementation

**Статус:** выполненный upstream fixture probe TASK-0027, 2026-09-18. Это не готовый Project Knowledge Service, не индексация всего проекта и не приёмка knowledge integration.

## Среда и ограничения

Выбран официальный PyPI пакет `graphifyy==0.9.63`, upstream Graphify-Labs/graphify. Установлен с MCP extra и only-binary в отдельную `.tmp/graphify-0.9.63-venv`; основная .venv и Task Manager не изменены. `pip check`: No broken requirements found. MCP SDK 2.2.0, starlette 1.6.0, tree-sitter 0.25.2. [Точный снимок зависимостей](../../requirements/graphify-probe-windows-py312.txt) относится только к проверенной Windows/Python 3.12 среде, без wheel hashes.

Сетевой доступ pip первоначально запрещён sandbox (WinError 10013), затем выполнена разрешённая эскалация для PyPI metadata/download. Исходники проекта не отправлялись: probe использует только синтетические fixtures, extraction/MCP работают в ограниченной среде без ключей моделей. Это не независимый аудит сетевых обращений всех зависимостей.

Не запускались graphify install, hooks, global registration, watch, PR tools, semantic extraction, интеграции внешних моделей. Query logging отключён GRAPHIFY_QUERY_LOG_DISABLE=1. В whitelist среды сохранены Windows system/home-location параметры без изменения их значений; API credentials исключены. Upstream CLI читает skill locations для version check даже при extract: без USERPROFILE/HOMEDRIVE/HOMEPATH он падает до extraction. Обходить это установкой global skill не требуется.

## Воспроизведение

[scripts/graphify_probe.py](../../scripts/graphify_probe.py), SHA-256 `6ce0a84af613e1e0ce25d4162f4695a759489fca07adcf3b4464c3d1670f7c52`.

```powershell
.venv\Scripts\python.exe -X utf8 scripts\graphify_probe.py --python .tmp\graphify-0.9.63-venv\Scripts\python.exe
```

Probe создаёт уникальный проверенный temp directory внутри workspace/.tmp и удаляет только собственные синтетические fixtures после завершения. Среда Graphify сохранена для следующего этапа; пользовательские файлы не удалялись. Для нового окружения сначала явно создайте отдельный venv и установите версии из закреплённого requirements; скрипт сам ничего не устанавливает.

## Фактический результат

- Fixture files: helper.py, модуль.py, Card.tsx, Panel.vue, notes.md.
- `python -m graphify extract <fixture-root> --code-only --no-cluster --out <isolated-output> --force --exclude indexed/**`: успех без credentials. Notes.md явно skipped; нет semantic pass.
- Graph JSON: 10 nodes, 12 edges. Node source_files: Card.tsx, Panel.vue, helper.py, модуль.py. TSX Card присутствует; Vue source присутствует. Полнота Vue framework semantics этим не доказана.
- Реальный stdio initialize → notifications/initialized → tools/list → tools/call: успех, protocol 2025-03-26. query_graph и graph_stats ответили без error.
- Query helper/Child/Base: 1036 characters. В ответе реальные NODE src/loc и EDGE provenance, imports/calls/inherits с EXTRACTED.
- После модуль.py → renamed.py и удаления Panel.vue: повторный extract успешен. Sources Card.tsx, helper.py, renamed.py; прежние модуль.py и Panel.vue отсутствуют. Это проверка full re-scan на существующем fixture output, не всего incremental API.

Пример фактической evidence: `EDGE .call() --calls [EXTRACTED context=call]--> helper() at=модуль.py:L4`. Это данные ответа, не инструкция агенту и не утверждение свежести production графа.

## Подтверждённые integration нюансы

1. Package extra действительно нужен для MCP. Реальный SDK здесь 2.x, поэтому предположение о единственном SDK 1.x неверно. Raw JSON-RPC probe подтверждает конкретный pinned вариант.
2. CLI --out задаёт output root, а graph.json находится ниже `graphify-out/graph.json`; нельзя считать сам --out путём к graph file.
3. Graph из --no-cluster пригоден для реального MCP запроса; отсутствие community labels нужно возвращать как ограничение, не выдумывать enrichment.
4. MCP catalog содержит query_graph, get_node, get_neighbors, shortest_path, graph_stats, god_nodes, get_community и get_pr_impact/list_prs/triage_prs. Wrapper должен разрешать только выбранный read-only subset, а не экспортировать upstream целиком.
5. Upstream schema допускает project_path. Fixed-project wrapper обязан запрещать этот аргумент и запускаться с явным graph file. Upstream multi-project capability — не isolation Orchestrator.
6. Query budget приблизительный; production adapter должен отдельно ограничивать полученный content/bytes и иметь timeout. Probe работает только с малым контролируемым графом, его ограничений недостаточно для production transport.
7. Для безопасного refresh предпочтительна новая staging graph version с проверкой corpus before/after и atomic publication. Нельзя запускать force над единственным production графом и считать exit=0 доказательством полноты.

## Что ещё требуется

Provider contract и fixed-root adapter, source snapshot dirty/untracked, явный include/exclude и secret policy, manifest/coverage verification, failed-refresh сохранность старого графа, graph integrity, degraded status, citation validation, production bounded transport и restart MCP после публикации. Probe не заменяет эти tests. Затем — initial load реального разрешённого корпуса проекта и явный post-change refresh.

Устанавливаемый Agent skill, автоматическая подготовка с knowledge query, execution gates, memory и ABAP в эту проверку не входят. Полная TASK-0027 остаётся открытой.

## Первичные источники

Документация проверена 2026-09-18: [README upstream](https://github.com/Graphify-Labs/graphify/blob/v8/README.md), [pyproject](https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/pyproject.toml), [CLI source](https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/graphify/cli.py), [MCP source](https://raw.githubusercontent.com/Graphify-Labs/graphify/v8/graphify/serve.py), [MCP reference](https://graphiffy.com/docs/mcp-tools). Ветка v8 движется; фактическая проверка закреплена package version 0.9.63 и installed dependency snapshot, не HEAD ветки.
