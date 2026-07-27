# Task Layer Specification

## Task Creator, Task Context, Task Manager и Task Execution

**Версия:** 0.3
**Статус:** нормативная спецификация уровня задач
**Язык:** русский

## 1. Назначение

Task Layer превращает пользовательский запрос в подготовленную задачу, регистрирует её в лёгкой очереди и проводит через execution workflow.

Уровень разделён на четыре независимых компонента:

1. **Task Creator** — исследует проблему или feature и создаёт спецификацию.
2. **Task Context** — единый документ определения и выполнения задачи.
3. **Task Manager** — хранит очередь, внешний статус и ссылку на контекст.
4. **Task Execution Workflow** — выполняет подготовленный план и проверки.

Главный принцип:

> Task Manager знает, в каком состоянии находится задача, но не знает, как её выполнять.

### 1.1. Нормативность и границы

- Этот документ является источником истины для контрактов Task Layer.
- Архитектурные границы и канонический roadmap задаёт `orchestrator-specification-ru.md`.
- Task Creator является coordinator workflow: он вызывает атомарные навыки классификации, анализа, спецификации, планирования и review, но не переносит их логику в Task Manager.
- Текущий статус существует только в Task Registry; результаты этапов и evidence существуют только в Task Context.

## 2. Task Creation Workflow

Пользователь может сказать:

> Создай задачу для исправления потери сессии после refresh token.

Оркестратор не должен сразу добавлять пустую запись в backlog. Сначала запускается workflow создания задачи:

```text
User request
→ Task classification
→ Project analysis
→ Brainstorming
→ Scope definition
→ Task specification
→ Plan writing
→ Plan review
→ Context validation
→ Task Manager registration
```

### 2.1. Анализ проекта

Агент изучает:

- Project Context и активные профили;
- исходный код и похожие реализации;
- существующие тесты;
- архитектурные документы и ADR;
- ограничения безопасности;
- связанные знания и предыдущие решения.

### 2.2. Brainstorming

Brainstorming должен:

- отделить симптом от вероятной причины;
- уточнить ожидаемый результат;
- рассмотреть альтернативы;
- выявить неизвестные, риски и влияние;
- определить границы задачи;
- выявить решения, требующие пользователя.

Оркестратор обращается к capability `brainstorming`, а конкретным provider может быть SuperSpec или локальный skill.

### 2.3. Task Specification

Спецификация содержит проблему, ожидаемое поведение, выбранный подход, scope, критерии приёмки, ограничения, риски и затрагиваемые компоненты.

### 2.4. Plan Writing

Capability `implementation-planning` создаёт конкретный исполнимый план, учитывающий реальные файлы, модули, команды и тесты проекта.

Плохой шаг:

> Написать код и протестировать.

Хороший шаг:

> Разделить обработку истёкшего access token и окончательного отказа в `src/auth/token_service.py`, затем добавить регрессионный тест в `tests/auth/test_token_refresh.py`.

### 2.5. Plan Review

Plan Reviewer проверяет:

- соответствие спецификации;
- полноту шагов;
- порядок выполнения;
- тестируемость;
- security и documentation impact;
- отсутствие выхода за scope;
- отсутствие чрезмерно крупных или абстрактных шагов.

При замечаниях план возвращается Plan Writer.

### 2.6. Context Validation

До регистрации проверяется:

- понятность цели;
- проверяемость acceptance criteria;
- отсутствие критических открытых вопросов;
- согласованность scope, рисков и плана;
- достаточность контекста для новой сессии или другого агента.

## 3. Режимы создания задачи

### 3.1. Quick

Для очевидных локальных изменений:

- короткий анализ;
- цель;
- scope;
- критерии;
- краткий план;
- регистрация без обязательного пользовательского approval, если нет нерешённого продуктового или security-решения.

### 3.2. Standard

Основной режим для bugs и features:

- анализ проекта;
- brainstorming;
- спецификация;
- подробный план;
- Plan Review;
- Context Validation.

Пользовательское approval требуется только для решений, меняющих scope, внешнее поведение, безопасность или необратимые действия.

### 3.3. Deep

Для архитектурных, рискованных и неоднозначных изменений:

- глубокое исследование;
- несколько альтернатив;
- ADR impact;
- явное пользовательское approval выбранного подхода;
- подробный план и Plan Review.

Режим может выбрать оркестратор, но пользователь вправе явно потребовать `quick`, `standard` или `deep`.
Поле режима называется `mode`; оно не является оценкой размера или времени.

## 4. Task Context

Task Context создаётся как черновик до регистрации:

```text
.orchestrator/tasks/drafts/<slug>.md
```

В черновике поле `id` отсутствует или равно `null`, а заголовок не содержит фиктивный ID. После успешной валидации Task Manager выделяет ID, записывает его во frontmatter и заголовок, затем переносит документ:

