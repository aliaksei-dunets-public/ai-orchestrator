# TASK-0035: исправления после повторного аудита Agent Runtime

**Статус:** реализованный и проверенный кандидат для отдельной пользовательской приёмки, 2026-09-18. Self-review; независимый аудит этой реализации не заявляется. Передача в `awaiting_acceptance` выполняется публичным Task Manager API после публикации readiness/acceptance artifacts.

## Результат

Узел с обязательным итоговым артефактом теперь может явно задать отдельные требования для вопроса, блокировки и ошибки. KnowledgeRefreshNode совместим со стандартной runtime паузой. Knowledge execution gate сохраняет policy при продолжении и публикует каждый результат отдельной неизменяемой версией. Действующие контракты и гайды согласованы; удалён устаревший callback API из docs README.

Основание — [разбор аудита](2026-09-18-agent-runtime-audit-followup-triage.md) и [дизайн](../plans/2026-09-18-agent-runtime-audit-fixes-design.md). Изменение бюджетов, definition rebinding и MCP delivery не включены. У первоначального аудита сохранены исторические факты воспроизведения.

## Контракты выходов

[Node](../../orchestrator/runtime_contracts.py) получил `required_outputs_by_outcome`. Запись полностью заменяет базовый `required_outputs` для выбранного объявленного исхода; пустой список снимает только требования к outputs. Отсутствующая запись сохраняет прежнее базовое правило. Mapping копируется и становится неизменяемым, списки нормализуются в tuple. Неизвестные outcomes и malformed overrides отвергаются при создании Node.

Graph.from_dict поддерживает новое поле, [available_actions](../../orchestrator/agent_runtime.py) выдаёт отделённое JSON-описание. Validator проверяет выбранный набор и сохраняет остальные structural guards. Новая модель не угадывает смысл доменных outcomes `approved`/`failed` и позволяет требовать отдельную diagnostics на ошибке.

Пример миграции: базовый `required_outputs=("plan",)`, overrides `needs_input: []`, `blocked: []`, `failure: ["diagnostics"]`. Без overrides старый граф по-прежнему требует plan на всех outcomes: это сохранение совместимости, а не автоматическое отключение проверки. [Контракт](../architecture/graph-runtime-contract.md), [исполнимый пример](../guides/agent-runtime.md).

## Knowledge confirmation

[KnowledgeRefreshNode](../../orchestrator/knowledge_refresh_node.py) возвращает runtime outcome `needs_input`, `WaitState` и доменный `data.result.status="awaiting_confirmation"`. Собственный graph объявляет needs_input с self-target. Обязательный служебный `result` сохранён на каждом исходе. После явного resume caller повторно исполняет узел с тем же request и решением; только `approved=True` с decision ref разрешает full refresh. Отказ или отсутствие ref оставляет запрос неподтверждённым и не выполняет full refresh.

[Knowledge execution gate](../../orchestrator/agent_execution.py) подаёт в runtime outcome узла, а не domain status. [Граф gates](../../orchestrator/execution_gates.py) допускает needs_input на knowledge stage. Продолжение без request использует сохранённый request; изменённый request отвергается до resume и refresh. Mapping decision должен быть JSON-представимым. Проверки stage/state и result budget происходят до внешнего эффекта.

Knowledge evidence получает version `v<process revision перед submit>`, поэтому запрос подтверждения, повторный запрос и успешный итог не конфликтуют с предыдущими payload. Старые versions остаются проверяемыми в Artifact Repository. Readiness policy использует доменный status, как прежде; создание process результата не выполняет Git commit.

Обновлены [knowledge guide](../guides/project-knowledge.md), [контракт gates](../architecture/execution-gates.md) и [guide gates](../guides/execution-gates.md). Callers, проверявшие outcome `awaiting_confirmation`, должны проверять outcome `needs_input` для runtime управления, а доменный status читать из data.result. Precommit status/commit_allowed остаются прежними.

## Доказательства и критерии задачи

