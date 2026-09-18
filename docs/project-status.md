# Текущее состояние Orchestrator

**Статус:** действующий снимок фактически реализованного состояния для агента.

**Дата:** 2026-09-18.

Этот документ обновляется после каждого завершённого этапа. Он фиксирует только подтверждённые кодом, тестами и командами возможности; планы остаются в `docs/plans/`, порядок работ — в `docs/roadmap.md`, история изменений — в `docs/worklog.md`.

## Репозиторий

- TASK-0037 — explicit WorkflowExecutor принят пользователем и completed v15: зарегистрированные model/capability adapters, точный model dispatch/receipt и явный fallback, immutable портовые артефакты/scoped exports, registered roles подготовки/gates и workflow snapshot в Plan/Review/Package/preflight. Приёмка зарегистрирована 2026-09-19 (`user-acceptance/task-0037/2026-09-19`), active run/claim отсутствуют. [Контракт](architecture/workflow-execution.md), [guide](guides/workflow-execution.md), [отчёт](reports/2026-09-18-task-0037-workflow-execution.md). 25 новых предметных проверок; root 206 (205 passed/1 Windows symlink skip), 0 failures; external LLM provider не подключён, локальный subprocess fixture и настоящий unittest проверены. Runtime in-memory/executor-free, Task Manager не изменён; durable/live/installed Agent delivery остаются будущими.

- TASK-0036 — конструктор workflow v1 реализован и принят пользователем: completed v23, без active run/claim. Строгие TOML/catalog/contract schemas, плоская компиляция подграфов с namespace/exit mapping, data-flow guards, project patch/replace, модельные descriptors и фиксированный snapshot. Builder skill подключён в `.agents/skills/orchestrator-workflow-builder`; самостоятельный HTML-инспектор показывает узлы/переходы/вложенность/settings. [Контракт](architecture/workflow-builder.md), [guide](guides/workflow-builder.md). Исполнитель и optional фасадная интеграция добавлены отдельной TASK-0037.

  Проверки TASK-0036: 22/22 предметных; root 181 (180 passed/1 Windows symlink skip), compileall и runnable guide; headless browser navigation/cards/edge/search/zoom/narrow/injection/offline checks прошли. Frontmatter/UI skill проверены отдельно; официальный quick_validate недоступен из-за отсутствия PyYAML, зависимости не устанавливались. [Отчёт](reports/2026-09-18-task-0036-workflow-builder-v1.md).

- TASK-0035 — подтверждённые исправления повторного аудита: реализован совместимый `Node.required_outputs_by_outcome`, knowledge confirmation использует runtime `needs_input` с domain status `awaiting_confirmation`, knowledge execution gates сохраняют request и отдельные immutable evidence versions. Кандидат проверен и принят пользователем 2026-09-18; TASK-0035 completed v16, без active run/claim; [результаты и границы](reports/2026-09-18-task-0035-agent-runtime-audit-fixes.md), [дизайн](plans/2026-09-18-agent-runtime-audit-fixes-design.md). Бюджеты и definition binding сохраняются. Последний root набор с real pinned Graphify: 159 tests, 158 passed, 1 Windows file-symlink skip, 0 failures; добавлено 8 предметных регрессий, 3 guide примера исполнены.

