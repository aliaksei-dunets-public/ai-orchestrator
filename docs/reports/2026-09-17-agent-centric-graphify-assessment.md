# Оценка агент-центричной архитектуры и миграции на Graphify

> **Исторический baseline:** ниже сохранён срез до реализации. Затем пользователь подтвердил дизайн, и TASK-0028 добавила первый явный Python runtime. Актуальное дополнение — [отчёт AgentGraphRuntime](2026-09-17-agent-runtime-v1.md); исходные цифры и утверждения этого отчёта относятся к первоначальной оценке, не к нынешнему коду.

**Статус:** первичная архитектурная оценка и baseline-проверка, не отчёт о завершённом внедрении. Конкретный дизайн миграции ожидает подтверждения. **Дата:** 2026-09-17. **Задача:** TASK-0027.

## 1. Главный вывод

Новое направление совместимо с большей частью реализованного проекта. Основной актив не Python workflow controller, а независимый Task Manager, immutable artifacts и формальные проверки. Их не нужно заменять агентскими обещаниями. Требуется изменить способ управления процессом: агент явно выбирает работу и передаёт результат детерминированным сервисам; сервисы не вызывают рассуждающие этапы вместо агента.

Пользователь отдельно подтвердил, что Task Manager с SQLite актуален и не изменяется. Поэтому TaskML, task.yaml, файловая карточка, events.jsonl и обязательная specification исключены из нового действующего подхода. Это не открытый вопрос миграции.

Graphify заменяет предполагаемую разработку собственного универсального graph backend, но не устраняет необходимость нашего freshness/provenance/query contract. Он не заменяет Task Manager, Workflow Graph, project memory, исходники и тестовые свидетельства.

В этом срезе изменена документация направления и подготовлен дизайн. Production Python-код не изменён; нового process API, agent skill или работающего Graphify adapter пока нет. Установка, индексация и глобальные настройки не выполнялись. Нельзя считать миграцию завершённой по появлению этих документов.

## 2. Что проверено и границы оценки

Изучены оба предоставленных документа полностью, текущий project status и roadmap, backlog, действующие контракты Task Manager, состояния/хранения, Workflow Run, Graph Runtime и Preparation Workflow, документационные индексы и master-spec прежнего PKM. Осмотрены все модули корневого `orchestrator`: request_router, task_creator, request_flow, workflow_runtime, artifact_repository и preparation_workflow; отдельно сверены точки подключения onboarding и публичного Task Manager.

Выполнены текущие полные unit suites ядра и двух пакетов, публичное чтение списка задач и read-only validate. Проверена опубликованная документация кандидата Graphify upstream. Не выполнялся полный построчный security audit Task Manager или всех импортированных draft-документов; не проверялись реальный Graphify runtime, Linux/macOS, внешний проект на новых контрактах, performance нового API или семантическая полнота графа. Оценка отличает обнаруженный кодовый факт от рекомендуемого решения.

Перед работой Git показывал только два новых пользовательских документа как untracked. Они не переписаны. `.venv`, посторонние файлы, старые artifacts и `obsolete/` сохранены; старый код не импортировался и не запускался для реализации. TASK-0027 создана публичным сервисом; это состояние текущей работы, а не изменение самого Task Manager.

## 3. Что реально есть

