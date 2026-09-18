# TASK-0028: первый кодовый срез агент-центричной миграции

**Статус:** реализация проверена и принята пользователем; TASK-0028 — completed, version 18, без active run/claim. Это не полное завершение миграции. **Дата реализации:** 2026-09-17; приёмки — 2026-09-18.

<a id="user-acceptance"></a>
## Приёмка пользователем

После предъявления результата пользователь ответил «подтверждаю продолжай», затем «продолжай». Перед accept_task проверены неизменные SHA-256 четырёх файлов кандидата. Публичный API атомарно завершил TASK-0028 v18 для указанной ниже candidate_revision; task_completed и health_check=[] проверены. Приёмка относится только к runtime-срезу, не к будущей подготовке или Graphify.

## Результат

Добавлен `AgentGraphRuntime`: агент подаёт результат текущего узла явно, без Python executor callback. Ядро проверяет структуру, process revision, закреплённую task definition, declared outcome/target, wait identity и budgets и хранит один canonical снимок процесса в памяти.

Существующие `GraphRuntime`, его сигнатуры и сериализация WorkflowRun сохранены. PreparationWorkflow по-прежнему работает с legacy callbacks. Код, схема, API, MCP/CLI и resources Task Manager не изменены; onboarding не менялся. Агентская подготовка, Graphify integration и persistence в этот срез не входят.

Подтверждённый [дизайн миграции](../plans/2026-09-17-agent-centric-graphify-migration-design.md) записан отдельным коммитом `f881dda`. Другие пользовательские/предыдущие изменения в этот коммит не включены. Подтверждение дизайна не записано как acceptance новой реализации.

## Изменения кода

- [agent_runtime.py](../../orchestrator/agent_runtime.py): AgentWorkflowRun и AgentGraphRuntime; create/inspect/available_actions/submit_result/resume_wait/cancel.
- [workflow_runtime.py](../../orchestrator/workflow_runtime.py): общая публичная структурная проверка validate_node_result вместо копирования validation logic; legacy валидные сценарии сохранены.
- [Публичные импорты](../../orchestrator/__init__.py): экспорт нового runtime, снимка и validator.
- [Предметные tests](../../tests/test_agent_runtime.py): 19 новых tests с positive/negative cases и integration с реальным публичным Task Manager во временном проекте.

Не создаётся второй снимок legacy run и не запускается reasoning loop. Новый runtime — отдельный выбранный agent-driven путь, использующий общие модели Graph/Node/Result. History — история принятия процессных actions, не копия task events и не durable audit.

## Устранённые нюансы

1. **Зависимость от callback для нового процесса:** готовый result принимается непосредственно. Агент выбирает объявленный outcome; target определяется политикой графа.
2. **Stale/duplicate result:** каждая мутация требует точную revision; повтор старого результата не продвигает другой узел и не создаёт второе событие.
3. **Устаревшее определение задачи:** процесс закрепляет definition_version, caller передаёт прочитанную текущую версию. Mismatch запрещён; runtime не обещает самостоятельно читать Task Manager.
4. **Потеря ответа при невалидном результате узла:** resume отдельно принимает response и оставляет его в resumed_wait/history; последующий rejected submit не уничтожает ответ.
5. **Повторное использование ожидания:** использованный wait_id запрещён даже после возврата к тому же узлу; чужой/старый wait не принимается.
6. **Неограниченный generic цикл:** общий budget по умолчанию 100 accepted results, дополнительные per-node limits. Rejected result не сбрасывает counters; cancel доступен при exhausted budget.
7. **Неоднозначный terminal/node target:** в новом пути reserved terminal имена нельзя использовать как node_id. Legacy loader не ужесточён.
8. **State не соответствует JSON:** новый путь запрещает non-finite numbers, cyclic values, tuples и нестроковые ключи; снимки изолированы от caller mutation.
9. **Конкурирующий compare-and-publish:** локальный RLock; тест с barrier одновременно подаёт два результата с revision=1, принимается один, второй получает conflict.

## Собственный code review

Проведена повторная проверка publish paths, копирования payload/history, state guards, лимитов, wait lifecycle и отделения задачи от процесса. Все сравнения и проверки нового API выполняются до замены canonical снимка; операции не запускают внешних side effects. Валидация результата отделена от semantic review и repository verification. Лимиты расходуются needs_input/blocked results, а resume не считается ещё одним result — это явно отражено в контракте.

Legacy callback подписи и сериализация проверены отдельным regression test; весь существующий preparation suite проходит. Public Task Manager integration подтверждает, что succeeded процесс не переводит created задачу в ready/active/completed, и попытки mark_ready/claim без существующих guards отклоняются. Runtime метка execution не выдаётся за разрешение исполнять задачу.