- С 2026-09-17 принято [агент-центричное направление](architecture/agent-centric-orchestration.md): агент выбирает работу внутри Workflow Graph, детерминированное ядро проверяет и хранит результаты. Текущий Task Manager с SQLite не меняется.
- Для знаний реализован [Project Knowledge Service с Graphify](architecture/project-knowledge-service.md): рабочий code-only snapshot, immutable graph/index, atomic current pointer, explicit full refresh, native incremental refresh и query_graph-only MCP adapter. Graphify 0.9.63 работает из прежней отдельной .tmp среды. Incremental path проверяет changed/added/deleted/renamed code sources через `graphify update --no-cluster`, сохраняет старый pointer при ошибке и даёт диагностируемый full fallback для legacy manifest. `AgentExecution.precommit_gate()` теперь явно делегирует этот gate и возвращает `commit_allowed`; automatic Git hook не заявляется. PoC TASK-0031 подтвердил semantic extraction двух Markdown текущим host-agent по Graphify skill без нового backend/API-ключа, но документный кандидат не опубликован. Default pipeline и execution fingerprint code-corpus/v1 сохранены; добавлен semantic_hash manifest compatibility fix. `docs/plans`, `docs/reports`, `.orchestrator` и `obsolete` исключены.
- TASK-0027 ведёт общую миграцию, preparing: пользователь подтвердил [поэтапный дизайн](plans/2026-09-17-agent-centric-graphify-migration-design.md), выбран Graphify-Labs/graphify и локальный code-only first slice. [Исходный отчёт](reports/2026-09-17-agent-centric-graphify-assessment.md) сохраняет baseline до реализации.
- TASK-0028 реализует [AgentGraphRuntime](architecture/agent-runtime-contract.md): явные Python submit/resume/cancel, process revision, task-definition binding, wait identity, bounded cycles и history в памяти без callback dispatch. Принята пользователем, completed v18, без active run/claim; [guide](guides/agent-runtime.md), [отчёт и ограничения](reports/2026-09-17-agent-runtime-v1.md).
- TASK-0029 реализует [AgentPreparation](architecture/agent-preparation.md): explicit Context/Analysis/Plan/Review, shared primitives, immutable publication, plan projection, ready без claim и pending/history reconciliation. Принята пользователем, completed v18, без active run/claim; [guide](guides/agent-preparation.md), [основание приёмки](reports/2026-09-18-agent-preparation-v1.md#user-acceptance).
- TASK-0030 — Knowledge Service slice, принята пользователем, completed v18, без active run/claim; immutable package и lifecycle в [отчёте](reports/2026-09-18-project-knowledge-service-v1.md). Общая TASK-0027 preparing v13, не completed; health_check=[]. Installed Agent skill и MCP facade ядра/knowledge service отсутствуют; full execution gates реализованы в принятом к readiness TASK-0017; callback GraphRuntime/PreparationWorkflow удалены в TASK-0034; единственный process runtime — AgentGraphRuntime.
- TASK-0020 — Incremental Refresh реализован и принят пользователем (`completed` v30): native Graphify update, manifest baseline, atomic publication/fallback и явный `AgentExecution.precommit_gate`; [отчёт](reports/2026-09-18-task-0020-incremental-refresh-v1.md).
- TASK-0033 — `[HIGH] Реализовать configurable KnowledgeRefreshNode`, принята пользователем и `completed v30`: добавлены режимы `auto`/`incremental`/`full`, strict `fallback_required`, default user confirmation и trusted per-node automatic full; [дизайн](plans/2026-09-18-knowledge-refresh-node-design.md), [отчёт](reports/2026-09-18-task-0033-knowledge-refresh-node-v1.md). Active run/claim отсутствуют, `health_check=[]`.
- TASK-0016 — [AgentExecution/preflight и work units](architecture/agent-execution.md), принята пользователем и completed v19, без active run/claim; [guide](guides/agent-execution.md), [отчёт](reports/2026-09-18-agent-execution-v1.md). Read-only immutable/source preflight до claim, explicit units/dependencies/delta validation, waits/new claims, lease, pending/unknown effects. TASK-0017 реализовала [execution gates и final acceptance](architecture/execution-gates.md); принята пользователем и completed v27, без active run/claim (проверено публичным API при TASK-0035).
- TASK-0031 — HIGH: единый Project Knowledge Graph на базе Graphify, blocked v21; host-agent PoC успешен на двух действующих архитектурных Markdown: 22 документных узла, три прямые references на AST-классы после передачи canonical IDs, оба документа найдены MCP-запросами. Текущий production code-only snapshot/pointer сохранён и остаётся stale/degraded; document admission не выполнен. BLOCK-01 provider_access разрешён; BLOCK-02 preparation_binding открыт: старые workspace plan/review/package требуют безопасного reprepare под вариант A, а blocked resume=ready не позволяет прямой переход в preparing публичным API. Task Manager не изменяется, устаревший пакет не выдан за актуальный ready. [Короткий отчёт](reports/2026-09-18-single-project-knowledge-graph-v1.md).
- TASK-0032 — будущий автономный headless semantic service Graphify (вариант B), created v3, definition v2, без подготовки/run/claim. Не является условием варианта A и не выполняется без отдельного решения пользователя.

- Активный проект называется `Orchestrator`.
- Старый продукт, релизы и старое состояние находятся в `obsolete/` как неизменяемый справочный архив.
- Новый графовый подход и действующие контракты находятся в `docs/`.
- In-memory runtime, подготовка до ready, work units/gates и explicit configurable WorkflowExecutor реализованы; durable/installed полный Orchestrator Agent пока отсутствует.

## Пакет Onboarding

Каталог: `packages/onboarding/`. Дистрибутив `orchestrator-onboarding`, импорт `orchestrator_onboarding`, команда `orchestrator-onboarding`.

Онбординг поддерживает безопасные `preview`/`apply` для внешнего проекта и self-hosting. Self-hosting текущего репозитория проверен 2026-09-15: созданы `.orchestrator/project.json` и `.orchestrator/project-context.md`, повторный preview показал 0 изменений. План содержит точный diff и SHA-256; `apply` требует подтверждённый хеш, повторно проверяет состояние, защищает пользовательские файлы и восстанавливает записанные файлы при обычной ошибке. Проверяются пути, UTF-8, символические ссылки, конфликты и наличие Task Manager skill в подключённом ядре. Прямой запуск исходного файла сохранён.

Онбординг создаёт `.orchestrator/project.json`, `.orchestrator/project-context.md`, управляемый блок `AGENTS.md` и правило `.orchestrator/state/` в `.gitignore`. Одноразовая инструкция первого запуска уже реализована и ведёт агента через полный стартовый сценарий: осмотр проекта, вопросы, preview/apply с подтверждением хеша, отдельное подтверждение установки Task Manager и финальную проверку. Для установленного Task Manager добавлены явные `check-task-manager` (реальный MCP handshake и read-only health check) и `mcp-config` (локальный host-neutral конфиг с выбранным Python, без записи глобальных настроек). После завершения постоянным проектным skill остаётся Task Manager; пакет не устанавливает зависимости молча и не запускает граф.

Подробнее: [контракт](architecture/onboarding.md), [гайд](guides/onboarding.md), [README пакета](../packages/onboarding/README.md).

## Task Manager Service

Каталог: `packages/task-manager/`. Дистрибутив `orchestrator-task-manager`, импорт `orchestrator_task_manager`; внешних зависимостей нет, ядро Orchestrator не импортируется. Для текущего self-hosted проекта пакет установлен в `.venv` в editable-режиме и проверен через CLI.

Каноническое состояние — `.orchestrator/state/tasks.sqlite3`. SQLite хранит снимок задачи, события, операции идемпотентности, tombstone удалённых задач и счётчик ID; схема развивается через встроенный реестр миграций с текущей версией `5`. Каждая мутация требует `expected_version`, выполняется транзакционно и создаёт событие; повторяемые операции принимают `operation_id`, события содержат контекст происхождения.

Поддерживаются создание, чтение, SQL-фильтрация и cursor-поиск, история, экспорт JSON, backup/restore SQLite, обратимая архивация, retention в три календарных месяца и физическое удаление с tombstone, типы задач `implementation`, `analysis`, `investigation`, `incident`, `exploration`, статусы подготовки/исполнения/ожидания/блокировки, plan и SHA-256 guard перед `ready`, claim/lease, блокеры, решения пользователя, ссылки на запуски, приёмка, завершение, отмена и усиленная read-only диагностика `validate`. Каноническое определение задачи находится в карточке Task Manager; отдельная specification не обязательна.

Дополнительный срез TASK-0023 реализует атомарный `accept_task`, SQL `summary`, структурный фильтр архива до LIMIT, единый транзакционный снимок export/validate, UTC для injected clock и файловые ошибки TaskError. SHA-256 потоковый; чтение документа проверяет именно возвращаемые байты. Restore мигрирует временную копию и создаёт консистентную safety copy, требует остановки других процессов/мутаций. Измерения и границы нагрузки опубликованы в [отчёте](reports/2026-09-16-task-manager-hardening.md).

TASK-0024 разделяет реализацию на contracts, migrations, repository, service, storage_transfer и diagnostics; task_manager сохраняет прежние импорты. Сервис не выполняет SQL и не вызывает приватные методы репозитория. Экспорт и диагностика используют read-only транзакцию, схема остаётся версии 5. [Архитектура пакета](../packages/task-manager/src/orchestrator_task_manager/resources/docs/architecture.md) входит в wheel; [отчёт разделения](reports/2026-09-17-task-manager-modularization.md) содержит проверки совместимости и парные замеры.

CLI:

```powershell
orchestrator-tasks --project . create ...
orchestrator-tasks --project . list
orchestrator-tasks --project . summary
orchestrator-tasks --project . list --format table
orchestrator-tasks --project . show TASK-0001
orchestrator-tasks --project . history TASK-0001
orchestrator-tasks --project . validate
orchestrator-tasks resources
orchestrator-tasks api
```

Панель запускается `orchestrator-tasks-web --project . --port 8765`, слушает только `127.0.0.1` и работает только на чтение.

CLI покрывает защищённые операции подготовки/исполнения, blocker/decision и приёмку. JSON по умолчанию и коды выхода сохранены; ошибки разбора аргументов также JSON. `--expected-version` фиксирует прочитанную версию, без флага CLI читает текущую. Для повтора с operation-id требуется первоначальная версия. Таблица поддерживается для list/show/summary; `api` показывает сигнатуры, не создавая базу.

В пакет входят полный [контракт](../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md), [гайд](../packages/task-manager/src/orchestrator_task_manager/resources/docs/usage.md) и [пример skill](../packages/task-manager/src/orchestrator_task_manager/resources/examples/skills/orchestrator-task-manager/SKILL.md). Проектный skill `.agents/skills/orchestrator-task-manager/SKILL.md` указывает на этот пример. Skill выбирает MCP stdio для внешнего агента, прямой `TaskManagerService` для in-process Python-оркестратора и CLI как fallback.

## Правила для агента

TASK-0025 исправляет обнаруженную аудитом ошибку CLI export: общий реестр переноса сопоставляет export с export_state. Экспорт, JSON-ошибки назначения и CLI backup/restore покрыты новыми регрессиями; [отчёт исправления](reports/2026-09-17-task-manager-cli-export-fix.md). Публичная карточка TASK-0025 завершена с пользовательской приёмкой. TASK-0026 реализует MCP stdio-адаптер: один общий пакет, отдельный экземпляр на проект, фиксированный root, 35 структурированных инструментов и ограничение файловых путей. Полный сценарный аудит исправил schema validation, lifecycle JSON-RPC, формат structuredContent, direct API validation, operation fingerprint и blocker diagnostics. TASK-0026 завершена с явной пользовательской приёмкой; [дизайн](plans/2026-09-17-task-manager-mcp-adapter-design.md), [исходный отчёт](reports/2026-09-17-task-manager-mcp-adapter.md), [интеграционный отчёт](reports/2026-09-17-task-manager-onboarding-mcp-hardening.md), [полный аудит и исправления](reports/2026-09-17-task-manager-full-audit-fixes.md).


- Источник истины о задаче — публичный Task Manager API, не Git и не SQLite напрямую.
- Перед мутацией перечитай задачу и передай текущую `version` как `expected_version`.
- При конфликте версии перечитай задачу; не повторяй изменение вслепую.
- `ready` требует каноническую карточку задачи, актуальный `plan.md`, review, Execution Package и отсутствия блокеров; отдельная specification не обязательна. `active` достигается только через claim.
- Состояние запуска принадлежит Graph Runtime; Task Manager хранит только ссылки.
- После мутации проверь карточку, историю и при необходимости `validate`.

## Реализованное ядро и ограничения

TASK-0034 реализует [удаление callback GraphRuntime](plans/2026-09-18-remove-callback-runtime-scope.md) и PreparationWorkflow. Классы, модули, exports и активные зависимости удалены; общие Graph/Node/NodeResult/WaitState/WorkflowRun, ошибки, terminal constants и validator находятся в `orchestrator.runtime_contracts`. Прежние callback guides заменены инструкциями миграции. [Отчёт изменений и проверки](reports/2026-09-18-task-0034-callback-removal.md); пользователь принял результат 2026-09-18, TASK-0034 completed v20, без active run/claim. Приёмка зарегистрирована атомарным публичным accept для candidate callback-removal-v1:deb47e44de0fc290606a5299bd2948261f8c08f282425e48e1c928b356aad4e3.

Единственный process path — `orchestrator.agent_runtime.AgentGraphRuntime`; `AgentWorkflowRun` добавляет revision, history, definition binding и budgets к общей базовой модели WorkflowRun. Публичные deep-copy snapshots и локальный lock защищают rejected/concurrent actions. Рабочая копия действия отделяет изменяемые контейнеры без повторного копирования принятых payload; возврат полной history всё ещё требует растущих затрат. Generic runtime не читает Task Manager и не делает ready/claim; caller передаёт актуальную definition. Состояние и история только в памяти. [Контракт runtime](architecture/agent-runtime-contract.md), [AgentPreparation](architecture/agent-preparation.md), [AgentExecution](architecture/agent-execution.md).

[Workflow Run](architecture/workflow-run.md) принимает явные results, приостанавливает текущий узел через WaitState и отдельно принимает response через resume_wait. AgentPreparation связывает Context → Analysis → Planning → Review → Package → Ready с Task Manager и Artifact Repository без claim. Исполнение требует ready/preflight/claim. Многосессионность/checkpoints/автоматическое восстановление остаются [будущей функцией](architecture/runtime-coordination.md). Исторические TASK-0003–0004 и TASK-0015 не переоткрываются из-за удаления прежнего API.

Граница хранения закреплена в [контракте](architecture/state-and-storage.md), Graph/Node/Artifact/WorkflowRun — в [общих контрактах графа](architecture/graph-runtime-contract.md). TASK-0003–TASK-0004 завершены. TASK-0014 прошла независимый Luna High аудит, исправления и delta-проверку без новых замечаний; принята и завершена (version 21). TASK-0015 реализует Context → Analysis → Planning → Review → Package → Ready, structured contracts, waits/blockers, ограниченные revisions и реальные ready guards; принята пользователем и завершена (version 18). Общей транзакции runtime/files/Task Manager нет: pending sync запрещает следующий шаг. Смысловые envelopes предоставляет агент; source revision проверяется execution preflight. Callback-адаптеры подготовки больше не используются; встроенного LLM в ядре нет.

AgentExecution/preflight и work units реализованы без callback dispatch; TASK-0017 добавляет explicit execution gates, immutable evidence, readiness и acceptance package, но не автоматическую сквозную маршрутизацию и синхронизацию с внешними трекерами. Полный устанавливаемый пакет ядра не собран. Последовательный [backlog v1](plans/2026-09-16-orchestrator-roadmap-backlog-design.md): TASK-0002–TASK-0004 и TASK-0014 завершены, TASK-0015 принята пользователем и завершена (version 18), TASK-0016 completed v19; TASK-0017 completed v27; TASK-0019–TASK-0022 остаются `created` (TASK-0019–0022 уточнены под миграцию); необязательная TASK-0018 не блокирует локальный v1. TASK-0023 завершена (version 18); TASK-0024 принята пользователем и completed; внутреннее разделение пакета не меняет process runtime. Независимый аудит TASK-0014 не является аудитом новой TASK-0015.

## Проверки

Последний полный набор TASK-0034 с real pinned Graphify fixture: root — 148 tests (147 passed, 1 Windows file-symlink skip), onboarding — 19 (18 passed, 1 Windows skip), Task Manager — 73/73. Всего 240, 238 passed, 2 skipped, 0 failures. Общие contracts — 7, agent runtime — 19, agent preparation — 28; callback-only suites удалены, предметные guards перенесены. Публичные snapshots изолированы; benchmark 100 вложенных результатов около 30 KiB: 17,5376 → 6,6959 s и peak 24,886 → 20,160 MiB под tracemalloc, один локальный замер, не гарантия latency. [Отчёт](reports/2026-09-18-task-0034-callback-removal.md). Данные последующих абзацев — исторические проверки отдельных этапов до удаления callback-пути.

Последний TASK-0017 root прогон: 151 tests, 149 passed, 2 skipped, 0 failures; включая 3 gate lifecycle tests, full AgentExecution/Preparation/Runtime/Knowledge regressions и Windows symlink skips. Compileall успешен; Task Manager/Onboarding suite и публичный validate проверены отдельно перед приёмкой кандидата. [Отчёт TASK-0017](reports/2026-09-18-task-0017-execution-gates-v1.md). Real Graphify E2E в этом self-check не заявляется; knowledge candidate явно помечен advisory/not_required.

Последний полный набор TASK-0030 с real provider env: root — 116 (115 passed, 1 Windows file-symlink skip), onboarding — 19 (18 passed, 1 Windows skip), Task Manager — 73/73. Всего 208, 206 passed, 2 skipped, 0 failures. Knowledge — 21 tests, включая real Graphify; guide исполнен, initial load/query/restart проверены. Compileall и diff check успешны; Task Manager/Onboarding и obsolete не изменены. [Отчёт](reports/2026-09-18-project-knowledge-service-v1.md). Это не полный внешний Agent execution E2E.

Последний полный набор TASK-0029: root — 94 tests (93 passed, 1 Windows file-symlink skip), onboarding — 19 (18 passed, 1 Windows skip), Task Manager — 73/73. Всего 186, 184 passed, 2 skipped, 0 failures. AgentPreparation — 23 новых tests, legacy preparation — 18/18; исполняемый guide и compileall успешны. Пакеты Task Manager/Onboarding не изменены; live health_check=[] после регистрации кандидата. [Отчёт и границы](reports/2026-09-18-agent-preparation-v1.md). Это не Graphify или полный внешний Agent E2E.

Последний полный набор TASK-0028: root — 71 tests (70 passed, 1 Windows file-symlink skip), onboarding — 19 (18 passed, 1 Windows skip), Task Manager — 73/73. Всего 163, 161 passed, 2 skipped, 0 failures. Agent Runtime — 19 новых предметных tests, legacy suites сохранены; Python-пример нового гайда исполнен, compileall успешен. [Результаты и ревизия кандидата](reports/2026-09-17-agent-runtime-v1.md). Это не Graphify или end-to-end Agent проверка.

Повторный baseline TASK-0027 от 2026-09-17: root — 52 теста (51 passed, 1 Windows file-symlink skip), onboarding — 19 (18 passed, 1 Windows symlink skip), Task Manager — 73/73. Итого 144 tests, 142 passed, 2 skipped, 0 failures. Публичный validate после создания задачи: `ok: true`, `result: []`. Это проверка существующего кода, а не нового agent API или Graphify. [Подробная оценка и границы проверок](reports/2026-09-17-agent-centric-graphify-assessment.md).

```powershell
python -m unittest discover -s packages/onboarding/tests -v
python -m unittest discover -s packages/task-manager/tests -v
```

Последний полный прогон TASK-0015: корневой Orchestrator — 52 теста, 51 прошёл и 1 пропущен из-за Windows-привилегии file symlink; Preparation Workflow — 18/18 внутри этого набора; Artifact Repository — 19 (18 прошли, 1 тот же skip), root/entry junction checks проходят. Onboarding — 19 (18 прошли, 1 Windows symlink skip); Task Manager — 73/73. Compileall и diff check успешны. Live `orchestrator-tasks --project . validate` должен возвращать `ok: true`. Подробности: [repository](reports/2026-09-17-artifact-repository-v1.md), [preparation](reports/2026-09-17-preparation-workflow.md). MCP benchmark ранее: p50 0.350 ms, p95 0.551 ms, startup 124.702 ms.
