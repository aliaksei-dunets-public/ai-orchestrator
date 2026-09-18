# TASK-0034: удаление callback GraphRuntime

**Статус:** проверенный локальный кандидат для отдельной пользовательской приёмки, 2026-09-18. Это не опубликованный Git commit и не автоматически принятая задача.

## Результат и решение

Удалены классы GraphRuntime и PreparationWorkflow, модули `orchestrator/workflow_runtime.py` и `orchestrator/preparation_workflow.py`, их публичные exports и активные импорты. Alias на AgentGraphRuntime отсутствует: сигнатуры и resume-семантика несовместимы. Единственный runtime процесса — AgentGraphRuntime; подготовка — AgentPreparation, исполнение — AgentExecution.

В [runtime_contracts.py](../../orchestrator/runtime_contracts.py) сохранены Graph, Node, NodeResult, WaitState, WorkflowRun, RuntimeError, terminal constants и публичный validate_node_result. Базовая WorkflowRun — общая модель снимка, не второй runtime. Агентские facade и KnowledgeRefreshNode используют этот модуль. PreparationError экспортируется из общих primitives; неиспользуемая callback-ветвь `_queue(resumed=...)` удалена. Общая `synchronize` сохранена: её вызывает TaskEffectSync через super, она не является callback dispatch.

Удаление заменяет прежнюю цель ремонта гонок callback-runtime и сохранения его API. Agent runtime уже проверяет terminal node names, revision/definition/wait guards, сохраняет response/cancel reason и ограничивает число results. Эти механизмы не ослаблены. Task Manager code/schema/API, соседние задачи, `.venv/` и `obsolete/` не изменены этой работой. Исходное рабочее дерево содержало изменения других этапов; они сохранены, полный suite проверяет совокупное текущее дерево.

Действующие контракты, README, roadmap/project-status и guides переведены на агентский путь. Старые адреса workflow/preparation guides теперь содержат инструкции миграции. В исторических отчётах сохранены факты и хеши на дату проверки; ссылки на удалённые исходные файлы заменены явно помеченными ссылками на миграцию.

## Перенос предметных проверок

Два callback test-модуля (10 runtime и 18 preparation tests) и agent test обещания неизменных legacy signatures удалены. Нужные проверки распределены между общими и агентскими suites:

| Прежняя область | Действующая проверка |
| --- | --- |
| Duplicate/malformed nodes, unknown targets, immutability graph/transitions | RuntimeContractsTests |
| Node outcomes/transitions/required_outputs, artifact shape/repository boundary, snapshot serialization | RuntimeContractsTests + AgentRuntimeTests |
| Последовательные переходы, wait identity, JSON/inputs/results isolation, cancel/terminal states | Существующие AgentRuntimeTests; guards/limits/history сохранены |
| Реальный ready без исполнения, owned blocker, revised plan/review, context/review limits | Существующие AgentPreparationTests |
| Потеря constraints, циклическая/неизвестная зависимость, пустая validation | Новый invalid-plan сценарий AgentPreparationTests |
| Bool definition binding, неполное criterion coverage, malformed/open major/critical findings и route | Новый review rejection сценарий AgentPreparationTests |
| Wait на каждой semantic стадии | Новый сценарий шести стадий, включая Package/Ready; rejected submit сохраняет response и прежние результаты |
| Ошибка plan projection без повторного planner | Новый IO failure/synchronize сценарий с неизменным принятым run |
| Внешний blocker и reconcile | Новый сценарий: версия принимается явно, blocked задача не допускает submit и чужой blocker не снимается |
| Версии/definition drift, pending/unknown effects, пользовательский plan, immutable corruption | Существующие AgentPreparationTests, включая history reconciliation и проверки каждого task boundary |
| Старые публичные API отсутствуют, shared exports существуют | Новый runtime contracts test |
| Изоляция старого и нового snapshot/history после нескольких actions | Новый agent runtime regression с вложенными изменяемыми данными и отказом создания публичного snapshot при submit/cancel |

Тесты: [общие контракты](../../tests/test_runtime_contracts.py), [agent runtime](../../tests/test_agent_runtime.py), [agent preparation](../../tests/test_agent_preparation.py). Перенос сохраняет проверяемые свойства; callback-specific execution exception/fallback/сигнатуры не имитируются новым API.

## Ресурсы AgentGraphRuntime

Убрана полная deep-copy run при подготовке submit/resume/cancel. Рабочая копия отделяет изменяемые контейнеры results/result_counts/history; ранее принятые runtime-owned payload не изменяются. Публикация сначала создаёт полный изолированный публичный snapshot и только затем заменяет canonical run. Inspect_run также возвращает deepcopy. Это сохраняет compare/check/publish и не даёт rejected action или правкам публичного snapshot изменить старые events.

