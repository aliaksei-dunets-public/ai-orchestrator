# Дизайн TASK-0031: единый Project Knowledge Graph

**Статус:** исторический implementation design, заменён уточнениями пользователя 2026-09-18 и [дизайном host-agent варианта A](2026-09-18-graphify-host-agent-design.md). Первоначальный headless PoC остановился без semantic backend, mixed default implementation откачена. Последующий host-agent PoC успешен без нового backend; production admission ещё не выполнен, TASK-0031 blocked на устаревших preparation bindings. Это рабочий план, исключённый вместе со всей папкой `docs/plans/`. [Действующий контракт](../architecture/project-knowledge-service.md), [результаты](../reports/2026-09-18-single-project-knowledge-graph-v1.md). Дальнейшие разделы описывают прежний план, не выполненную документную интеграцию.

## Решение

В проекте существует один `Project Knowledge Graph` на базе Graphify. В его source corpus входят выбранная кодовая база и долговечные документы проекта: архитектурные документы, ADR, актуальная техническая и продуктовая документация и доменные концепты. Код и документы индексируются одной Graphify extraction, одной immutable graph/index version и одним current pointer; отдельный documentation graph не создаётся.

Критерий включения: информация должна оставаться источником правды проекта через несколько месяцев. Временные задачи, планы, черновики, промежуточный анализ, execution envelopes, review/acceptance evidence и содержимое `.orchestrator/` остаются в оперативном Task Context/Task Manager/Artifact Repository. `obsolete/`, `docs/plans/` и `docs/reports/` всегда исключены. Исторические imported design archives исключаются policy roots, пока отдельное решение не переведёт материал в актуальную durable documentation.

## Компоненты и поток

`CorpusPolicy v2` задаёт безопасные project-relative roots и расширения кода/Markdown. `snapshot_sources` считает один fingerprint по байтам кода и durable docs. `ProjectKnowledgeService.refresh` копирует этот snapshot во временный corpus, вызывает Graphify один раз в mixed code+documents режиме, проверяет source manifest/nodes/edges и публикует immutable graph и index атомарно. Provider identity, policy и snapshot binding входят в index. При provider/API failure старый current pointer сохраняется.

`query_graph` остаётся единственным read-only MCP query tool. Ответ advisory: citations — indexed-path evidence, semantic assertions требуют прямой проверки. Knowledge Service не владеет задачами, workflow, memory, user decisions или Task Context. Orchestrator Agent сам решает, когда запросить context и когда выполнить explicit refresh/final-validation gate.

Graphify semantic document extraction требует настроенного provider backend/API; code-only mode больше не считается полным Project Knowledge Graph. Без provider credentials refresh возвращает structured degraded/failure и не публикует неполный граф. Тесты используют deterministic fake provider для contract coverage и отдельный real Graphify test только при явно настроенном environment.

## Миграция и границы

Существующая code-only version считается устаревшим provider/policy snapshot. При первом успешном mixed refresh новый version заменяет current pointer атомарно; старый immutable graph сохраняется для диагностики. Никакого второго documentation pointer или graph directory не появляется. Onboarding и Task Manager не получают новую базу. Следующие TASK-0019/0020 подключат этот service к workflow context/final-validation; TASK-0031 не реализует automatic refresh, memory или incremental backend.

## Проверки

Покрываются durable document inclusion, code/document shared graph, transient plan/report/task exclusion, obsolete exclusion, policy fingerprint, provider failure fallback, old code-only migration, query freshness, citations и mixed Graphify argument contract. Acceptance требует explicit source manifest, real provider evidence when configured, all tests, updated guides and no separate documentation artifact.
