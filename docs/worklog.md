# Журнал работ

## 2026-09-18 — TASK-0016 принята; создана TASK-0031

- Пользователь явно принял AgentExecution candidate. Через публичный `accept_task` TASK-0016 завершена атомарно: `completed v19`, candidate revision `agent-execution-v1:625b6d2c66ef06541fe732d247ea14f3370e23ed16ad9bdeb5447989ccbdf3d0`, completion decision `user-acceptance:2026-09-18:TASK-0016`; active run/claim отсутствуют, `health_check=[]`.
- По отдельному запросу создана TASK-0031 `HIGH: единый Project Knowledge Graph на базе Graphify`, статус `created v1`. Задача не запускалась: нет plan, claim, run или подготовки. В карточке закреплены требования одного графа для кода и долговечной документации, исключения временного Task Context и запрета отдельного documentation graph. Отдельного поля priority в текущем публичном Task Manager нет, поэтому высокий приоритет зафиксирован в title/constraints.
- Новая задача не меняет код, граф, Task Manager schema/API или `obsolete/`; дальнейшее выполнение начнётся только отдельным явным запуском TASK-0031.

## 2026-09-18 — TASK-0030 принята; TASK-0016 AgentExecution

- Пользователь принял Knowledge Service и разрешил продолжить миграцию. Исторический immutable acceptance package и 10 file hashes сверены до новых code changes; публичный accept_task завершил TASK-0030, completed v18, task_completed подтверждён, health_check=[].
- Через публичный API уточнены TASK-0016–0017 и TASK-0019–0022 под agent-centric migration, original_request сохранён. TASK-0016 прошла действительные plan/self-review/package/ready/claim до реализации, active v10. Task Manager code/schema/API/resources/guards, Onboarding и obsolete не менялись.
- Добавлены AgentExecution и read-only ExecutionPreflight: immutable/source guards до claim, explicit work units/dependencies, фактическая code delta, claim/lease, pauses/reclaim, terminal failure, handoff к будущим gates и cleanup без rollback файлов. Общий TaskEffectSync выделен из AgentPreparation; 23 preparation tests сохранены. Смысловую работу выполняет агент, не callbacks.
- Проверки обнаружили преждевременный checkpoint guard на собственных изменениях и handoff lost-response state; guards исправлены с регрессиями. Known pending допускает явный abandon/cancel; unknown требует exact public-history reconciliation без replay.
- Полный набор 241 tests: 239 passed/2 Windows skips/0 failures, реальный Graphify integration выполнен. AgentExecution — 33 tests. Новый guide исполнен в temp project; compileall/diff check успешны. Independent audit не проводился.
- Выполнен manual Graphify full rebuild после final code: 51 files, 989 raw nodes/3324 edges, AgentExecution query ok/fresh; obsolete исключён. Созданы русский контракт, guide, подробный отчёт; status/roadmap/navigation и исторические source banners обновлены.
- Публичная регистрация кандидата: TASK-0016 awaiting_acceptance v18, без active run/claim; TASK-0027 preparing v13, health_check=[]. Финальная сверка: TASK-0017/0019/0021 created definition v2, TASK-0020/0022 created definition v4. Проверен 461 local Markdown target, missing=0 (без проверки anchors). Full gates, knowledge workflow integration, portable delivery/E2E, durable checkpoints и memory не объявлены реализованными.
- Brainstorming использован для ограничения следующего slice утверждённым дизайном, Task Manager skill — для lifecycle без SQL. Новая приёмка за пользователя не зарегистрирована. Commit/PR не создавались; чужие изменения сохранены.

## 2026-09-18 — TASK-0029 принята; TASK-0030 Knowledge Service

- Пользователь принял AgentPreparation сообщением «принято. продолжай дальше». Исторические candidate hashes сверены до новых exports; публичный accept_task завершил TASK-0029, completed v18, без active run/claim, health_check=[].
- Следующий срез прошёл plan/self-review/package/ready/claim до реализации. Добавлены ProjectKnowledgeService, closed corpus policy/SHA-256 snapshot, explicit full-rebuild refresh, immutable graph/index, atomic current pointer и query_graph-only Graphify MCP adapter. Task Manager, Onboarding и obsolete не менялись; нового global install/hooks/config или semantic passes нет.
- Реальные Graphify tests выявили .json path requirement, text errors, AST placeholders/external imports; adapter/validation актуализированы. В core Artifact Repository добавлены bounded get/verify и manifest reads с регрессией, public old calls сохранены.
- Final initial-load/refresh текущего проекта: 47 files, 882 raw nodes/2890 edges; query ok/fresh. Python/TSX/Vue/Unicode/rename/delete/restart проверены реальным graphifyy 0.9.63 из отдельной .tmp среды. Полный набор 208 tests, 206 passed/2 Windows skips, 0 failures; реальный provider test не skipped. Guide и compileall успешны.
- Созданы [контракт](architecture/project-knowledge-service.md), [guide](guides/project-knowledge.md), [подробный отчёт/оценка/миграция](reports/2026-09-18-project-knowledge-service-v1.md); исправлены status/roadmap/навигация и устаревшее отсутствие Graphify в agent guides. Brainstorming помог сохранить одобренные границы semantic/deterministic и code/memory; self-review не независимый аудит.
- TASK-0030 передаётся на отдельную пользовательскую приёмку, общая TASK-0027 остаётся preparing. Installed Agent skill, agent execution, host facade, checkpoints и portable delivery не заявляются реализованными. Code commit/PR не создавался; unrelated dirty changes сохранены.
- Фактическая регистрация завершена: TASK-0030 awaiting_acceptance v17, active run/claim отсутствуют, immutable acceptance package v1 опубликован; TASK-0027 preparing v12. Health_check=[], knowledge status=fresh. Проверены 430 local Markdown targets, missing=0, anchors отдельно нет.

## 2026-09-18 — TASK-0027: реальный Graphify upstream probe

- Проверены официальные PyPI metadata и upstream source; graphifyy[mcp]==0.9.63 установлен only-binary в отдельную .tmp среду после разрешённого сетевого доступа. Основная .venv/Task Manager не менялись; global install/hooks/config, модели и semantic pass не запускались.
- [Воспроизводимый probe](../scripts/graphify_probe.py) прошёл на Windows: 10 nodes/12 edges, Python/TSX/Vue/Unicode sources, code-only skip документа, real MCP handshake/query/stats, rename/delete очищают прежние sources. Credentials отсутствуют в дочерней среде, query logging отключён. Synthetic fixtures удалены самим probe, среда сохранена.
- Зафиксированы реальные SDK 2.x, nested output layout, чтение home locations при CLI version check и опасная для wrapper поверхность project_path/PR tools. [Отчёт](reports/2026-09-18-graphify-upstream-probe.md) и [dependency snapshot](../requirements/graphify-probe-windows-py312.txt) отличают upstream evidence от ещё отсутствующих production adapter/service/freshness/initial load.
- Реальный probe payload опубликован ArtifactRepository и зарегистрирован через публичный Task Manager как evidence общей миграции: TASK-0027 preparing v11, health_check=[].
- Финальный root regression повторно 94 tests (93 pass/1 skip); compileall включает probe. Проверены 307 local Markdown targets, missing=0 (без проверки anchors), git diff --check успешен.

