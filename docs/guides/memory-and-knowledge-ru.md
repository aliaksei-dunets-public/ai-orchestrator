# Память и граф знаний оркестратора

## Назначение

Этот guide объясняет, как Project Memory и Knowledge Graph участвуют в работе оркестратора: от получения пользовательской задачи до обновления контекста для следующих задач.

Память и граф решают разные задачи:

- **Memory** хранит наблюдения, решения, уроки и явно подтверждённые инструкции.
- **Knowledge Graph** хранит структурированные сущности проекта и связи между ними.
- **Retrieval** выбирает только релевантную и актуальную часть этих данных и формирует ограниченный Context Pack для агента.

Контракт реализации описан в [спецификации оркестратора](../specifications/orchestrator-specification-ru.md), workflow задач — в [спецификации Task Layer](../specifications/task-layer-specification-ru.md), а архитектурное решение — в [ADR-0002](../adr/0002-project-memory-knowledge-lifecycle.md).

## 1. Пользователь приходит с задачей

Пример запроса:

> Добавить endpoint `/reports`, использовать существующую RBAC-модель и покрыть функциональность тестами.

Оркестратор не начинает изменение кода непосредственно из текста запроса. Сначала Task Creation Workflow формирует Task Context:

- цель и ожидаемый результат;
- текущую проблему;
- входящий и исключённый scope;
- затрагиваемые компоненты;
- ограничения и риски;
- критерии приёмки;
- пошаговый план;
- открытые вопросы.

Режим выбирается по сложности и риску:

| Режим | Назначение | Context Pack |
|---|---|---:|
| `quick` | небольшая задача с низким риском | 2048 символов |
| `standard` | обычная инженерная задача | 6144 символа |
| `deep` | архитектурная или рискованная задача | 12288 символов |

`deep`-задача не регистрируется без явного approval выбранного подхода.

## 2. Перед анализом строится свежий Context Pack

Перед созданием Task Context и перед выполнением задачи оркестратор заново строит Context Pack. В запрос retrieval входят:

- текст задачи;
- затрагиваемые пути;
- дополнительные термины;
- выбранный режим и его лимит.

Retrieval читает canonical stores:

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

Для каждой записи проверяются актуальность источника и безопасность. Из retrieval исключаются:

- отключённые записи;
- записи, заменённые через `supersedes`;
- записи с изменившимся source digest;
- secret-like содержимое;
- источники за пределами проекта;
- `.git`, `.env`, `secrets`, `credentials` и `releases`.

Текущий retrieval локальный и детерминированный. Он не использует embeddings, внешнюю базу или cross-project memory:

1. текст запроса разбивается на нормализованные термины;
2. memory entries и graph nodes получают lexical score;
3. релевантные записи сортируются стабильно по score и ID;
4. к релевантным узлам добавляются связанные узлы максимум на два перехода;
5. в общий бюджет добавляются nodes и edges;
6. pack ограничивается бюджетом и максимумом 32 записей.

Если подходящей информации нет, пустой Context Pack является нормальным результатом. Оркестратор не заменяет отсутствие данных догадками.

## 3. Что получает агент

Для задачи про `/reports` Context Pack может содержать такие сведения.

### Memory

```text
decision:
RBAC для API реализуется через существующий AuthorizationService.
source: docs/adr/0010-api-authorization.md
```

### Knowledge Graph

```text
component: reports-api
contract: report-contract
component: authorization-service

reports-api implements report-contract
reports-api depends_on authorization-service
```

Memory отвечает на вопросы «что уже решили?» и «какие уроки нужно учитывать?». Граф отвечает на вопросы «какие сущности существуют?» и «как они связаны?». Оба источника дополняют, но не заменяют первичные файлы проекта и Task Context.

Pack содержит также:

- `query_digest` — отпечаток запроса;
- `store_digest` — состояние canonical stores на момент сборки;
- `used_chars` и `budget_chars`;
- выбранные memory entries;
- выбранные nodes и edges.