```text
.orchestrator/tasks/TASK-0007.md
```

### 4.1. Контракт Task Context

```markdown
---
schema_version: 1
id: TASK-0007
revision: 1
title: Исправить потерю сессии при refresh token
type: bug
mode: standard
risk: medium
created_by: task-creation-workflow
---

# TASK-0007 — Название

## Исходный запрос

## Цель

## Проблема или потребность

## Текущее поведение

## Ожидаемое поведение

## Анализ

## Выбранный подход

## Рассмотренные альтернативы

## Объём задачи

### Входит в scope

### Не входит в scope

## Затрагиваемые компоненты

## Критерии приёмки

## Ограничения

## Риски

## План реализации

## Plan Review

## Открытые вопросы

# Execution Record

## Фактические изменения

## Тесты

## Task Review

## Code Review

## Security Review

## Решение пользователя

## Документация

## Память и граф знаний

## Итог выполнения
```

Для `standard` и `deep` обязательны все разделы до `Execution Record`, кроме разделов, неприменимость которых явно объяснена. Для `quick` обязательны «Исходный запрос», «Цель», «Объём задачи», «Критерии приёмки», «План реализации» и «Открытые вопросы»; остальные разделы можно опустить. При регистрации критические открытые вопросы запрещены, а неприменимые разделы нельзя заполнять пустыми фразами.

После регистрации определение задачи от «Исходного запроса» до «Открытых вопросов» считается baseline. Его смысловое изменение требует возврата задачи в `backlog`, увеличения revision Task Context и повторной Context Validation. Execution Record дополняется по мере выполнения.

Frontmatter использует ограниченное YAML-подмножество: один уровень уникальных scalar-полей без anchors, tags, multiline values и вложенных коллекций. Это позволяет Task Manager первой версии разбирать обязательные поля стандартной библиотекой Python; полный YAML parser не требуется.

Для `deep` draft после решения пользователя добавляется `approach_approved: true`. Context Validation и Task Manager запрещают регистрацию `deep`-задачи без этого evidence.

### 4.2. Единственный источник статуса

Текущий статус не хранится в Task Context. Единственный источник истины — Task Registry.

## 5. Task Registry

Канонический файл первой версии:

```text
.orchestrator/tasks/tasks.json
```

Пример:

```json
{
  "schema_version": 1,
  "next_id": 3,
  "tasks": [
    {
      "id": "TASK-0002",
      "title": "Реализовать Task Manager",
      "status": "in_progress",
      "context": "TASK-0002.md",
      "status_note": "Реализуется CLI",
      "created_at": "2026-07-26T12:35:00+02:00",
      "updated_at": "2026-07-26T13:10:00+02:00"
    }
  ]
}
```

JSON выбран потому, что:

- читается стандартной библиотекой Python;
- детерминированно валидируется;
- удобен для машинного вывода;
- не зависит от YAML-библиотеки;
- остаётся читаемым человеком.

`next_id` — следующий ещё не выделенный числовой идентификатор; после успешной регистрации он монотонно увеличивается и не переиспользуется после удаления или отмены задачи. Поле `context` хранит POSIX-путь относительно `.orchestrator/tasks/` и не может указывать в `drafts/` или выходить из корня. `status_note` — строка или `null`, а timestamps записываются в RFC 3339 с timezone.

Порядок массива является порядком очереди первой версии. Команды `next` и `claim-next` рассматривают только элементы со статусом `backlog`.

Task Registry является локальным operational state и исключается из Git:

```gitignore
.orchestrator/tasks/tasks.json
.orchestrator/tasks/*.tmp
.orchestrator/tasks/*.lock
```

Task Context не игнорируется и остаётся версионируемым. История operational-статусов в первой версии не хранится; Git фиксирует baseline, Execution Record и результаты реализации, но не переходы `tasks.json`.

## 6. Task Manager

Task Manager отвечает только за:

- регистрацию готового Task Context;
- генерацию ID;
- список и чтение задач;
- выбор следующей задачи;
- single-writer взятие задачи;
- проверку переходов;
- изменение статуса;
- краткий status note;
- проверку целостности registry.

Task Manager не выполняет:

- brainstorming;
- planning;
- implementation;
- tests;
- reviews;
- documentation update;
- memory update;
- commits.

## 7. Статусы

Минимальный набор:

- `backlog` — подготовленная задача доступна;
- `in_progress` — оркестратор выполняет задачу;
- `waiting_user` — требуется решение или review пользователя;
- `blocked` — продолжение невозможно;
- `done` — завершён полный workflow;
- `cancelled` — задача отменена.

Planning, testing, code review и security review являются этапами workflow, а не статусами Task Manager.

### 7.1. Переходы

