# TASK-0029: агентная подготовка и состояние миграции

**Статус:** код реализован, проверен и принят пользователем; TASK-0029 completed v18, без active run/claim. Не завершение общей миграции TASK-0027. **Дата:** 2026-09-18.

<a id="user-acceptance"></a>
## Приёмка пользователем

После предъявления результата пользователь ответил «принято. продолжай дальше». До новых изменений проверены неизменные хеши пяти файлов кандидата. Публичный accept_task завершил TASK-0029 v18 для указанной ниже candidate_revision; task_completed и health_check=[] проверены. Это приёмка только preparation-среза, не будущего Knowledge Service.

После регистрации этого кандидата выполнен отдельный [реальный Graphify upstream probe](2026-09-18-graphify-upstream-probe.md); теперь TASK-0027 preparing v11. Graphify 0.9.63 доступен только во временной среде, production service/adapter по-прежнему отсутствуют. Матрица ниже фиксирует границу самого preparation-среза.

Реальные свидетельства зарегистрированы публичным Task Manager API; immutable `TASK-0029:acceptance_package:v1`, SHA-256 `dc9de54d8c9a0bcd3e02420d2e7359495eb3d36f6548f9620fb306e20597e5e6`. Health_check после регистрации — [].

## Результат

Новый AgentPreparation принимает готовые Context/Analysis/Plan/Review от агента. Общие primitives проверяют payload, публикуют immutable versions, защищают plan.md, регистрируют реальные approved review и Execution Package, закрывают preparation link и вызывают Task Manager mark_ready. Ни reasoning callbacks, ни автоматического claim/исполнения нет.

Это вторая кодовая часть миграции, после принятой TASK-0028. Теперь новый process API не остаётся изолированным runtime: он связан с реальной подготовкой и существующими guards SQLite Task Manager. Полная система исполнения и Graphify всё ещё отсутствуют.

## Что изменено

| Материал | Изменение |
| --- | --- |
| [agent_preparation.py](../../orchestrator/agent_preparation.py) | Фиксированный root, явные start/request/submit/resume/cancel, версии, pending sync, unknown effect reconciliation, guards перед ready |
| [preparation_primitives.py](../../orchestrator/preparation_primitives.py) | Выделены общие validators, graph policy, envelopes, artifact publication, projection, pending effects и публичная Task Manager синхронизация |
| [preparation_workflow.py](../../orchestrator/preparation_workflow.py) | Сохраняет legacy semantic callbacks и прежние сигнатуры, наследует общие deterministic primitives; новый путь его не вызывает |
| [Публичные импорты](../../orchestrator/__init__.py) | AgentPreparation доступен из orchestrator |
| [tests](../../tests/test_agent_preparation.py) | 23 новых предметных теста, включая реальные временные проекты и fault injection |
| [Контракт](../architecture/agent-preparation.md) / [guide](../guides/agent-preparation.md) | Русские API, инструкции агента, исполняемый пример и ограничения |
| README/status/roadmap/storage/legacy guides | Убраны заявления, что агентная подготовка ещё отсутствует; прежние сценарии явно обозначены legacy |

Пакеты Task Manager и Onboarding не менялись. Их diff пуст. Пользовательские исходные документы нового дизайна и obsolete не редактировались. Старые отчёты и принятые артефакты не перезаписываются новыми результатами.

## Проверенные нюансы