Лимит считается по сериализованному pack, а не напрямую по токенам модели. Фактическое потребление зависит от модели, языка и JSON-структуры.

## 4. Регистрация и выполнение задачи

После retrieval Task Context регистрируется в Task Manager. Для примера он фиксирует:

```text
Scope:
- добавить /reports;
- использовать AuthorizationService;
- добавить unit и scenario tests.

Out of scope:
- менять модель ролей;
- менять публичный контракт авторизации;
- добавлять новую identity system.

Acceptance:
- endpoint доступен только разрешённым ролям;
- неавторизованный запрос получает ожидаемый ответ;
- существующие тесты проходят;
- новые тесты проходят.
```

Execution Workflow выглядит так:

```text
claim task
→ read Task Context
→ validate freshness
→ retrieve fresh Context Pack
→ implement plan
→ run tests
→ task/code review по режиму и риску
→ security review
→ documentation
→ session report
→ memory candidates
→ commit
→ complete
```

Каждый шаг имеет ограниченное число попыток и ограниченное evidence. Checkpoint используется для восстановления выполнения, но является operational state и не попадает в Git.

Если во время работы меняется scope, требуется решение пользователя или появляется security-impact, workflow останавливается в `waiting_user` либо `blocked`. Он не принимает существенное решение молча.

## 5. Session Report и кандидаты памяти

После выполнения Session Reporter формирует отчёт с секциями:

- Changes;
- Validation;
- Decisions;
- Risks;
- Next actions.

До записи отчёта секреты редактируются. Кандидаты памяти извлекаются так:

| Секция отчёта | Тип memory | Базовая confidence |
|---|---|---:|
| Decisions | `decision` | 1.0 |
| Validation | `lesson` | 0.8 |
| Changes | `observation` | 0.7 |

Например:

```text
kind: lesson
content: RBAC следует проверять до формирования ответа endpoint.
confidence: 0.8
requires_approval: true
```

Кандидат ещё не является canonical memory. Он сохраняется в operational proposals:

```text
.orchestrator/memory/proposals/proposals.jsonl
```

Workflow не публикует кандидата в `entries.jsonl` автоматически.

## 6. Approval и promotion в Memory

Каждый proposal получает hash, рассчитанный по типу, содержимому, источнику, digest источника, confidence и supersede-связи.

Promotion без дополнительного approval разрешён только для данных из неизменившихся авторитетных источников:

- спецификация;
- принятый ADR;
- завершённый Task Context;
- approved review.

Пользовательская инструкция, обычный Session Report и любой другой non-authoritative source требуют explicit approval. Тип `instruction` всегда требует approval.

Approval привязывается к:

- `proposal_hash`;
- `source_digest`;
- решению `approve` или `reject`;
- actor;
- собственному `approval_hash`.

Если исходный файл был изменён, старое approval становится stale и не может примениться к новому содержимому.

После успешного promotion появляются:

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/memory/approvals.jsonl
```

Memory append-only. Исправление выполняется через lifecycle events:

- `disable` — выключить ошибочную или больше не применимую запись;
- `supersede` — связать старую запись с заменяющей.

В effective memory попадают только включённые и не superseded entries.

## 7. Knowledge Graph

Граф не должен превращаться в автоматическую свалку всех фраз из диалогов. Узлы и связи добавляются на основании конкретных source-файлов через knowledge-curator или CLI.

При первичном onboarding именно `knowledge-curator` выполняет read-only
инвентаризацию и возвращает `knowledge_graph` proposal. `project-onboarding`
включает этот proposal в общий preview и `plan_hash`; до approval пользователя
canonical nodes и edges не записываются. После approval graph применяется вместе
с остальными onboarding changes и участвует в общем rollback. Пустой proposal
является корректным no-op.

Canonical graph stores:

```text
.orchestrator/knowledge/ontology.json
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

Core ontology содержит стандартные node kinds:

```text
document
component
contract
decision
task
risk
```