```text
backlog → in_progress
backlog → cancelled

in_progress → waiting_user
in_progress → blocked
in_progress → done
in_progress → cancelled

waiting_user → in_progress
waiting_user → blocked
waiting_user → cancelled

blocked → backlog
blocked → in_progress
blocked → cancelled
```

`done` и `cancelled` терминальны в первой версии.

Переход `waiting_user → done` запрещён: после пользовательского решения оркестратор возвращает задачу в `in_progress`, завершает документацию, память, commit и только затем ставит `done`.

Task Manager проверяет только допустимость перехода и структурную целостность. Перед вызовом `complete` execution workflow обязан подтвердить выполнение acceptance criteria и обязательных gates в Execution Record; Task Manager не подменяет semantic review.

## 8. Правило одной активной задачи

Первая версия использует:

```json
{
  "single_active_task": true,
  "continue_backlog_while_waiting_user": false
}
```

Слот выполнения занимают `in_progress` и, при `continue_backlog_while_waiting_user: false`, `waiting_user`. `blocked` не занимает слот, однако переход `blocked → in_progress` запрещается, пока слот занят другой задачей. Первая версия рассчитана на одного разработчика и один изменяющий Task Manager process; конкурентные writers не поддерживаются. Параллельность и межпроцессная блокировка добавляются только после появления подтверждённой необходимости.

## 9. Task Manager CLI

Предпочтительный интерфейс:

```bash
python .orchestrator/bin/task.py <command>
```

### 9.1. Команды

```bash
python .orchestrator/bin/task.py register --context drafts/task.md
python .orchestrator/bin/task.py list
python .orchestrator/bin/task.py list --json
python .orchestrator/bin/task.py show TASK-0003
python .orchestrator/bin/task.py next --json
python .orchestrator/bin/task.py claim-next --json
python .orchestrator/bin/task.py status TASK-0003 waiting_user --note "..."
python .orchestrator/bin/task.py block TASK-0003 --note "..."
python .orchestrator/bin/task.py resume TASK-0003
python .orchestrator/bin/task.py complete TASK-0003
python .orchestrator/bin/task.py cancel TASK-0003
python .orchestrator/bin/task.py validate --json
```

`claim-next` в рамках одного CLI process выбирает первую `backlog`-задачу, проверяет отсутствие активной задачи, переводит её в `in_progress`, crash-safe сохраняет registry и возвращает путь к Task Context. Одновременный запуск двух изменяющих команд находится вне контракта первой версии.

`register` берёт title из проверенного frontmatter черновика. `status` изменяет только нетерминальные статусы с тем же валидатором переходов; `block`, `resume`, `complete` и `cancel` — безопасные специализированные команды, причём только `complete` и `cancel` могут устанавливать терминальный статус. `resume` переводит `waiting_user` или `blocked` в `in_progress`; для возврата заблокированной задачи в очередь используется `status TASK-ID backlog`.

### 9.2. Машинный вывод

Успех:

```json
{
  "ok": true,
  "task": {
    "id": "TASK-0003",
    "status": "in_progress",
    "context": ".orchestrator/tasks/TASK-0003.md"
  }
}
```

Ошибка:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_TRANSITION",
    "message": "Transition from done to in_progress is not allowed"
  }
}
```

### 9.3. Exit codes

- `0` — успех;
- `1` — общая ошибка;
- `2` — задача не найдена;
- `3` — недопустимый переход;
- `4` — registry повреждён;
- `5` — уже есть активная задача;
- `6` — доступных задач нет.

### 9.4. Надёжность записи

Скрипт использует только Python standard library:

1. читает registry и валидирует инварианты;
2. валидирует структуру и переход;
3. пишет временный файл в том же каталоге;
4. выполняет flush/fsync;
5. заменяет основной файл через `os.replace`;
6. удаляет оставшийся временный файл в `finally`, если публикация не состоялась.

`os.replace` обеспечивает crash-safe публикацию файла, но не сериализует конкурентные read-modify-write операции. Регистрация изменяет Task Context и registry как одну восстанавливаемую single-writer операцию: при обычной ошибке выполняется rollback, а после аварийного завершения `validate` сообщает об orphan context или зарегистрированной записи без context и не исправляет её автоматически.

Агент не редактирует `tasks.json` вручную, если CLI доступен.

## 10. Task Execution Workflow

Execution получает уже подготовленный Task Context:

```text
claim-next
→ read context
→ validate context freshness
→ implement plan
→ design/run tests
→ task review when required by mode/risk
→ code review when required by mode/risk
→ security review
→ user review when required
→ documentation
→ memory and knowledge
→ commit
→ complete
```

Freshness, implementation, tests и Security Review обязательны для каждого маршрута. `quick` low/medium-risk task не запускает semantic Task Review и Code Review, если нет security-sensitive или другого escalation signal; `standard` запускает оба review, а `deep` и high/critical-risk task требуют независимого review. Approval и documentation добавляются только при соответствующем impact.

При замечании review выполнение возвращается к реализации. При необходимости решения пользователя ставится `waiting_user`. При невозможности продолжать — `blocked` с причиной. Execution evidence каждой попытки ограничивается по размеру, а число попыток шага имеет жёсткий верхний предел; полный диагностический output хранится отдельным artifact с source pointer, а checkpoint сохраняет компактные head/tail, длину и digest. Execution Record финализируется до commit; после успешного commit `complete` изменяет только незатреканный Task Registry.

Числовая execution telemetry является локальным operational state и не является источником статуса, определения задачи или review evidence. Она не хранит prompt/evidence payload и может отсутствовать, если platform provider не сообщает usage counters.

## 11. Backlog Loop

```text
while limit not reached:
    task = claim-next()
    if no task: stop
    result = execute task workflow
    if result is waiting_user or blocked: stop
    if result is done: continue
    stop with workflow error