Замер выполнен Python 3.12.14 на Windows через [runtime_benchmark.py](../../scripts/runtime_benchmark.py). Submit latency и peak allocations измерены под tracemalloc; отдельный inspect измерен без tracing. Каждая строка — один локальный проход, не статистический SLA. Начальный baseline снят до удаления и оптимизации; дополнительные размеры — после. Большой дополнительный проход выполнялся при параллельных suite checks, поэтому его latency отражает также текущую нагрузку хоста. [Полные данные](2026-09-18-task-0034-runtime-measurements.json).

Payload: string — одна строка 32 KiB; nested_json — список 256 маленьких dictionaries, сериализованный размер 30 620 bytes.

| Payload / results | Baseline total s | После total s | Baseline peak MiB | После peak MiB |
| --- | ---: | ---: | ---: | ---: |
| String / 10 | 0,0042 | 0,0031 | 0,390 | 0,387 |
| String / 50 | 0,0470 | 0,0278 | 1,756 | 1,718 |
| String / 100 | 0,1606 | 0,0906 | 3,507 | 3,423 |
| Nested JSON / 10 | 0,1561 | 0,1018 | 2,686 | 2,255 |
| Nested JSON / 50 | 3,5557 | 1,7407 | 12,459 | 10,119 |
| Nested JSON / 100 | 17,5376 | 6,6959 | 24,886 | 20,160 |

Для 100 nested results последний submit: 264,629 → 137,516 ms под tracing; полный inspect без tracing: 24,413 → 24,986 ms. Retained memory почти прежняя: 13,049 → 13,045 MiB, поскольку история результатов остаётся полной. Это сокращение лишних копий, а не уменьшение объёма канонической истории.

Дополнительные post-change samples для 100 results: nested JSON 7 616 bytes — 1,5239 s, peak 5,222 MiB; 122 804 bytes — 43,6333 s, peak 81,910 MiB. String 8 204 bytes — peak 1,079 MiB; 131 084 bytes — peak 12,892 MiB. Вложенные контейнеры требуют существенно больше копирования, чем строки, которые deepcopy переиспользует внутри снимка; JSON normalization при submit всё равно создаёт новое принятое значение.

Полный snapshot включает всю историю, поэтому совокупная стоимость последовательных возвращаемых snapshots всё ещё может быть O(N²). Result/node budgets ограничивают число results, но не bytes. Произвольные лимиты текстовых полей, новые transport gates и checkpoint storage не добавлялись. Caller должен задавать budgets и передавать большие payload через проверенные repository refs; structural runtime ref не заменяет проверку тела. Отдельная pagination/history API могла бы менять стоимость полной выдачи, но не входит в согласованное удаление callback-пути.

Повторить post sample:

```powershell
.\.venv\Scripts\python.exe scripts/runtime_benchmark.py --output .tmp/runtime-after.json
.\.venv\Scripts\python.exe scripts/runtime_benchmark.py --payload-size 8192 --output .tmp/runtime-small.json
.\.venv\Scripts\python.exe scripts/runtime_benchmark.py --payload-size 131072 --output .tmp/runtime-large.json
```

## Проверки кандидата

- До изменения: root suite — 164 tests, 162 passed, 2 skipped (Windows file symlink и provider без explicit env).
- После: root suite с `ORCHESTRATOR_GRAPHIFY_PYTHON=.tmp/graphify-0.9.63-venv/Scripts/python.exe` — 148 tests, 147 passed, один Windows file-symlink skip; real pinned Graphify fixture прошёл.
- Общие contracts / runtime / preparation — 54/54 (7 + 19 + 28). Onboarding — 19 tests, 18 passed, один Windows skip. Task Manager — 73/73. Итого полный набор: 240 tests, 238 passed, 2 skips, 0 failures.
- Исполнимые Python-примеры действующих runtime/preparation/execution guides, проверка относительных ссылок затронутых материалов, AST-проверка отсутствия callback classes/imports, compileall и diff check выполнены отдельно.
- Публичный Task Manager использован для подготовки, review/immutable package, ready, source preflight и claim. Кандидат передан в awaiting_acceptance с реальными readiness/acceptance artifacts; разрешение выполнять работу не выдаётся за приёмку.

## Ограничения

Runtime/history/sync cursors остаются in-memory. Persistence/checkpoints, full execution gates, универсальный schema registry и новые внешние adapters не реализованы этим изменением. Production knowledge current pointer не обновлялся в рамках удаления: автоматический commit не выполнялся, а runtime tests/Graphify fixture используют отдельные временные проекты. Это self-review и suite validation, не независимый внешний аудит или полный Agent E2E.