## 2026-09-18 — TASK-0029: агентная подготовка, TASK-0028 принята

- Пользователь принял предъявленный runtime-срез и разрешил продолжение. Хеши кандидата TASK-0028 проверены до следующего изменения; accept_task завершил её v18, проверены task_completed и health_check=[]. Приёмка не распространяется на новые результаты.
- TASK-0029 прошла реальный план, self-review, Execution Package, ready и claim до кодовых изменений. Реализован AgentPreparation без reasoning callbacks; validation/publication/projection/sync вынесены в общие primitives для нового и legacy пути.
- Добавлены guards версий, отдельный resume с сохранением ответа, фиксированный root, pending barrier и conservative unknown outcome reconciliation через публичную историю. Immutable Plan/Review/Package и проекция проверяются перед ready и повторно во время sync. Task Manager и Onboarding не менялись.
- 23 новых tests, 18 прежних preparation сохранены. Полный набор: root 94 (93 pass/1 skip), onboarding 19 (18 pass/1 skip), Task Manager 73/73; всего 186/184/2, без ошибок. Новый Python guide исполнен, compileall и diff check успешны.
- [Контракт](architecture/agent-preparation.md), [guide](guides/agent-preparation.md), [подробный отчёт/матрица миграции](reports/2026-09-18-agent-preparation-v1.md) актуализированы. Self-review не является независимым аудитом. Checkpoints, installed Agent skill, Graphify и execution не заявляются реализованными.
- Реальные implementation/testing/review/documentation/readiness и immutable acceptance package зарегистрированы через публичный API. TASK-0029 awaiting_acceptance v17, без active run/claim; TASK-0027 preparing v10, общая миграция не completed. Health_check=[].

## 2026-09-17 — TASK-0028: первый agent-facing process API

- Пользователь подтвердил поэтапный дизайн TASK-0027. Уточнение записано публичным API, ожидание снято; общий дизайн зафиксирован отдельным коммитом f881dda без остальных изменений. Связанные worktree/writing-plans skills недоступны; составлены локальный предметный plan, реальный самостоятельный review и Execution Package, TASK-0028 прошла ready и claim перед изменением кода.
- Добавлен AgentGraphRuntime без callback dispatcher: explicit results, allowed actions, process revision, task-definition binding, wait response/resolution, budgets и in-memory history. Общая structural validation переиспользована legacy runtime. Старые подписи/сериализация/подготовка сохранены; Task Manager и onboarding не изменены.
- Написаны [контракт](architecture/agent-runtime-contract.md), [runnable guide](guides/agent-runtime.md), [отчёт с ревизией](reports/2026-09-17-agent-runtime-v1.md), актуализированы README/roadmap/project status и прежние миграционные предупреждения. Исходная оценка сохранена как исторический baseline, не переписана задним числом.
- Проверки: root 71 (70 passed, 1 Windows skip), onboarding 19 (18 passed, 1 Windows skip), Task Manager 73 passed; всего 163, 161 passed, 2 skipped, 0 failures. Новый runtime 19/19, simultaneous submit barrier test и публичная Task Manager isolation/definition/guard integration проходят. Guide исполнен, compileall успешен.
- Persistence, agent skills, новый preparation sync, knowledge service/Graphify и сквозное исполнение не реализованы в этом срезе. Самостоятельный code review не выдается за независимый аудит; подтверждение дизайна не используется как приёмка результата.
- Пакет приёмки опубликован существующим ArtifactRepository, свидетельства зарегистрированы публичным Task Manager API. TASK-0028 awaiting_acceptance v17, без active run/claim; TASK-0027 preparing v9. Live validate и health_check без нарушений. Проверены 255 local Markdown targets (anchors отдельно нет), отсутствующих файлов нет; diff check успешен с LF/CRLF предупреждениями.

## 2026-09-17 — TASK-0027: агент-центричное направление и оценка Graphify

- Изучены два новых пользовательских решения, действующие контракты, roadmap/backlog и корневой код. Зафиксировано уточнение пользователя: текущий Task Manager с SQLite не изменяется; файловая карточка/TaskML и обязательная specification не возвращаются.
- Созданы [русское распределение ответственности](architecture/agent-centric-orchestration.md), [направление Project Knowledge Service](architecture/project-knowledge-service.md), [оценка состояния и нюансов](reports/2026-09-17-agent-centric-graphify-assessment.md) и [предложенный поэтапный дизайн](plans/2026-09-17-agent-centric-graphify-migration-design.md). Обновлены roadmap, навигация, project status и миграционные границы старых контрактов/гайдов. Старый backlog и PKM master-spec помечены как исходники прежнего направления.
- Brainstorming использован для альтернатив и проверки дизайна перед behavioral implementation. Принятое направление отделено от конкретных предложенных API; новый процессный путь, skills и Graphify пока не реализованы. Пользовательские исходники, production Python-код, ресурсы/схема/API Task Manager и historical artifacts не переписывались.
- Baseline: root 52 tests (51 passed, 1 Windows skip), onboarding 19 (18 passed, 1 Windows skip), Task Manager 73 passed; всего 144, 142 passed, 2 skipped, 0 failures. Публичный validate после создания TASK-0027: ok, без нарушений. Upstream Graphify проверен по первичной документации; не установлен, индекс не строился.
- Состояние работы ведётся через публичный Task Manager API, не прямой SQL. TASK-0027 ожидает подтверждения дизайна: awaiting_input v6, без active run/claim, health_check без нарушений. TASK-0016–0022 не уточнялись и не закрывались; новой пользовательской приёмки не зарегистрировано. Перед кодовой миграцией требуется подтверждение предложенного дизайна и конкретного Graphify upstream/корпуса.
- Проверены 217 локальных Markdown-ссылок затронутых файлов, отсутствующих целей нет; anchors отдельно не проверялись. Git diff check успешен с предупреждениями LF/CRLF. Production-код трёх областей (`orchestrator`, `packages/onboarding`, `packages/task-manager`) не изменён.

## 2026-09-17 — TASK-0015: пользовательская приёмка