| Область | Реализовано | Что не следует из реализации |
| --- | --- | --- |
| Task Manager | Независимый пакет, SQLite v5, транзакционные мутации, optimistic version, события, idempotency, ready guards, claim/lease, blockers/decisions, acceptance, backup/restore, CLI/MCP и read-only web | Не выполняет workflow или reasoning; ссылки на run не сохраняют его state |
| Onboarding | preview/apply с hash confirmation, защита файлов, self-hosting, проверка MCP Task Manager и локальный конфиг | Не подключает Orchestrator Agent или Graphify; наличие onboarding не означает end-to-end execution |
| Artifact Repository | Immutable версии payload/manifest, SHA-256, canonical JSON, атомарная публикация версии, проверка чтения, path/reparse guards | Не durable workflow state и не semantic quality evaluator; нет общей транзакции с Task Manager |
| Request Router | Принимает внешнюю классификацию, валидирует direct_response/managed_work и task type | Не собственный классификатор и не автоматически подключённый агентский skill |
| Task Creator | Внешний builder формирует смысл; wrapper проверяет draft и вызывает публичный create_task | Не reasoner и не полноценный task-creation skill для внешнего MCP-агента |
| Request Flow | Последовательный Router → Creator | Не автоматически запускает подготовку и исполнение |
| Graph Runtime | Graph/Node/Result/Wait, один шаг, declared transitions, waits/resume/cancel, изолированные снимки в памяти | Нет persistence, process revision, explicit submit API, actor binding или общего enforcement permissions |
| Preparation Workflow | Context → Analysis → Planning → Review → Package → Ready, внешние adapters, artifact publication и Task Manager sync, bounded revisions | Не новая agent-driven orchestration, не execution loop и не restart recovery |
| Знания | Проектные PKM материалы и новые решения пользователя | Нет реализованного provider service, Graphify adapter/indexer, freshness tracking или memory store |

Ключевой нюанс: утверждение «Python сейчас решает всю семантику» неточно. `RequestRouter.classifier`, `TaskCreator.builder` и четыре preparation adapters уже передают семантику наружу. Реальная controller-centric часть — фиксированная последовательность, callback dispatch и пакетирование/sync в PreparationWorkflow, а не встроенная LLM-логика, которой в ядре нет.

## 4. Что сохраняем, что меняем

| Объект | Решение | Почему |
| --- | --- | --- |
| `packages/task-manager/` и его resources | Не менять | Прямое уточнение пользователя; уже нужная детерминированная граница |
| SQLite задач и публичные карточки completed работ | Сохранить | Источник истины и исторические свидетельства; архитектурная смена не отменяет приёмку |
| `artifact_repository.py` | Сохранить как сервис | Уже соответствует роли durable artifacts |
| `workflow_runtime.py` | Расширить отдельным explicit-result/action путём | Агент должен подавать результат без требования Python executor callback |
| `preparation_workflow.py` | Временно сохранить, затем заменить основной usage | Не наращивать reasoning controller; извлечь reusable validation/publication primitives |
| `request_router.py`, `task_creator.py` | Сохранить контрактные primitives; перенести рекомендуемое usage к агенту | Смысл уже внешний, массовая перепись не нужна |
| `request_flow.py` | Совместимость, не центр новой архитектуры | Агент сам решает direct/managed и обращается к сервисам |
| Onboarding | Позже расширить явным подключением агентских instructions и knowledge profile | Настройка должна оставаться preview/apply, без скрытых установок |
| Старый PKM backend design | Заменить новым provider-independent service | Не реализовывать собственную graph database/extractors/identity engine для первого Graphify среза |
| Старые план/review/testing/documentation contracts | Переносить предметные инварианты, а не controller graphs | Evidence, coverage и binding нужны и агенту; способ маршрутизации изменяется |
| Runtime checkpoints, permissions/workspaces | Отдельные primitives и platform adapters | Не прятать их в Task Manager или agent reasoning |

«Заменить артефакты» означает создавать новые действующие версии контрактов и результатов, а не стирать принятые исторические планы, audit findings или user decisions. Immutable payload должен остаться immutable. Существующий код выводится из основного пути только после эквивалентных проверок нового пути.

## 5. Оценка нового подхода

### Сильные стороны

Агент владеет сбором контекста, выбором skills, глубиной анализа и адаптацией к evidence — это естественнее, чем кодировать каждую вариацию workflow. Детерминированные сервисы сохраняют проверяемость lifecycle и artifacts. Отделение platform adapters помогает переносимости; отсутствие обязательных sub-agents снижает сложность v1. Graphify позволяет сосредоточиться на knowledge integration вместо разработки ещё одного parser/graph store.

Это архитектурные преимущества, а не измеренное ускорение. Токены, latency, качество impact analysis и стоимость Graphify на нашем корпусе ещё не измерены. Переносимость инструкций не гарантирует одинаковые permissions/tool behavior во всех хостах.

### Основной риск