| Критерий | Проверка |
| --- | --- |
| AC-01: требования по исходам, совместимость и guards | Два новых [contracts tests](../../tests/test_runtime_contracts.py): overrides/defaults/legacy, loader, malformed definitions и immutable ownership. Два новых [runtime tests](../../tests/test_agent_runtime.py): вопрос и blocker → resume → approved/failed; обязательные plan/diagnostics; отрицательные wait/artifact/JSON/revision сценарии и изоляция actions. |
| AC-02: reusable node pause/resume/confirmation | Два новых [knowledge node tests](../../tests/test_knowledge_refresh_node.py): настоящий node → настоящий runtime → resume → approved refresh, а также отказ/неверный approved/отсутствие ref без full refresh. Старый тест graph confirmation обновлён на новый runtime outcome. |
| AC-03: knowledge execution gates | Два новых [facade tests](../../tests/test_agent_execution.py): полный gates → вопрос → отказ → одобрение без ref → одобрение с ref → final readiness/awaiting_acceptance; четыре immutable versions проверены. Попытка сменить policy, malformed request/decision, отсутствие ответа и exhausted budget не выполняют refresh; отказанные guard действия сохраняют snapshot. |
| AC-04: документация | Контракты и гайды описывают оба уровня status/outcome и явные overrides. Docs README указывает поддерживаемые методы, AgentExecution и gates. Устаревшие заявления об отсутствии gates исправлены в затронутых guides; навигация и относительные ссылки проверены. |
| AC-05: проверенный кандидат | Весь root набор прошёл, включая real pinned Graphify fixture. Readiness/acceptance package публикуются с хешами кандидата; состояние задачи меняется только публичным сервисом, без приёмки от имени пользователя. |

Команды и результаты:

- `python -X utf8 -m unittest tests.test_runtime_contracts tests.test_agent_runtime tests.test_knowledge_refresh_node` — **38/38**.
- `python -X utf8 -m unittest tests.test_agent_execution` — **40/40**. После расширения отрицательных проверок и final readiness повторно исполнены два изменённых facade tests, **2/2**.
- `ORCHESTRATOR_GRAPHIFY_PYTHON=.tmp/graphify-0.9.63-venv/Scripts/python.exe`, `python -X utf8 -m unittest discover -s tests -v` — **159 tests, 158 passed, 1 skipped, 0 failures**, 24,877 s. Пропуск — отсутствие Windows file-symlink privilege. `RealGraphifyIntegrationTests.test_real_staging_refresh_mcp_unicode_frontend_rename_delete` прошёл.
- Исполнены два блока agent-runtime guide и новый confirmation блок project-knowledge guide; **3/3**. Knowledge пример использовал deterministic service double и не изменял production pointer.
- `python -X utf8 -m compileall -q orchestrator tests`, `git diff --check`, проверка ссылок обновлённых материалов и публичный Task Manager health/history.

Добавлено **8 предметных тестов**. Full Graphify confirmation на production данных, внешний MCP transport, межсессионное recovery и performance benchmark в этой работе не выполнялись. Task Manager/Onboarding code не менялся, отдельные suites этих пакетов не повторялись; публичные lifecycle guards Task Manager проверены на новой задаче.

## Подготовка и передача

TASK-0035 создана по прямому поручению пользователя и прошла AgentPreparation с содержательными Context/Analysis/Plan, self-review, immutable Plan/Review/Execution Package, ready и ExecutionPreflight до claim. Первый plan был корректно отклонён, поскольку driver не включил inherited analysis invariants. Driver завершился; ссылка утраченной in-memory сессии закрыта публичным API без заявления об успехе. Повторная preparation включила все инварианты; claim выполнен штатно. Ни одна защитная проверка не отключалась.

Пользователь разрешил реализацию, но ещё не принимал этот результат. Кандидат передаётся с отдельными readiness/acceptance artifacts; фактические version/state/history следует читать в Task Manager. Все исходные изменения соседнего этапа execution gates сохранены, не выдаются за созданные TASK-0035. Obsolete, .venv, чужие задачи и production knowledge pointer не изменены.

Ограничения прежнего runtime остаются: process state в памяти; waits расходуют result budget; definition drift требует проверки новой подготовки; публикация Artifact Repository, Task Manager и runtime не образует общей транзакции. Исправление knowledge confirmation не обещает recovery после произвольного сбоя внешнего эффекта.