```

Цикл обязан иметь:

- лимит задач;
- лимит времени или шагов;
- stop conditions;
- commit per task;
- отдельный результат каждой задачи;
- session report после завершения.

## 12. Platform Adaptation

Основной интерфейс одинаков для разных платформ:

```yaml
task_manager:
  mode: cli
  command: python .orchestrator/bin/task.py
  supports_shell: true
```

Для платформ без shell допускается `direct_file` fallback, но агент обязан самостоятельно выполнить все validations. CLI остаётся предпочтительным путём.

## 13. Health Check для Task Layer

Health Check проверяет:

- JSON schema registry;
- уникальность ID;
- допустимость статусов;
- наличие Task Context;
- корректность относительных путей;
- согласованность `next_id`;
- не более одной задачи, занимающей слот выполнения;
- отсутствие зарегистрированных draft-файлов;
- отсутствие orphan context и записей без context;
- доступность CLI и Python;
- наличие правил `.gitignore` для Task Registry и временных файлов;
- соответствие конфигурации переходов.

## 14. Тестовая стратегия

### Unit tests

- генерация ID;
- переходы;
- регистрация;
- crash-safe write через `os.replace`;
- последовательный `claim-next`;
- rollback/recovery регистрации и аварийной записи;
- JSON output;
- exit codes.

### Contract tests

- registry schema;
- Task Context contract;
- config schema;
- skill and workflow contracts.

### Scenario tests

- создание quick-задачи;
- standard creation с Plan Review;
- пустой backlog;
- `claim-next`;
- попытка второй активной задачи;
- waiting user и resume;
- blocker и recovery;
- повреждённый JSON;
- отсутствующий context;
- полный small workflow до `done`.
- quick/standard/deep route selection с обязательным Security Review;
- bounded evidence и telemetry без payload leakage.

Каждая найденная ошибка превращается в regression test.

## 15. Roadmap Task Layer

### T0 — Контракты

Task Registry schema, Task Context contract, статусы и переходы.

### T1 — Read-only Task Manager

`list`, `show`, `next`, `validate`.

### T2 — Registration

Генерация ID, перенос draft и создание записи.

### T3 — State Management

`claim-next`, `status`, `block`, `resume`, `complete`, crash-safe single-writer writes.

### T4 — Quick Task Creator

Короткая спецификация и план для простых задач.

### T5 — Standard Task Creator

Анализ проекта, brainstorming, specification и Plan Writer.

### T6 — Plan Review и Context Validation

Обязательная проверка standard/deep задач до регистрации.

### T7 — Execution Integration

Сквозной workflow от `claim-next` до `done`.

### T8 — Backlog Loop

Конечная последовательная обработка задач.

### T9 — Platform Validation

Последовательная проверка на OpenAI Codex, Google Antigravity, GitHub Copilot VS Code и Claude VS Code, а также минимум на двух технологических стеках.

Этапы `T0–T9` уточняют фазы канонического roadmap из `orchestrator-specification-ru.md`; таблица соответствия находится в разделе 12.1 основной спецификации. Они не ведутся как отдельный параллельный backlog.

## 16. Не входит в первую версию

- SQLite и внешняя БД;
- web UI и Kanban;
- несколько исполнителей;
- сложные зависимости и подзадачи;
- оценки времени;
- отдельный event log;
- GitHub Issues synchronization;
- параллельное выполнение;
- конкурентные Task Manager writers, межпроцессная блокировка и stale-lock recovery;
- автоматическое исправление содержимого Task Context.

Task Context и Git предоставляют историю определения и реализации задачи. История operational-статусов в первой версии намеренно не сохраняется; отдельный event log можно добавить как независимую capability.