и relations:

```text
defined_by
depends_on
implements
affects
supersedes
produced_by
```

Каждый node и edge получает provenance:

- source path;
- SHA-256 digest источника;
- kind или relation;
- enabled state;
- supersede-связь при необходимости.

Проектная ontology может только добавлять совместимые identifiers и не может конфликтовать с core ontology.

Если узел заменён, старые edges к нему перестают быть эффективными. Если edge указывает на неизвестный или неэффективный node, это ошибка в данных, а не молчаливое удаление связи.

Индексы строятся из canonical stores:

```text
.orchestrator/knowledge/indexes/
```

Они являются производными и игнорируются Git.

## 8. Следующая задача

После promotion следующая задача получает новый fresh Context Pack. Например, задача «добавить CSV-экспорт отчётов» может увидеть:

```text
decision: все API endpoints используют AuthorizationService
component: reports-api
reports-api depends_on authorization-service
lesson: RBAC проверяется до формирования ответа
```

Если исходный ADR, контракт или другой source изменился, старые записи исключаются retrieval как stale. Их необходимо обновить новой записью или supersede через подтверждённый источник.

## 9. Git-политика

В Git хранятся проверенные canonical stores:

```text
.orchestrator/memory/entries.jsonl
.orchestrator/memory/events.jsonl
.orchestrator/memory/approvals.jsonl
.orchestrator/knowledge/ontology.json
.orchestrator/knowledge/nodes.jsonl
.orchestrator/knowledge/edges.jsonl
```

В Git не попадают:

```text
.orchestrator/tasks/tasks.json
.orchestrator/tasks/checkpoints/
.orchestrator/memory/proposals/
.orchestrator/knowledge/indexes/
.orchestrator/migrations/backups/
.orchestrator/releases/
releases/
.agents/
```

Это разделяет проверенное проектное знание и локальное operational state.

## 10. Практические CLI-операции

Получить bounded Context Pack:

```powershell
python -m orchestrator context --root . --mode standard --task-context "Добавить endpoint /reports" --path orchestrator/reports.py
```

Создать memory proposal:

```powershell
python -m orchestrator memory --root . propose --kind lesson --content "RBAC проверяется до формирования ответа" --source reports/session.md --confidence 0.8
```

Посмотреть effective memory:

```powershell
python -m orchestrator memory --root . list
```

Добавить узел графа:

```powershell
python -m orchestrator knowledge --root . add-node --id reports-api --kind component --label "Reports API" --source docs/specifications/api-contract.md
```

Перестроить производные индексы:

```powershell
python -m orchestrator knowledge --root . rebuild
```

Для promotion proposal требуется найти его hash, создать hash-bound approval и только затем выполнить promotion. CLI и ядро отклоняют stale approval, неизвестный source, секретное содержимое и попытку записать instruction без approval.

## 11. Типовые остановки и ошибки

| Ситуация | Поведение |
|---|---|
| Нет релевантной памяти | Пустой Context Pack, работа продолжается по первичным источникам |
| Source изменился | Запись исключается как stale |
| Нет необходимого approval | Promotion не выполняется |
| Proposal или approval изменён | Hash validation отклоняет операцию |
| Секрет в memory candidate | Кандидат не публикуется |
| Source за пределами проекта | Операция отклоняется |
| Dangling edge или supersede cycle | Ошибка данных, требуется исправление |
| Изменился Task Context | Execution останавливается на freshness check |
| Требуется продуктовый выбор | Статус `waiting_user` |

## 12. Границы текущей реализации

Текущая версия намеренно не использует:

- embeddings и vector search;
- внешнюю базу знаний;
- общую память между проектами;
- автоматическое изменение собственного ядра;
- автоматическую публикацию всех наблюдений в canonical memory.

Такой дизайн делает retrieval воспроизводимым, ограничивает расход контекста, сохраняет provenance и оставляет окончательное решение о долговременной памяти за approval workflow.