- Пользователь подтвердил показанный отчёт TASK-0015 сообщением «Подтверждаю». SHA-256 workflow, Graph Runtime и integration tests повторно сверены с показанной ревизией; изменений кандидата нет.
- Публичный атомарный accept зарегистрировал acceptance=approved и завершил TASK-0015: `awaiting_acceptance` v17 → `completed` v18. Активных run/claim нет; [основание приёмки](reports/2026-09-17-preparation-workflow.md#user-acceptance).
- Актуализированы отчёт, контракт, guide, дизайн, README, project status и roadmap. Новое исполнение TASK-0016 в рамках этой приёмки не запускалось.

## 2026-09-17 — TASK-0014: Artifact Repository v1

- Реализован независимый `orchestrator.artifact_repository` с публичными `ArtifactRepository`, `ArtifactRecord`, `StoredArtifact` и `ArtifactError`; уникальность определяется тройкой `ref + role + version`.
- Payload и JSON-манифест хранятся под `.orchestrator/artifacts/`; после аудита публикация готовит оба файла со `fsync` во staging и выполняет единый rename всей версии; существующие версии не перезаписываются, чтение повторно проверяет размер и SHA-256.
- Task Manager и SQLite не импортируются и не используются; Task Manager остаётся владельцем lifecycle и хранит только ссылки/метаданные. Локальное runtime-хранилище добавлено в `.gitignore`.
- Добавлены 9 предметных тестов и русский [интеграционный guide](guides/artifact-repository.md); обновлены контракт хранения, Graph Runtime boundary, Task Manager boundary, README, roadmap и project status.
- Реализация подготовлена к пользовательской приёмке; итоговые команды и хеш ревизии указаны в [отчёте TASK-0014](reports/2026-09-17-artifact-repository-v1.md).

## 2026-09-17 — TASK-0014: независимый Luna High аудит и регрессии

- Pascal (`gpt-5.6-luna`, High) выполнил read-only аудит кода, тестов и документации, fault injection, Windows junction и plan-проекцию через публичный Task Manager API. Выявлены два P1, пять P2 и неточность evidence P3.
- Исправлены root/entry reparse boundary, атомарность полной версии и очистка staging, manifest validation, структурированные IO-ошибки, Windows-safe identifiers/case aliases и несовместимая инструкция регистрации plan path.
- Добавлены 10 регрессий: repository — 19 тестов (18 passed, 1 expected Windows file-symlink skip), корень — 34 (33 passed, 1 тот же skip), Task Manager — 73/73, Onboarding — 18 passed + 1 expected skip, compileall успешен. Pascal провёл delta-проверку: новых замечаний нет. По условному разрешению пользователя TASK-0014 принята и завершена через публичный API, version 21.

## 2026-09-17 — TASK-0015: граф подготовки до ready

- После завершения зависимостей подготовлены и зарегистрированы plan, реальное review плана основным агентом и Execution Package; задача исполнена через claim/отдельный run-ref, без прямого SQLite.
- Добавлен Preparation Workflow поверх Graph Runtime: четыре внешних адаптера, структурные контракты, immutable артефакты, plan projection, binding review/package, реальные guards до ready. Встроенный LLM/PKM и автоматическое исполнение не добавлены.
- Реализованы waits/blockers, ограниченные context/review циклы и явная pending-синхронизация без повторного planner/reviewer. Конфликт версии требует caller reconcile, definition/artifact changes отвергаются. Посторонний plan не перезаписывается.
- Добавлены 18 integration tests; полный прогон: корень 52 (51 passed, 1 Windows skip), Task Manager 73/73, Onboarding 19 (18 passed, 1 Windows skip), compileall/diff check успешны.
- Обновлены русские [контракт](architecture/preparation-workflow.md), [guide](guides/preparation-workflow.md), архитектурные границы, roadmap/status и пометки импортированных исходников; [отчёт](reports/2026-09-17-preparation-workflow.md). TASK-0015 переведена публичным API в `awaiting_acceptance`, version 17; run закрыт, claim освобождён. Live validate чистый, проверены 178 локальных ссылок в 37 документах. Независимый Luna аудит repository не распространяется на TASK-0015.

## 2026-09-17 — TASK-0003: минимальный in-memory Workflow Runtime

- Реализован независимый `orchestrator.workflow_runtime` для одного графа и одной real-time сессии: immutable Graph/Node contract, in-memory WorkflowRun, один узел на `step`, terminal outcomes, pause/resume и cancel.
- Добавлены структурированные ошибки и проверки `run_not_found`, `invalid_state`, `node_mismatch`, `unknown_outcome`, `contract_violation`, `stale_wait`, `blocked` и `execution_failure`; Task Manager и SQLite не затрагиваются.
- Добавлены 6 предметных сценариев runtime; корневой набор — 11/11. Архитектурные статусы и гайды обновлены; [отчёт TASK-0003](reports/2026-09-17-workflow-runtime-v1.md).
- Задача подготовлена через публичный Task Manager API и переведена в `awaiting_acceptance` (version 16) без автоматического закрытия; ожидается пользовательское утверждение.

## 2026-09-17 — TASK-0003: исправления после независимого аудита

- Отдельный read-only агент на `gpt-5.6-terra High` подтвердил отсутствие P0, но выявил P1/P2/P3 в атомарности `resume`, возобновлении `blocked`, глубокой изоляции данных, загрузке графа, валидации артефактов и согласованности API-документации.
- Все замечания исправлены в `orchestrator/workflow_runtime.py`; добавлены регрессионные тесты на 10 runtime-сценариев, включая `resume_blocked`, повтор после невалидного resume, malformed/duplicate nodes и Artifact contract.
- Обновлены контракт Graph Runtime, дизайн, гайды и отчёт проверки. Полный набор: Orchestrator 15/15, Task Manager 73/73, Onboarding 19 (1 ожидаемый Windows skip), `compileall`, `git diff --check` и live `validate` прошли.
- Новая ревизия принята через публичный Task Manager API: TASK-0003 завершена, version 22.

## 2026-09-17 — TASK-0004: проверка и документация Workflow Runtime

- TASK-0004 запущена через публичный Task Manager API с отдельным run-ref; зарегистрированы plan, plan review и Execution Package.
- Добавлен русскоязычный [пользовательский guide Workflow Runtime](guides/workflow-runtime.md) с запуском, pause/resume, `resume_blocked`, отменой и границами Task Manager.
- Актуализированы навигация `docs/README.md`, project status, roadmap, onboarding guide, архитектура хранения и Task Manager boundary; устаревшие утверждения о нереализованном Graph Runtime удалены.
- Подтверждены предметные тесты runtime и полный набор проверок: Orchestrator 15/15, Task Manager 73/73, Onboarding 19 (1 ожидаемый Windows skip), compileall, diff check и live validate.

## 2026-09-17 — TASK-0026: полный сценарный аудит и исправления

- Отдельный агент провёл read-only аудит Task Manager от создания до архивации, включая MCP lifecycle, прямой API, изоляцию проектов, backup/restore и onboarding.
- Исправлены строгая MCP schema validation, lifecycle JSON-RPC, object-shaped `structuredContent`, типовые ошибки direct API, fingerprint `event_context` и диагностика blocker payload.
- Обновлены контракт, usage, переносимый skill, архитектурный план и onboarding-разбор; добавлен [полный отчёт аудита](reports/2026-09-17-task-manager-full-audit-fixes.md).
- Task Manager: 73 теста; Onboarding: 19 тестов, 1 ожидаемый Windows skip; корневой Orchestrator — 5 тестов; `validate` чистый; свежие wheel пересобраны и проверены изолированно. TASK-0026 закрыта атомарной пользовательской приёмкой через публичный API.

## 2026-09-17 — TASK-0026: усиление skill, onboarding и Windows stdio

- По результатам аудита обновлён пакетный Task Manager skill: MCP stdio выбран основным интерфейсом внешнего агента, прямой Python API — для in-process оркестратора, CLI — fallback.
- Onboarding теперь проверяет MCP entry point подключённого ядра, предоставляет `check-task-manager` с реальным handshake/health check и `mcp-config` для явной генерации локального host-neutral конфига с выбранным Python.
- Глобальные настройки Codex/MCP-хоста не изменяются автоматически; конфигурация ограничена целевым проектом.
- MCP stdio перенастраивает UTF-8 для входа и выхода до чтения сообщений; добавлены регрессии для Unicode ввода и `--help` на legacy Windows code page.
- Проверки: Onboarding — 19 тестов, 18 прошли и 1 пропущен из-за symlink на Windows; Task Manager — 66/66. Результаты сведены в [отчёт](reports/2026-09-17-task-manager-onboarding-mcp-hardening.md).

## 2026-09-17 — TASK-0026: реализация MCP stdio-адаптера

- Создана задача на MCP-адаптер Task Manager. Пользователь согласовал архитектуру: один общий переиспользуемый пакет, локальный stdio-транспорт и отдельный процесс на каждый проект с фиксированным `project_root`.
- Решение зарегистрировано в карточке TASK-0026 через `record_user_decision`; plan привязан к задаче. Раздельные project root и SQLite-базы, отсутствие прямого SQL/дублирования guards и CLI fallback закреплены как ограничения.
- Реализованы `task_mcp.py`, entry point `orchestrator-task-manager-mcp`, 35 инструментов, lifecycle JSON-RPC, структурированные ошибки, fixed root и ограничение файловых путей. HTTP daemon, общий мульти-проектный процесс, кэш и пакетные мутации в первый срез не входят.
- Полный MCP subprocess-lifecycle, изоляция проектов, перезапуск и ошибки проверены. Task Manager: 65 тестов; ядро: 5; wheel с Python -S: WHEEL_MCP_ISOLATION_OK; benchmark 100 вызовов: p50 0.350 ms, p95 0.551 ms, startup 124.702 ms. [Архитектурный план и результаты](plans/2026-09-17-task-manager-mcp-adapter-design.md).
- TASK-0026 подготовлена к пользовательской приёмке; реализация не завершает задачу автоматически.
- Итоговый [отчёт](reports/2026-09-17-task-manager-mcp-adapter.md) добавлен отдельно от плана; конкретный GUI-хост Codex ещё не подключался.

## 2026-09-17 — TASK-0025: исправление export после аудита Luna

- По разрешению пользователя исправлен вызов отсутствующего service.export; parser/dispatch используют единый реестр export → export_state, backup → backup, restore → restore.
- Добавлены три регрессии: успешный неизменяющий экспорт, структурированные ошибки назначения и CLI backup/restore на временном проекте. 60 тестов Task Manager и 5 тестов ядра прошли; новый wheel проверен с Python -S без исходного пакета, живой validate чистый.
- Обновлены ресурсы пакета, README и снимок проекта; [отчёт](reports/2026-09-17-task-manager-cli-export-fix.md) отделяет исправление от рекомендаций. На момент этого исторического среза MCP ещё был рекомендацией; последующая TASK-0026 реализовала согласованный stdio-адаптер.
- Результат подлежит пользовательской приёмке; разрешение исправить ошибку не считается приёмкой результата. TASK-0024 не завершалась автоматически.
- TASK-0025 переведена через публичный API в awaiting_acceptance, version 17; запуск и claim закрыты, свидетельства зарегистрированы, user_decisions пустой. Финальный health_check живого проекта — без нарушений.

## 2026-09-17 — TASK-0024: модульная структура Task Manager

- Пользователь согласовал разделение после аудита; [дизайн](plans/2026-09-16-task-manager-modularization-design.md) и plan зарегистрированы через публичный API. Существующие изменения TASK-0023 сохранены, отдельный коммит не создавался.
- Выделены contracts, migrations, repository, service, storage_transfer и diagnostics. Фасад task_manager сохраняет старые классы и константы; сервис не выполняет SQL и не вызывает приватные методы репозитория. Единый жизненный цикл и guards сохранены.
- Экспорт и диагностика используют read_transaction с BEGIN DEFERRED и query_only; restore запускает миграции временной копии через самостоятельный вход. Схема SQLite остаётся версии 5, зависимостей не добавлено.
- Проверены 57 тестов Task Manager и 5 тестов потребителя, прежние импорты и снимок API, AST 50 непереписанных методов, изолированный wheel с Python -S и рабочий validate. Парные замеры не выявили выраженного общего замедления, ускорение не заявляется.
- Архитектура поставляется внутри пакета; обновлены контракт, гайды, снимок проекта и roadmap. [Отчёт](reports/2026-09-17-task-manager-modularization.md) содержит условия, результаты и ограничения проверок. Результат подлежит отдельной пользовательской приёмке.
- TASK-0024 переведена в awaiting_acceptance с закрытым запуском и без пользовательской приёмки. При финальной сверке TASK-0023 уже completed, version 18, с отдельным событием приёмки; этот этап не выполнял её завершение. Снимок проекта исправлен по публичному API.

## 2026-09-16 — TASK-0023: надёжность и агентский интерфейс Task Manager

- Пользователь после аудита явно разрешил дополнительный срез для стабильной и быстрой работы агента; создана TASK-0023 через публичный API, подготовлены [дизайн](plans/2026-09-16-task-manager-hardening-design.md) и plan, выполнены ready/claim с сохранением guards.
- Реализованы потоковое SHA-256, единый UTC, структурный архив до LIMIT, SQL summary, согласованный экспорт и ускоренная read-only диагностика. Файловые ошибки дают TaskError, временные файлы уникальны; restore мигрирует staged-копию, создаёт консистентный backup и сохраняет исходный .pre-restore при восстановлении из него. Повтор purge работает после удаления карточки.
- Добавлены атомарный accept_task и CLI защищённых операций с expected-version, JSON-ошибками, подсказками, api и табличным чтением. Обновлены контракт, гайд, переносимый skill и README; устранён дублированный абзац README. Python TypeError сигнатур не заменён.
- Проверки: Task Manager — 52/52, корневой Orchestrator — 5/5; рабочий validate — ok; wheel собран и проверен без ядра с Python -S. Стандартный валидатор skill недоступен из-за отсутствия PyYAML; frontmatter и ссылки проверены напрямую. Документация и результаты сведены в [отчёте](reports/2026-09-16-task-manager-hardening.md).
- Замеры на 100/500/1000 задач: validate на 1000 ускорился с 61.4 до 14.1 мс (медиана), страница — около 1 мс, summary — 3.3 мс. Другие операции не объявляются ускоренными; сохранены durable commit и ограничения нагрузки.
- Уточнён исходный аудит: текст archive внутри JSON-строки экранируется; регрессия фильтра связана с сериализацией и LIMIT. По публичной карточке подтверждено, что TASK-0002 уже completed с явной приёмкой; устаревший project-status исправлен. Это не утверждение о реализации runtime.
- TASK-0023 переведена в awaiting_acceptance (version 17) с implementation/review/testing/documentation/readiness/acceptance_package и закрытой ссылкой на текущую Codex-сессию; 17 событий, validate — ok. Разрешение реализации не записывается как финальная приёмка.

## 2026-09-16 — TASK-0002: кандидат контрактов Graph Runtime

- На основании действующих материалов `docs/architecture/`, `docs/graph/` и `docs/development/` подготовлен кандидат `docs/architecture/graph-runtime-contract.md`.
- Зафиксированы Graph, Node, Artifact, WorkflowRun, NodeResult, WaitState, минимальный API движка, владельцы данных, маршрутизация и ограничения real-time v1 без многосессионной координации.
- TASK-0002 прошла `created → preparing → ready → active → awaiting_acceptance`; plan, review, execution package, проверка ссылок и `git diff --check` зарегистрированы через Task Manager. Пользовательская приёмка ещё не записана.

## 2026-09-16 — Task Tracker Adapter отложен на будущее

- TASK-0018 сохранена в Task Manager со статусом `created`, но явно помечена как будущая необязательная интеграция.
- Зависимость TASK-0022 от TASK-0018 снята; локальный v1 проверяется без внешнего трекера. Исходные материалы `docs/graph/05–07` сохранены для последующего этапа.

## 2026-09-15 — принято решение исключить отдельную спецификацию задачи

- Пользователь подтвердил упрощение workflow: отдельный `.orchestrator/tasks/TASK-xxxx/specification.md` исключается из обязательного процесса и остаётся только legacy-артефактом для совместимости.
- Каноническое определение задачи остаётся в структурированной карточке Task Manager; `docs/plans/` хранит архитектурный дизайн, а `plan.md` — план реализации.
- Решение зафиксировано в [дизайне удаления спецификации](plans/2026-09-15-remove-task-specification-design.md); реализация выполнена в `TASK-0012`.

## 2026-09-15 — полный цикл TASK-0012: спецификация исключена из ready guard

- `TASK-0012` выполнена и закрыта через полный lifecycle Task Manager.
- `ready_guard` теперь требует карточку задачи, `plan`, `plan_review` и `execution_package`; `specification.md` остаётся только legacy-артефактом для чтения.
- `attach_execution_package` больше не требует `specification_sha256`; старый аргумент поддержан необязательно для совместимости.
- Добавлен тест задачи без specification, обновлены контракт, usage, README, skill и архитектурные документы.

## 2026-09-15 — полный цикл TASK-0013: архивация и физическое удаление задач

- `TASK-0013` выполнена и закрыта через полный lifecycle Task Manager.
- Добавлены `archive_task`, `unarchive_task` и `purge_task`; архив скрывается из списка по умолчанию, а физическое удаление разрешено архивным `completed` и `cancelled` задачам после трёх календарных месяцев с terminal-события.
- Snapshot и события удаляются атомарно, минимальный tombstone сохраняется в `purged_tasks`, ID не переиспользуется. CLI, веб-фильтр архива, экспорт и документация обновлены.
- Добавлена миграция схемы v5 и тесты retention/архивации/удаления; итоговый пакет Task Manager — 30 тестов.

## 2026-09-16 — уточнение purge для завершённых задач

- По подтверждённому требованию пользователя `purge_task` теперь разрешён для архивных задач со статусом `completed` и `cancelled` после истечения трёх календарных месяцев.
- Исправлены guard, предметный тест completed-задачи, контракт, README, usage и дизайн TASK-0013; проверка `cancelled`-сценария сохранена.

## 2026-09-15 — последовательное выполнение TASK-0006–TASK-0011

- `TASK-0006` закрыта: идемпотентность `operation_id`, таблица операций и конфликт отпечатка; 20 тестов.
- `TASK-0007` закрыта: публичные `export_state`, `backup`, `restore`, CLI-команды и безопасный `.pre-restore`; 22 теста.
- `TASK-0008` закрыта: SQL-фильтры, индекс типа и cursor-пагинация; 23 теста.
- `TASK-0009` закрыта: миграция схемы v4 и метаданные событий `actor_ref/source/correlation_id/run_ref`; 24 теста.
- `TASK-0010` закрыта: усиленный read-only `validate` (снимок, статусы, payload, orphan-события, operations); 25 тестов.
- `TASK-0011` закрыта: конкурентные повторы и rollback-тесты; итоговый пакет Task Manager — 27 тестов.
- Для каждой задачи зафиксированы дизайн, specification, plan, review, execution package, readiness и пользовательская приёмка через публичный Task Manager API. Финальные проверки: Orchestrator — 5, Onboarding — 15 (1 skipped на Windows symlink), `validate` — `ok: true`.

## 2026-09-15 — задачи оптимизации Task Manager

- Созданы задачи `TASK-0006`–`TASK-0011` для всех оставшихся рекомендаций аудита: идемпотентность, backup/export/restore, SQL-фильтрация и пагинация, метаданные событий, усиленный `validate` и отказоустойчивые тесты.
- На момент создания все задачи имели статус `created`, критерии приёмки и ограничения; реализация выполнялась последовательно после `TASK-0005`.

## 2026-09-15 — полный цикл TASK-0005: миграции схемы Task Manager

- Создана и закрыта `TASK-0005` через полный lifecycle Task Manager: `preparing → ready → active → awaiting_acceptance → completed`.
- Подготовлены [дизайн миграций](plans/2026-09-15-task-manager-schema-migrations-design.md), specification и plan в `.orchestrator/tasks/TASK-0005/`.
- В `SQLiteTaskRepository` добавлен реестр миграций с базовой миграцией `0 → 1`, транзакционным `BEGIN IMMEDIATE`, сохранением текущей схемы и отказом для неподдерживаемых будущих версий.
- Добавлен тест отказа версии `99` без записи. Проверки: Task Manager — 19 тестов, Orchestrator — 5, Onboarding — 15 (1 пропущен из-за Windows symlink), `validate` — `ok: true`.

## 2026-09-15 — закрытие TASK-0001 и аудит Task Manager

- `TASK-0001` закрыта через полный публичный lifecycle Task Manager: `preparing → ready → active → awaiting_acceptance → completed`. Зафиксированы specification, plan, review, execution package, readiness, пользовательская приёмка и 14 последовательных событий.
- Task Manager: 18 тестов прошли; корневой Orchestrator: 5 тестов прошли; `orchestrator-tasks resources` вернул контракт, usage и пример skill; `orchestrator-tasks --project . validate` вернул `ok: true`.
- Подтверждены текущие свойства: атомарная запись снимка и события, optimistic concurrency через `expected_version`, атомарный claim/lease, SHA-256 guard документов, read-only web-панель и изоляция пакета от ядра.
- На момент аудита ограничения были ожидаемыми для v1: CLI не покрывал все защищённые переходы, миграции схемы и backup/export отсутствовали. Последующие TASK-0005–TASK-0011 закрыли эти пункты; полный Graph Runtime и Executor Loop по-прежнему не входят в пакет.

## 2026-09-15 — актуализация исторических графовых материалов

- Для `TASK-0001` сверены материалы `docs/graph/` и `docs/development/` с действующими решениями SQLite Task Manager и real-time Workflow Runtime.
- Добавлены русскоязычные README для обоих каталогов, ссылки на действующие контракты и явная граница: файловое состояние задач и Executor Loop относятся к историческим/будущим вариантам, а не к v1.
- В отдельных материалах усилены предупреждения о статусе внешнего трекера и фонового Executor Loop. Код, SQLite и `obsolete/` не изменялись.
- Проверки: локальные Markdown-ссылки — `MARKDOWN_LINKS_OK`; `git diff --check` не выявил ошибок, остались только предупреждения о CRLF.

## 2026-09-15 — задачи следующего среза Graph Runtime

- В Task Manager созданы задачи `TASK-0001`–`TASK-0004`: актуализация документации, согласование минимальных контрактов Graph Runtime, реализация in-memory runtime и тестирование с документацией.
- Все задачи созданы через публичный CLI `orchestrator-tasks`, имеют статус `created`, версию `1` и критерии приёмки; прямых записей в SQLite не выполнялось.
- Проверка `orchestrator-tasks --project . validate` завершилась с `ok: true`.

## 2026-09-15 — повторная проверка onboarding текущего проекта

- После переноса wizard в одноразовую инструкцию создан новый preview для self-hosting с `--target . --core .`; устаревшие планы не использовались.
- Первый план получил хеш `d9eae4e887e688aa4f6daed88b7cabda5fc97435e9ce613f847bd2eb41134ee3`, но был отклонён после изменения журнала: отпечаток ядра изменился.
- Финальный план v2 получил хеш `b5fbdc7fd9c17d606d585077f72515d25fd82eff3208a127db16dcd652fc2056`; после явного подтверждения выполнен `apply`, изменений нет: существующие `.orchestrator/project.json` и `.orchestrator/project-context.md` соответствуют текущим ответам.

## 2026-09-15 — выполнение полного сценария первичного onboarding

- Повторный self-hosted preview с хешем `51dbfca4937145ce0a58d10cbfb32133635d7b803d3fd305b7beaa3ba8569d58` подтверждён и применён; изменений нет.
- Task Manager установлен в `.venv` в editable-режиме. Первая команда установки потребовала сетевые build-зависимости и была повторена с `--no-build-isolation`.
- Проверки прошли: импорт `orchestrator_task_manager`, `orchestrator-tasks --help`, `orchestrator-tasks --project . validate` (`ok: true`), корневые тесты — 5, Task Manager — 18, Onboarding — 15 (1 пропущен из-за Windows symlink).
- `validate` создал `.orchestrator/state/tasks.sqlite3`; каталог состояния исключён из Git.

## 2026-09-15 — wizard перенесён в одноразовую инструкцию

- По уточнению пользователя постоянный механизм первичного запуска удалён. Полный wizard-порядок перенесён в `docs/guides/onboarding.md` и явно закреплён в `AGENTS.md` как инструкция первого запуска.
- Onboarding проверяет и добавляет только постоянный Task Manager skill; временный wizard не устанавливается.
- Инструкция сохраняет два подтверждения: сначала конфигурационный plan, затем установка Task Manager. После завершения остаётся только Task Manager skill для повседневной работы.
- Проверка: onboarding — 15 тестов, 14 прошли, 1 пропущен из-за Windows symlink; Orchestrator — 5 тестов; Task Manager — 18 тестов.

## 2026-09-15 — исправление маркеров и устаревших onboarding-планов

- Управляемый блок `.gitignore` теперь использует Git-комментарии `# orchestrator:begin/end`; HTML-комментарии сохранены только для `AGENTS.md`.
- Формат плана повышен до версии 2 и теперь содержит версию onboarding и отпечаток содержимого ядра. `apply` отклоняет старые планы и планы после изменения ядра до первой записи.
- Добавлены тесты на маркеры `.gitignore`, изменение ядра после preview и старую версию плана. Текущий self-hosted проект успешно построил новый plan v2 с 0 изменениями; старый plan v1 отклонён.
- Добавлена миграция legacy-блока `.gitignore` с HTML-маркерами только при точном совпадении его содержимого.
- Проверка: onboarding — 15 тестов, 1 пропущен из-за ограничения Windows на symlink. Документация контракта, гайда и README пакета обновлена.

## 2026-09-15 — аудит качества onboarding

- Self-hosting-прогон признан корректным: preview/apply создали только два ожидаемых файла, повторный preview показал 0 изменений, существующие `AGENTS.md` и `.gitignore` не затронуты.
- Приоритетные улучшения реализации: использовать настоящие комментарии в управляемом блоке `.gitignore` (текущие HTML-маркеры интерпретируются как шаблоны); привязать план к версии/хешу ядра и пакета; усилить транзакционность при аварийном завершении; сохранять права и переводы строк существующих файлов.
- Дополнительные улучшения: строго проверять итоговую конфигурацию, распознавать варианты широких правил `.gitignore`, проверять владение существующим managed-блоком и добавить тесты на повреждённые планы, гонки, кодировки, разрешения и аварийное завершение.
- Рекомендовано отделить безопасный `apply` от явной команды `verify`: не выполнять произвольные `test_commands` автоматически, но проверять конфигурацию, установленные пакеты и команды отдельным подтверждённым шагом.
- Код в рамках аудита не менялся; выводы являются планом улучшений v1, а не утверждением о реализованной функциональности.

## 2026-09-15 — self-hosting текущего репозитория

- В текущем репозитории выполнен onboarding в режиме self-hosted с `--target . --core .`. Старый временный план от 14 сентября с `.graph-orchestrator/` не использовался.
- После подтверждения хеша `65a4369ef9bc978171edb885149cba38a1c434f7e25da7ac0dccbe36679f3f22` созданы только `.orchestrator/project.json` и `.orchestrator/project-context.md`. `AGENTS.md` и `.gitignore` не изменялись; `.orchestrator/state/` остаётся исключённым из Git.
- Повторный `preview` для тех же ответов показал 0 изменений. Проверка: Orchestrator — 5 тестов; Task Manager — 18 тестов; Onboarding — 12 тестов, 1 пропущен из-за ограничения Windows на symlink. Все завершились успешно.

## 2026-09-15 — первый входной срез Request Router → Task Creator

- Реализованы `orchestrator.request_router`, `orchestrator.task_creator` и последовательный фасад `orchestrator.request_flow` на основе существующего контракта `docs/graph/02-request-routing-graph-template.md`.
- Router принимает классификатор-адаптер и проверяет `direct_response`/`managed_work` и тип управляемой задачи. Creator принимает builder-адаптер, возвращает `success`/`needs_input`/`failure`, не создаёт артефакты подготовки и регистрирует задачу только через публичный `TaskManagerService.create_task()`.
- Добавлен русскоязычный [гайд входного потока](guides/request-flow.md); обновлены roadmap, project-status и навигация. LLM-провайдер и правила классификации намеренно не зашиты в ядро, поскольку в исходной спецификации они оставлены открытыми.
- Проверка: `\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 5 тестов; Task Manager — 18 тестов; Onboarding — 12 тестов, 1 пропущен из-за ограничения Windows на symlink. `git diff --check` показывает только предупреждения LF/CRLF.

## 2026-09-15 — сверка графовых наработок перед реализацией

- Изучены материалы `docs/graph/`, `docs/development/` и `docs/context-knowledge/`. Основная цепочка уже описана существующими документами: Request Router → Task Creator → Task Manager → Context → Analysis → Specification → Planning → Plan Review → Execution Package → `ready` → Implementation → Code Review → Testing → Documentation → Final Check → User Acceptance.
- Зафиксировано разделение ответственности: граф управляет переходами и артефактами, узлы выполняют шаги, Task Manager хранит состояние задач, а runtime хранит состояние текущего запуска. Контракты результатов Analysis, Planning, Plan Review, Implementation, Code Review, Testing и Final Check уже находятся в `docs/development/`.
- Обнаружены исторические расхождения импортированных материалов с действующей границей хранения: отдельные документы всё ещё описывают файловое состояние задач и асинхронный Executor Loop. Они остаются исходными материалами; для реализации применяются актуальные русскоязычные архитектурные документы и пакет Task Manager.
- Удалён экспериментальный параллельный контракт графа и его пример/тест, чтобы не создавать второй источник требований. В этом срезе код, SQLite и `obsolete/` не изменялись; функциональные тесты не запускались.

## 2026-09-15 — координация нескольких запусков вынесена в будущую функцию

- По уточнению пользователя проект отдельной runtime-базы, индекса продолжений и блокировок оформлен как самостоятельная [будущая функция](architecture/runtime-coordination.md). Она не реализуется в текущем v1, но сохранена как направление возможного расширения.
- Активные документы Workflow Run, паузы, roadmap, project-status и навигация теперь ссылаются на будущую функцию, не включая её в текущий контракт.
- Проверки кода и Task Manager не требовались: менялась только документация. `obsolete/` и пользовательские данные не изменялись.

## 2026-09-15 — упрощение runtime для агента в реальном времени

- Пользователь подтвердил один последовательный граф в текущей сессии агента. Зафиксировано [новое решение](plans/2026-09-15-realtime-runtime-design.md).
- Переписаны [Workflow Run](architecture/workflow-run.md) и [пауза](architecture/workflow-pause-resume.md): состояние процесса в памяти, структурированные результаты, переходы по графу, ожидание ответа в той же сессии. Возможность отдельной координации нескольких запусков вынесена в [документ будущей функции](architecture/runtime-coordination.md) и сейчас не реализуется.
- Предыдущий проект блокировок сохранён как возможное расширение, а не как часть активного решения. Обновлены граница хранения, roadmap, снимок состояния и указатели исходных материалов.
- Существующие task-claim, lease и guards Task Manager не изменены. Ограничение API возврата от устаревшего ожидания к подготовке сохранено явно; оно не обходится фиктивными хешами. Контрольные точки между сессиями и автоматическое восстановление отложены.
- Проверены 55 локальных ссылок в 15 документах; `git diff --check` прошёл с предупреждениями LF/CRLF. Код, SQLite и `obsolete/` не менялись; функциональные тесты не запускались, поскольку менялась только документация. Этап 3 целиком ещё не завершён.

## 2026-09-15 — подтверждение паузы и кандидат координации runtime

- Пользователь подтвердил сохранение запуска с освобождением claim и новой активацией после ожидания. Обновлены статусы связанных документов; реализации пока нет.
- Созданы [кандидат координации](architecture/runtime-coordination.md) и [варианты хранения](plans/2026-09-15-runtime-coordination-design.md). Рекомендуются отдельная SQLite runtime, транзакционный индекс продолжений и исключительная активация с проверкой поколений результата.
- Защита ограничена одним локальным хранилищем; истечение lease не разрешает повторный старт без проверки остановки. Отмечен недостающий переход Task Manager от устаревшего ожидания исполнения к подготовке — он не обходится фиктивным возвратом в ready.
- Проверены 38 локальных ссылок в восьми документах; `git diff --check` прошёл с предупреждениями LF/CRLF. Код, базы, архив и пользовательские данные не изменены; функциональные тесты не запускались.

## 2026-09-15 — подтверждение последовательного v1 и кандидат протокола ожидания

- Пользователь подтвердил минимальный последовательный Workflow Run; обновлены статусы контракта, дизайна и связанных указателей. Это подтверждение архитектуры, не реализации.
- Сверены текущие методы `release_claim`, `link_workflow_run`, `record_user_decision` и `transition_status`. Подготовлены [кандидат протокола](architecture/workflow-pause-resume.md) и [варианты решения](plans/2026-09-15-pause-resume-design.md).
- Рекомендуется сохранять запуск, завершать активацию и освобождать claim при ожидании; продолжение использует новую активацию. Отмечены обязательные индекс продолжений, проверка остановки исполнителя, привязка ответа к ожиданию и повторный Preflight. Эти компоненты не реализованы; предложение требует подтверждения.
- Проверены 34 локальные ссылки в семи документах; `git diff --check` прошёл с предупреждениями LF/CRLF. Код и состояние задач не изменены, функциональные тесты не запускались.

## 2026-09-15 — кандидат Workflow Run и результата узла

- Изучены шаблон маршрутизации, правила повторного использования подграфов и материалы Executor Loop. Подготовлены [кандидат контракта](architecture/workflow-run.md) и [предложенный дизайн](plans/2026-09-15-workflow-run-design.md); согласование пользователем пока не получено.
- Предложен последовательный v1 с устойчивыми попытками, проверкой результатов и контрольной точкой до следующего узла. Маршрутом владеет граф; неоднозначные побочные эффекты не повторяются вслепую.
- Выявлена открытая граница ожидания: текущий Task Manager требует закрытия активной связи и освобождения claim перед возобновлением задачи. Протокол продолжения будет согласован отдельно без обхода публичного API.
- Обновлены навигация и снимок состояния, в двух исходных документах добавлены ссылки на кандидат. Проверены 24 локальные ссылки в шести документах; `git diff --check` прошёл с предупреждениями LF/CRLF. Runtime не реализован; код, SQLite и архив не изменены; функциональные тесты не запускались.

## 2026-09-15 — согласование состояния и хранения, первый срез этапа 3

- Пользователь подтвердил SQLite как источник истины задач, файловые Specification и Plan и отдельную ответственность будущего Graph Runtime за `.orchestrator/runs/`.
- Созданы [архитектурная граница](architecture/state-and-storage.md) и [решение](plans/2026-09-15-state-and-storage-design.md). Уточнено, что Task Manager регистрирует и проверяет документы, но не создаёт их; текущий Execution Package хранится как метаданные, а не отдельный реализованный репозиторий манифестов.
- В десяти импортированных документах отмечена замена положений о файловом каноническом состоянии. Обновлены навигация, интеграционная граница, roadmap и снимок состояния. Исходные процессные предложения сохранены для следующего согласования.
- Проверка: 40 локальных ссылок в 16 затронутых документах ведут на существующие файлы; `git diff --check` прошёл, только предупреждения LF/CRLF. Код, SQLite, старый архив и пользовательские данные не изменялись; функциональные тесты не запускались, поскольку поведение не менялось.
- Этап 3 целиком не завершён. Следующий срез — точный контракт Workflow Run и результатов узлов, затем артефакты и переходы с восстановлением.

## 2026-09-14 — подготовка нового репозитория и правила документации

- Прежняя реализация, её настройки, локальное состояние и релизы перенесены в `obsolete/`; проектные материалы графового подхода размещены в `docs/`.
- В корневых инструкциях закреплено обязательное документирование каждого этапа, подготовка нужных гайдов на русском языке и исправление обнаруженных неточностей.
- Корневой README, навигация по проектным материалам и план миграции приведены к русскоязычному формату.
- Проверка: сверены пути 379 файлов прежнего продукта и 58 файлов нового набора; все 56 записей манифеста указывают на существующие документы. Для текущих изменений проверены локальные ссылки в затронутых документах.
- Новый графовый runtime пока не реализован; импортированные англоязычные проектные материалы требуют перевода и согласования при внедрении соответствующих контрактов.

## 2026-09-14 — первый срез онбординга

- Согласован и записан проект безопасной первичной настройки: агент готовит смысловой контекст, детерминированный инструмент строит preview и применяет только подтверждённый план.
- Добавлен модуль `graph_orchestrator.onboarding` для внешнего проекта и self-hosting без вложенной копии ядра; артефакты и ограничения описаны в русскоязычных контракте и гайде.
- В Windows-консоли при первом self-hosted preview обнаружена ошибка кодировки русского вывода; исправлена настройка UTF-8 и повторный preview прошёл. План предложил создать только `project.json` и `project-context.md`, без изменения `AGENTS.md`.
- Проверка: `\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 10 тестов, 9 прошли, 1 пропущен из-за недоступности символических ссылок на этой Windows-системе. Есть отдельный тест русского вывода CLI при старой кодировке консоли. `git diff --check` не выявил ошибок содержимого; показал только предупреждения о переводе LF в CRLF. Локальные ссылки в затронутой документации проверены.
- Применение self-hosted плана ожидает явного подтверждения показанного хеша. Graph Runtime и Task Manager Service остаются нереализованными.

## 2026-09-14 — инструкция в корневом README

- В README добавлены пошаговые действия для внешнего проекта: submodule, подготовка ответов агентом, preview, подтверждение хеша, apply и проверка результата.
- Отдельно указан self-hosted вариант без вложенной копии и текущее ограничение: настройка проекта работает, выполнение задач графом ещё нет.

## 2026-09-14 — имя Orchestrator и первый срез Task Manager Service

- Активное ядро переименовано в Python-пакет `orchestrator`; согласованы пути `tools/orchestrator/` для внешнего проекта и `.orchestrator/` для локальной конфигурации и состояния. В `obsolete/` ничего не менялось. Широкое игнорирование `.orchestrator/` заменено на `.orchestrator/state/`, чтобы проектные файлы могли версионироваться. Прежний self-hosted preview с предыдущими путями устарел; применять его нельзя, нужен новый preview и подтверждение нового хеша.
- Реализован детерминированный Task Manager Service на SQLite: транзакционные снимки и события, оптимистические версии, контролируемые статусы, проверка артефактов перед `ready`, атомарное закрепление с lease, блокеры, решения пользователя и приёмка. Состояние графовых запусков в сервис не переносилось: хранятся только ссылки.
- Добавлены JSON CLI и локальная веб-панель только для чтения со списком, поиском, фильтром, карточкой, документами и историей. Диагностика `validate` выявляет нарушения целостности без автоматического исправления.
- Созданы [действующий контракт](architecture/task-manager.md), [инструкция пользователя](guides/tasks.md) и [проект решения](plans/2026-09-14-task-manager-design.md); README, roadmap и документация онбординга приведены к новой терминологии и текущему состоянию.
- Проверка: `\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 26 тестов, 25 прошли, 1 пропущен из-за недоступности символических ссылок в Windows. Включены параллельный claim, проверка изменения плана после `ready`, CLI и HTTP. Панель визуально проверена в локальном браузере на списке и карточке задачи. Graph Runtime и автоматический Executor Loop не реализованы.

## 2026-09-14 — отдельный пакет Task Manager Service и skill

- Реализация Task Manager Service, CLI и локальной панели перенесена из `orchestrator/` в устанавливаемый пакет `packages/task-manager/` (`orchestrator-task-manager`, импорт `orchestrator_task_manager`). Добавлены консольные команды `orchestrator-tasks` и `orchestrator-tasks-web`; формат SQLite и расположение состояния не менялись. Онбординг остался в ядре, пакет его не импортирует.
- Создан проектный skill `.agents/skills/orchestrator-task-manager/SKILL.md`; корневые инструкции и управляемый блок `AGENTS.md` для внешнего проекта направляют агента к нему. `.gitignore` теперь позволяет версионировать `.agents/skills/`, но игнорирует другое локальное содержимое `.agents/`.
- Обновлены [проект выделения](plans/2026-09-14-task-manager-package-design.md), [контракт](architecture/task-manager.md), [инструкция](guides/tasks.md), README и документы онбординга. Старый preview онбординга после изменения управляемого блока и путей должен быть построен заново перед применением.
- Проверка: пакет установлен в `.venv` из локального каталога; wheel собран без зависимостей и установлен отдельно в `.tmp/`. Изолированный запуск `python -S` из `.tmp/` создал задачу, прочитал историю и открыл HTML-представление без импорта `orchestrator`. `orchestrator-tasks --help` и `orchestrator-tasks-web --help` работают; ошибка русского вывода веб-команды в старой Windows-кодировке исправлена тестом. Тесты перенесены рядом с пакетом: `\.venv\Scripts\python.exe -m unittest discover -s tests -v` — 12 тестов ядра, 11 прошли и 1 пропущен по ограничению Windows на symlink; `\.venv\Scripts\python.exe -m unittest discover -s packages/task-manager/tests -v` — 17 тестов пакета прошли. Валидатор skill не смог запуститься из-за отсутствия `PyYAML` в доступных Python-окружениях; структура, относительные ссылки и видимость Git проверены вручную.

## 2026-09-14 — пакет Onboarding и полная поставка материалов Task Manager

- Onboarding перенесён в `packages/onboarding/` с собственными `pyproject.toml`, README, тестами, Python API и командой `orchestrator-onboarding`. Прямой запуск файла сохранён для первоначальной настройки без установки. Семантика preview/apply, структура плана и проверка подтверждённого хеша не менялись; зависимость от структуры ядра осталась явной.
- Контракт, пользовательский гайд и полный пример skill перенесены в ресурсы `orchestrator-task-manager` и включены в wheel. Корневые документы стали интеграционными указателями, а проектный skill `.agents/skills/` направляет к полному примеру в пакете. Команда `orchestrator-tasks resources` показывает пути к ресурсам, не создавая состояние проекта.
- Созданы [решение о границах](plans/2026-09-14-package-boundaries-design.md) и [инструкция пакета Onboarding](../packages/onboarding/README.md); обновлены README, архитектура, гайды и план работ. Прежние локальные preview-планы с устаревшими путями нельзя применять — перед применением требуется новый preview и подтверждение нового хеша.
- Проверка: `\.venv\Scripts\python.exe -m unittest discover -s packages/onboarding/tests -v` — 12 тестов, 11 прошли, 1 пропущен из-за недоступности symlink в Windows; `\.venv\Scripts\python.exe -m unittest discover -s packages/task-manager/tests -v` — 18 тестов прошли. Оба wheel собраны и установлены отдельно в `.tmp/`; изолированные импорты работают, а wheel Task Manager содержит все три Markdown-ресурса. Обе консольные команды и `orchestrator-tasks resources` проверены. Относительные ссылки и frontmatter обоих skill проверены вручную; штатный валидатор skill не запустился из-за отсутствия `PyYAML`.

## 2026-09-15 — живой снимок состояния

- Создан [`docs/project-status.md`](project-status.md) как единый актуальный снимок реализованного состояния для агента. Он отделён от roadmap, архитектурных контрактов и worklog: описывает доступные пакеты, команды, skill, проверки и отсутствующие возможности.
- В `AGENTS.md`, `README.md` и `docs/README.md` добавлены ссылки на этот документ. Его нужно обновлять после каждого завершённого этапа только подтверждёнными фактами.