1. **Два semantic контроллера:** новый facade не получает adapters и не имеет step. Агент осмысляет request и подаёт result; код занимается политикой/структурами/effects. Legacy controller остаётся только выбранным совместимым путём.
2. **Расхождение контрактов:** common extraction вместо копирования plan/review/projection правил. Все 18 прежних сценариев подготовки сохранены.
3. **Случайный другой project root:** facade сам создаёт оба сервиса из одного проверенного root. Во временных проектах одинаковые TASK ID не приводят к записи в чужую базу.
4. **Stale и duplicate:** process revision и task version обязательны. Изменение canonical definition требует новой подготовки; cleanup текущего процесса не отменяет задачу. Два одновременных submit принимают только один result.
5. **Resume выполняет работу вместо агента:** теперь отдельный action только регистрирует ответ/разрешение и возвращает preparing. Невалидный последующий result не теряет принятый answer, включая explicit null.
6. **Затирание пользовательского плана:** postоронняя/изменённая projection даёт projection_conflict; тест подтверждает неизменные пользовательские байты. План не удаляется ради прохождения guard.
7. **Ложная готовность по метаданным:** при Ready проверяются immutable Plan/Review/Package и actual plan projection; checks повторяются перед mark_ready во время sync.
8. **Повтор после потерянного ответа:** unknown task effect блокирует synchronize. Exact history reconciliation позволяет завершить уже записанный effect без второй мутации. Проверены start, attachment Plan/Review, package, waits, run link, blocker, clarification, resolution и mark_ready.
9. **Неатомарность файлов/SQLite:** принятый result и pending effects не откатываются автоматически. После временного ready guard run может быть succeeded, а task ещё preparing; тест требует sync_pending и только после исправления допускает реальную ready.
10. **Бесконечные циклы:** сохранены review/context budgets, плюс total accepted-result budget AgentGraphRuntime. Последний исчерпанный review сохраняется как artifact вместе с owned blocker.

## Проверки

| Проверка | Результат |
| --- | --- |
| Agent preparation + legacy preparation | 41/41: 23 новых + 18 прежних |
| Root `unittest discover -s tests -q` | 94 tests, 93 passed, 1 Windows file-symlink skip, 4.481 s |
| Onboarding suite | 19 tests, 18 passed, 1 Windows symlink skip, 0.500 s |
| Task Manager suite | 73/73, 16.323 s |
| Всего | 186 tests, 184 passed, 2 skipped, 0 failures |
| Python-пример нового guide | Исполнен: TASK-0001 ready, реальные assertions и health_check=[] |
| Compileall orchestrator/tests | Успешен |
| Diff check | Успешен; только предупреждения LF/CRLF, не ошибки whitespace |
| Local Markdown targets после probe docs | 307 проверены, missing=0; anchors отдельно не проверялись |

Финальный повтор root suite после всех source assertions: 94 tests, 93 passed/1 skipped, 4.524 s; compileall также включает scripts/graphify_probe.py. Число 186 относится к unittest suites, не включает отдельный реальный upstream probe.

Эти проверки выполнены на текущей Windows-среде. Cross-platform гарантии, реальная Graphify совместимость, host/MCP permissions и restart recovery из них не следуют.

## Ревизия кандидата

`agent-preparation-v1:9da5d7d8882a564a99d5574313792aff9cdb1b20c969f6f5d453092bec0be86c`

Хеш — SHA-256 UTF-8 записей `relative/path:lowercase_sha256\n` в порядке таблицы. Относится к этому code/test срезу; исторические хеши принятого runtime сохраняют baseline до нового экспорта __init__.py.

| Файл | SHA-256 |
| --- | --- |
| orchestrator/__init__.py | 409396b774552097913af6e85daecd032d8475c8b71cefd610e0e5ef974dfe04 |
| orchestrator/agent_preparation.py | 10436361c32d5590dc5058994f33640efd9bcb48c96060c13d19a298d7722e82 |
| orchestrator/preparation_primitives.py | 171591b5812581ea5e19327bd83eca514008b9a3d35c5f83a70fe14a3aadacd1 |
| orchestrator/preparation_workflow.py | c530ac55ffb232641076154e1fb5727a98b01d072ccbbb40770759ca6eab57dd |
| tests/test_agent_preparation.py | b9057f129b999e53df275518858db650de2c041c710284e4a0a21b92640d1dd7 |

## Фактический self-review

Проверены границы semantic/deterministic, shared extraction, atomic rejection, pinning и resume retention, projection preservation, root isolation, ready без claim, результат fault injection и полнота docs. При проверке добавлен повторный immutable guard перед mark_ready; ошибки этого guard происходят до task mutation и не обозначаются unknown write. Самостоятельный review не является независимым аудитом; agent-review payload тоже не делает reviewer независимым.