Если перенести gates только в skill, система станет агент-центричной по названию, но менее надёжной. Ядро должно проверять допустимость результата, актуальность task definition/plan/source snapshot, waits и limits. Агент по-прежнему не может выставить ready без существующих свидетельств или принять собственный результат от имени пользователя.

Второй риск — новая избыточность: Kernel из StateStore, PolicyValidator, ToolRegistry, MemoryStore и Scheduler может вырасти во второй оркестратор. Для v1 нужны небольшие primitives вокруг уже реализованных сервисов, а не новый универсальный framework или обязательный event-bus.

## 6. Нюансы существующего кода

1. **Нет agent-facing submit primitive.** `GraphRuntime.step/resume` требуют executor. Агент может быть реализован callback-ом, но это не удобный внешний API для inspect → choose → work → submit. Нужна проверка process revision и повторного/stale result; одной task version недостаточно.
2. **Controller ownership подготовки.** `_graph()` задаёт фиксированные переходы, `_execute()` вызывает adapters, `_queue()` выбирает side effects. Это основное место декомпозиции, не повод удалить validation plan/review или лимиты.
3. **Синхронизация только текущей сессии.** Pending actions/cursor существуют в памяти; обычный отказ можно продолжить без повторного planner, потерю процесса — нельзя. Нельзя объявлять durable orchestration, пока нет отдельного checkpoint/effect protocol.
4. **Неопределённый commit outcome.** Публичная версия и operation_id помогают не всем действиям; recovery после timeout/crash требует реальной сверки. Exactly-once для tool effects сейчас не обеспечивается.
5. **Source revision передаётся строкой caller-ом.** Preparation проверяет её непустоту, но не вычисляет и не сверяет working-tree snapshot. Graph freshness и execution preflight нужно проектировать на реальных байтах выбранного корпуса.
6. **Совпадение project roots — обязанность caller.** Preparation не доказывает общность проекта service/repository. Будущий composition boundary должен обеспечить фиксированный root, не обращаясь к приватным internals Task Manager.
7. **Runtime contracts преимущественно структурные.** Имена input/output contracts не запускают semantic schema validation сами по себе; artifact hash в generic result не доказывает существование/достаточность evidence. Это честно отражено в нынешних документах и должно сохраниться.
8. **Permissions не реализованы универсально ядром.** Repository защищает свои пути, но не все shell/Git/tools агента. Обещание «Kernel предотвращает любой destructive Git» без соответствующего adapter будет неверным.
9. **Результаты узлов перезаписываются по node_id.** Immutable repository хранит версии, но runtime.results не полная история попыток. Для durable audit процесса потребуется отдельная история принятия actions, не изменение events задач.
10. **Не универсальные retry bounds.** Preparation имеет counters review/context; generic runtime не имеет собственной retry policy enforcement. Все будущие limits следует подкреплять tests, а не считать уже существующими.

Это архитектурные ограничения и места будущих изменений. В baseline suite новых падений не обнаружено; исправления поведения в этом срезе не выполнялись.

## 7. Оценка Graphify и недостающих контрактов

В новых документах нет конкретной версии или upstream URL. Кандидат для интеграции — [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify/blob/v8/README.md); dependency пока не pinned. Не выбираем другой одноимённый пакет автоматически. Published README и MCP reference — свидетельство поверхности upstream, не доказательство его работы в нашем Windows environment.