Открытых major/critical findings в этом самостоятельном review не выявлено. Независимый review sub-agent не проводился и не заявляется. Это не полный security audit tools/host и не end-to-end проверка автономного агента.

## Проверки

| Проверка | Результат |
| --- | --- |
| `python -m unittest tests.test_agent_runtime -v` | 19/19, 0.076 s |
| `python -m unittest discover -s tests -q` | 71 tests: 70 passed, 1 Windows file-symlink skip, 2.849 s |
| `python -m unittest discover -s packages/onboarding/tests -v` | 19: 18 passed, 1 Windows symlink skip, 0.576 s |
| `python -m unittest discover -s packages/task-manager/tests -v` | 73/73, 18.282 s |
| Guide Python example | Выполнен, все assertions прошли |
| `python -m compileall -q orchestrator tests` | Успешно |
| Diff Task Manager/onboarding | `git diff --name-only -- packages/task-manager packages/onboarding` пуст |

Все команды выполнены `.venv/Scripts/python.exe` из корня Windows workspace. Итого 163 tests, 161 passed, 2 skipped, 0 failures. Duration — один запуск, не benchmark. MCP/CLI Task Manager проверяются существующим пакетным suite, не новым transport runtime. Windows skip не выдается за прошедшую защитную проверку.

Проверены 255 local Markdown targets в изменённых/новых документах: отсутствующих файлов нет, anchors отдельно не проверялись. Git diff check прошёл с предупреждениями LF/CRLF. После регистрации свидетельств и закрытия run публичный live validate вернул `ok: true`, `result: []`; health_check — `[]`.

Пакет приёмки опубликован через ArtifactRepository как immutable `TASK-0028:acceptance_package:v1`, SHA-256 `532596ae4399e285ff2ba0433572c24cae96666c07ac9826acc9880bd07b4bca`. Task Manager хранит ссылку и repository metadata. Implementation/testing/code_review/documentation/readiness зарегистрированы реальными ссылками на этот отчёт. Явная приёмка нового результата не выдумывалась и complete/accept не вызывались. Общая TASK-0027 остаётся preparing, version 9, поскольку миграция продолжается.

## Ревизия кандидата

Кандидат: `agent-runtime-v1:57d8b6a7e0d7308e323d7ef68796f18a0aad4a56cf8189ad498b0e04a0b6bace`.

Digest вычислен по UTF-8 строкам `relative/path:lowercase_sha256` в указанном порядке, с LF после каждой строки. Не включает старые документационные изменения и исходные пользовательские документы.

| Файл | SHA-256 |
| --- | --- |
| orchestrator/__init__.py | 9ab43ed29686cacaf9fc65250128a638bf5cb7eb1bbc165c70575ffa5b4be60d |
| orchestrator/agent_runtime.py | 5062aff10b26ad52e1a4eab2a9eb92a9454bbc295c78b91a12403cb4e7a578d4 |
| orchestrator/workflow_runtime.py | d7146da9c58692c917041f353ecf0076d0b964530c991a6bcdcb4d1d08e0da38 |
| tests/test_agent_runtime.py | 4081204ebfa40bda7b8e94b13fce048cdcbc47490d246c536cfead037e138688 |

## Чего ещё нет и как продолжается миграция

- Нет MCP/CLI фасада нового process API и установленного Orchestrator Agent skill.
- Нет artifact publication/Task Manager sync нового пути. Generic runtime не проверяет task claim, source snapshot или semantic plan approval самостоятельно.
- Нет durable checkpoints/restart recovery, actor authorization, multiprocess scheduling и гарантий exactly-once внешних инструментов.
- Нет реализованного Project Knowledge Service/Graphify adapter, indexer, initial load/refresh, corpus fingerprint или memory store.
- Нет нового execution preflight/gates и устанавливаемого agent/core bundle.

Следующий согласованный этап — agent-driven preparation поверх существующих Artifact Repository и неизменяемого Task Manager. Затем provider contract и реальный version-pinned Graphify code-only initial integration, без глобальных hooks и отправки документов внешней модели. Старый PreparationWorkflow удаляется только после эквивалентных новых проверок, не в этом срезе.

Полная исходная [оценка архитектуры и миграционная матрица](2026-09-17-agent-centric-graphify-assessment.md) остаётся историческим baseline; этот отчёт актуализирует состояние после первого implementation этапа. Новый [контракт](../architecture/agent-runtime-contract.md), [guide](../guides/agent-runtime.md) и [roadmap](../roadmap.md) согласованы с фактическим кодом.
