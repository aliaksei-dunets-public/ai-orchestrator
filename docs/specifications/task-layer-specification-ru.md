# Task Layer Specification

## Task Creator, Task Context, Task Manager и Task Execution

**Версия:** 0.2  
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
- регистрация без обязательного пользовательского approval.

### 3.2. Standard

Основной режим для bugs и features:

- анализ проекта;
- brainstorming;
- спецификация;
- подробный план;
- Plan Review;
- Context Validation.

### 3.3. Deep

Для архитектурных, рискованных и неоднозначных изменений:

- глубокое исследование;
- несколько альтернатив;
- ADR impact;
- обязательное пользовательское решение;
- подробный план и Plan Review.

Режим может выбрать оркестратор, но пользователь вправе явно потребовать `quick`, `standard` или `deep`.

## 4. Task Context

Task Context создаётся как черновик до регистрации:

```text
.orchestrator/tasks/drafts/<slug>.md
```

После успешной валидации Task Manager выделяет ID и переносит документ:

```text
.orchestrator/tasks/TASK-0007.md
```

### 4.1. Контракт Task Context

```markdown
---
id: TASK-0007
title: Исправить потерю сессии при refresh token
type: bug
size: standard
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

Не каждый раздел обязателен для quick-задачи. Task Context — контракт результата, а не форма, которую нужно механически заполнить пустыми фразами.

### 4.2. Единственный источник статуса

Текущий статус не хранится в Task Context. Единственный источник истины — Task Registry.

## 5. Task Registry

Рекомендуемый файл:

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

Порядок массива является порядком очереди первой версии.

## 6. Task Manager

Task Manager отвечает только за:

- регистрацию готового Task Context;
- генерацию ID;
- список и чтение задач;
- выбор следующей задачи;
- атомарное взятие задачи;
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

## 8. Правило одной активной задачи

Первая версия использует:

```json
{
  "single_active_task": true,
  "continue_backlog_while_waiting_user": false
}
```

Это упрощает восстановление, историю Git и работу одного разработчика. Параллельность добавляется только после появления реальной необходимости.

## 9. Task Manager CLI

Предпочтительный интерфейс:

```bash
python .orchestrator/bin/task.py <command>
```

### 9.1. Команды

```bash
task.py register --title "..." --context drafts/task.md
task.py list
task.py list --json
task.py show TASK-0003
task.py next --json
task.py claim-next --json
task.py status TASK-0003 waiting_user --note "..."
task.py block TASK-0003 --note "..."
task.py resume TASK-0003
task.py complete TASK-0003
task.py cancel TASK-0003
task.py validate --json
```

`claim-next` атомарно выбирает первую `backlog`-задачу, проверяет отсутствие активной задачи, переводит её в `in_progress`, сохраняет registry и возвращает путь к Task Context.

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

1. читает registry;
2. валидирует структуру и переход;
3. пишет временный файл;
4. выполняет flush/fsync;
5. заменяет основной файл через `os.replace`.

Агент не редактирует `tasks.json` вручную, если CLI доступен.

## 10. Task Execution Workflow

Execution получает уже подготовленный Task Context:

```text
claim-next
→ read context
→ validate context freshness
→ implement plan
→ design/run tests
→ task review
→ code review
→ security review
→ user review when required
→ documentation
→ memory and knowledge
→ commit
→ complete
```

При замечании review выполнение возвращается к реализации. При необходимости решения пользователя ставится `waiting_user`. При невозможности продолжать — `blocked` с причиной.

## 11. Backlog Loop

```text
while limit not reached:
    task = claim-next()
    if no task: stop
    execute task workflow
    if waiting_user or critical blocker: stop
    update docs, memory and knowledge
    commit task
    mark done
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
- не более одной активной задачи;
- отсутствие зарегистрированных draft-файлов;
- доступность CLI и Python;
- соответствие конфигурации переходов.

## 14. Тестовая стратегия

### Unit tests

- генерация ID;
- переходы;
- регистрация;
- atomic write;
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

Каждая найденная ошибка превращается в regression test.

## 15. Roadmap Task Layer

### T0 — Контракты

Task Registry schema, Task Context contract, статусы и переходы.

### T1 — Read-only Task Manager

`list`, `show`, `next`, `validate`.

### T2 — Registration

Генерация ID, перенос draft и создание записи.

### T3 — State Management

`claim-next`, `status`, `block`, `resume`, `complete`, atomic writes.

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

Проверка минимум на двух агентных платформах и двух технологических стеках.

## 16. Не входит в первую версию

- SQLite и внешняя БД;
- web UI и Kanban;
- несколько исполнителей;
- сложные зависимости и подзадачи;
- оценки времени;
- отдельный event log;
- GitHub Issues synchronization;
- параллельное выполнение;
- автоматическое исправление содержимого Task Context.

Git предоставляет историю изменений, поэтому отдельный подробный audit log Task Manager пока не требуется.