Открытые ограничения ниже остаются явной частью контракта, а не скрытым заявлением production-ready. Нового внешнего code reviewer не запускалось.

## Что уже есть и чего ещё нет

| Область | Уже есть | Не реализовано / следующая работа |
| --- | --- | --- |
| Task lifecycle | Отдельный зрелый SQLite Task Manager, canonical definition, guards, claim, приёмка | Изменения пакета не требуются и запрещены текущей миграцией |
| Process policy | AgentGraphRuntime, CAS revision, declared transitions, waits, history, bounded results | Durable checkpoints, actor/host permission enforcement, external process transport |
| Preparation | Явные Context/Analysis/Plan/Review, immutable artifacts, projection, Package/Ready без claim | Installed Agent skill, автоматическая связь RequestFlow → выбранный facade, source preflight |
| Sync failures | Cursor, pending barrier, явная version reconcile и single-successor unknown outcome recovery | Durable journal, complex ambiguous multi-event recovery, общая транзакция |
| Knowledge | Принятый Project Knowledge Service/Graphify дизайн и первичная проверка upstream docs | Provider contract в коде, corpus snapshot, pinning/install, real MCP/indexer, refresh/freshness/provenance |
| Execution | Task Manager claim примитив доступен отдельно | Agent execution workflow, work units, review/tests/docs/final validation/knowledge refresh |
| Delivery | Отдельные onboarding/Task Manager пакеты | Core/Agent bundle, подключение knowledge profile, полный внешний E2E |
| Memory | Архитектурно отделена от графа | Сервис не создан; не блокирует локальный code-only Graphify |

## Ограничения и остаточные риски

- Состояние facade/effects только в памяти. При crash ссылка в задаче не позволяет восстановить current_node. Артефакты и события сохранены, но требуется аудит и новый процесс, не выдуманное continuation.
- Unknown effect после дополнительных внешних событий не восстанавливается автоматически. Definition drift при pending также требует ручного разбора; нельзя просто сбросить cursor и принять новую карточку. Это fail-closed, не полноценный journal.
- Evidence refs, source revision, zero_context_executable и approved — утверждения агента, проверяемые структурно. Нужны semantic дисциплина/инструкции и будущий execution preflight, не переименование validator в Agent.
- Публичные runtime/service атрибуты доступны Python caller; прямой обход facade не защищён host sandbox. MCP/permissions не обещаются.
- Legacy API ещё не удалён и не объявлен deprecated; удаление — отдельная миграция внешних callers после E2E, не скрытая смена сигнатур.
- Кодовые изменения остаются в рабочем дереве; новый commit кода этим срезом не создавался. Единственный ранее созданный design commit f881dda сохраняется отдельно от пользовательских изменений.

## Как мигрировать дальше

1. Для новых preparation runs использовать AgentPreparation и [протокол агента](../guides/agent-preparation.md). Старые активные callback runs не переносить посередине процесса: закончить/закрыть их явно, затем запускать новый путь с актуальной карточкой.
2. Следующий этап по roadmap — Project Knowledge Service с выбранным Graphify-Labs/graphify. Зафиксировать конкретный upstream, подтвердить local code-only indexer/MCP, source include/exclude и Windows smoke. Не считать fake provider tests реальной интеграцией.
3. После знаний — agent execution и уточнение созданных TASK-0016–0017/0019–0022 по принятому дизайну. Старые completed работы не переоткрывать, неподтверждённые unrelated задачи не закрывать автоматически.
4. Поставка portable Agent instructions, MCP facade и E2E перед удалением callback path. Checkpoints — самостоятельный срез, не изменение SQLite Task Manager.

Полная миграция TASK-0027 остаётся открытой. Этот отчёт дополняет [исходную архитектурную оценку](2026-09-17-agent-centric-graphify-assessment.md) и [принятый runtime-срез](2026-09-17-agent-runtime-v1.md), не заменяет будущую проверку Graphify и исполнения.