[MCP reference](https://graphiffy.com/docs/mcp-tools) не описывает инструмент initial load/refresh. Наш service должен отдельно оборачивать indexing и query. Кроме того, upstream допускает project_path и может возвращать текстовый context; нужны project isolation и честная нормализация без выдуманного typed graph output.

Для безопасной интеграции ещё нужны:

- provider identity/version и capabilities; поддержка incremental отдельно от query;
- source snapshot с dirty/untracked changes и исключением generated graph outputs;
- раздельная freshness code и semantic layers;
- bounded query result с evidence/citations/provenance и limitations;
- политика missing/stale/failed/refreshing и advisory/required;
- refresh result с проверкой источников до и после индексации;
- публикация проверенного графа и сохранение старого при отказе;
- rename/delete reconciliation, branch switch и перезагрузка graph snapshot MCP-сервером;
- явный data boundary: что индексируем локально и что может обрабатываться моделью;
- command timeout/output limit, path restrictions и безопасные аргументы;
- правила отдельной project memory с evidence и аннулированием выводов при изменении источников.

Новый документ предполагает, что граф перед commit соответствует implementation candidate. Сравнение только HEAD этого не обеспечивает: код после implementation ещё dirty. Fingerprint всего workspace также неверен — graph refresh изменит свои outputs и сам себя сделает stale. Нужен явно определённый corpus fingerprint.

Рекомендуется code-only initial integration. Обработка документов внешней моделью, Git hooks, автоматическая глобальная регистрация skills и сетевые PR-tools не входят в безопасный default. Заявление о полностью локальной обработке всего корпуса не подтверждено для семантических inputs; [upstream README](https://github.com/Graphify-Labs/graphify/blob/v8/README.md) различает эти режимы.

SAP/ABAP остаётся последующим extension. React/Vue проверяются fixtures, а не только наличием TSX/Vue extensions в опубликованном списке. Собственный memory store также не нужен для подтверждения первого code graph среза.

## 8. Какие документы меняются

| Материалы | Новый статус/действие |
| --- | --- |
| Два документа пользователя | Сохранены как исходные решения; файловые task examples не нормативны |
| `architecture/agent-centric-orchestration.md` | Новое русское принятое распределение ответственности и фиксированная граница Task Manager |
| `architecture/project-knowledge-service.md` | Новое направление и предложенные service/provider contracts; не объявлены реализацией |
| README, docs README, project status | Новый подход и явное различие между направлением и старым работающим API |
| Roadmap | Старые execution/PKM controller steps заменены последовательностью agent-interface → preparation → provider → execution → packaging → scenarios |
| Workflow Run / Graph Runtime / Preparation contracts и guides | Сохраняют описание фактического API, получают миграционное предупреждение и новый приоритет направления |
| Старый backlog v1 | Помечен как прежняя зависимость, не как план новой реализации |
| PKM master-spec и индексы development/graph | Отмечен новый приоритет service/backend и запрет переноса старого controller/backend автоматически |
| Остальные imported development/knowledge материалы | Требуют предметного переноса при соответствующем срезе; не объявлены полностью переписанными |
| Worklog | Фиксирует baseline, документационные изменения и отсутствие behavioral implementation |

Не следует массово переводить десятки старых drafts и объявлять их действующими без кода. Требуется точная таблица переносимых invariants на каждом implementation этапе: review independence/coverage, testing evidence, work-unit dependency, documentation sync, acceptance candidate revision. Смена архитектуры не отменяет эти требования автоматически.

## 9. Как мигрируем

### Этап A — согласование границ, текущий срез

Документировать решение и ограничения, сверить Task Manager и baseline, предложить новый process/query контракт. Результат этого среза — документы оценки и дизайн к подтверждению, не ready execution package. Нужно подтвердить конкретный Graphify upstream и безопасный первый индексируемый корпус.

### Этап B — explicit agent process API

Добавить явное принятие результатов без Python callback dispatch, inspection допустимых actions и process revision. Сохранить runtime compatibility. Обязательные tests: invalid action/result, stale version/definition, duplicate submission, wait identity, loop bounds и unchanged snapshot после rejected action.

### Этап C — подготовка управляемой задачи агентом

Перенести основной usage Context/Analysis/Planning/Review к агентским instructions/skills, выделить validation/publication/sync primitives. Проверить реальные Artifact Repository и Task Manager до ready; не fabricating review. Одинаковая task/root binding, version conflict и pending effects не позволяют следующий шаг. Устаревший controller выводится из основного пути только после покрытия.

### Этап D — provider contract и первый реальный Graphify

Capabilities, fixture transport, version-pinned реальный index/query smoke test, snapshot metadata, advisory fallback и явный refresh. Проверки dirty/untracked/rename/delete, failure safety и project isolation обязательны. Только реальный integration run подтверждает Graphify compatibility; mocks не достаточно.

### Этап E — исполнение и gates

Preflight сверяет подготовленный пакет с текущим source snapshot; claim берётся существующим API. Агент выбирает work units и review remediation. Код сохраняет структурную валидность, limits и evidence bindings. Tests/documentation/knowledge refresh/final validation приводят к acceptance, не self-approval.

### Этап F — packaging и сквозная готовность

Устанавливаемый agent/core bundle, host-neutral инструкции и минимальные adapters, внешний onboarding, end-to-end execution, stale plan/graph, waits, crashes, uncertainty, permissions и rollback. Только после проверки документации, артефактов и сценариев публикуется readiness. Cross-session checkpoints могут быть отдельным срезом: пока их нет, не обещаем restart recovery.

Внешний tracker, worker pool, ABAP и продвинутая semantic memory не блокируют локальный v1. TASK-0016–0022 сейчас created и требуют уточнения canonical cards под этот дизайн; в текущем срезе они не изменены и не закрыты. TASK-0024 остаётся awaiting_acceptance; новая работа не является её приёмкой.

## 10. Совместимость и возврат

Не менять database schema/API Task Manager. Не переписывать историю completed задач. Новый process graph имеет свою version; нельзя подменить graph definition существующего run. Legacy путь сохраняется временно с явным статусом, а не выбирается скрыто после ошибки нового. При отказе Graphify main workflow возвращается к direct discovery только согласно политике; stale статус сохраняется.

Не удалять старый graph/artifact до проверки нового. Не install global config/hooks для эксперимента. Исходные пользовательские файлы и `.venv` сохраняются. Откат к прежнему API — выбор legacy path для нового процесса, а не git reset, восстановление всей SQLite или стирание побочных эффектов.

## 11. Результаты проверок

Команды запущены из корня репозитория интерпретатором `.venv/Scripts/python.exe`:

| Команда | Результат |
| --- | --- |
| `-m unittest discover -s tests -v` | 52 теста: 51 passed, 1 Windows file-symlink privilege skip; 3.674 s |
| `-m unittest discover -s packages/onboarding/tests -v` | 19 тестов: 18 passed, 1 Windows symlink skip; 0.996 s |
| `-m unittest discover -s packages/task-manager/tests -v` | 73 passed; 22.572 s |
| `-m orchestrator_task_manager.task_cli --project . validate` | `ok: true`, `result: []` после создания TASK-0027 |

Итого baseline: 144 tests, 142 passed, 2 skipped, 0 failures. Эти проверки подтверждают нынешний код, не отсутствующее новое поведение. Duration — один запуск на этом Windows workspace, не benchmark.

Проверены 217 локальных Markdown-ссылок в изменённых и новых документах: отсутствующих целей нет (anchors отдельно не валидировались). `git diff --check` прошёл, только предупреждения настройки LF/CRLF. `git diff --name-only -- packages/task-manager orchestrator packages/onboarding` пуст: production-код и пакетные ресурсы не изменены. Новые code tests появятся вместе с реализацией. Проверки Graphify не выполнены: зависимости не установлены, индекс не построен, MCP query к нему не выполнялся.

TASK-0027 после регистрации реального уточнения пользователя и ссылки на этот отчёт переведена публичным API в `awaiting_input`, version 6, без active run/claim. История содержит создание, начало подготовки, clarification, documentation attachment, закрытие run-link и статус ожидания. `health_check()` после этих мутаций вернул `[]`. Задача не completed; разрешение начать работу не зарегистрировано как acceptance.

## 12. Что сделано и что ещё не сделано

Сделано: оценка направления, кодовая карта миграции, baseline, новые русские архитектурные документы, обновлённая навигация/roadmap и проект конкретной миграции. Зафиксирована неизменяемая граница Task Manager.

Не сделано: explicit-result API, agent skill suite, runtime persistence, agent-driven preparation implementation, knowledge contracts как Python API, indexer/MCP adapter, работающий Graphify граф, execution primitives/gates, новый устанавливаемый bundle и end-to-end acceptance. Исправления обнаруженных архитектурных нюансов пока описаны, а не выданы за implemented fixes.

Следующий шаг — подтвердить [поэтапный дизайн](../plans/2026-09-17-agent-centric-graphify-migration-design.md), после чего подготовить предметный plan/review/Execution Package для первого implementation среза по существующему Task Manager протоколу.
