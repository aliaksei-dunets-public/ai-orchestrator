# Execution Gates и финальная приёмка

**Статус:** реализованный Python-контракт TASK-0017, 2026-09-18. [Guide](../guides/execution-gates.md), [отчёт](../reports/2026-09-18-task-0017-execution-gates-v1.md).

## Граница

После `AgentExecution.submit(..., {"outcome": "handoff"})` work-unit runtime
завершён, но задача остаётся `active` с собственным claim. Это не означает
пользовательскую приёмку. `start_gates()` создаёт отдельный in-memory gate run и
привязывает его к той же задаче через публичный Task Manager API.

Последовательность узлов:

```text
code_review → testing → documentation → knowledge_refresh → final_validation
```

Агент подаёт результаты review, tests и documentation; ядро не вызывает LLM,
тестовый runner и не редактирует файлы. Каждая принятая envelope проверяется по
структурному контракту и сохраняется в Artifact Repository как immutable JSON.
Для `code_review`, `testing`, `documentation`, `readiness` и `acceptance_package`
ссылка также регистрируется через `TaskManagerService.attach_artifact`.

## Guards

Gate session фиксирует task definition version, execution package ref, code-corpus
source revision и candidate revision. Каждый вызов требует текущие process/task
versions, собственный claim и active gate run. Source drift закрывает дальнейшее
движение; старые review/test/docs evidence нельзя выдать за текущий candidate.

`changes_required`, `failure`, `blocked`, `stale`, `fallback_required` и
`awaiting_confirmation` не ведут к readiness. `source_adjacent_changed=true` в
documentation требует отдельного delta review и также запрещает текущий readiness.

## Knowledge policy

`refresh_knowledge()` делегирует `KnowledgeRefreshNode`. `knowledge_required=False`
разрешает только `success`/`not_required` и диагностируемый `degraded`; последний
попадает в warnings. При required policy допускаются только `success`/`not_required`.
Stale/failed/fallback/confirmation всегда остаются denial. Full refresh с
authorization `required` использует обычный runtime wait/resume; молчаливого full
fallback нет.

## Подтверждение knowledge refresh

Knowledge stage использует стандартный runtime outcome `needs_input` с
WaitState user_input; доменный status остаётся `awaiting_confirmation`.
`refresh_knowledge` принимает explicit decision, возобновляет точный wait и
повторно исполняет KnowledgeRefreshNode. Сохранённый request нельзя менять
при активной паузе; отсутствие request при продолжении использует сохранённый.
Одобрение требует decision ref, отказ не запускает full refresh. Состояние,
request/decision и remaining result budget проверяются до вызова service.

Knowledge evidence получает immutable version `v<revision перед submit>`.
Пауза, повторный запрос и завершение имеют отдельные versions; role/ref остаются
прежними, snapshot указывает актуальную версию. Доменный status проверяется
readiness policy отдельно от runtime outcome. [Продолжение](../guides/execution-gates.md).

## Readiness и acceptance

`final_validation` не повторяет review и не запускает тесты. Он проверяет четыре
совпадающие revisions, knowledge status/policy, пустые blocking findings, полное
покрытие acceptance criteria и явные пользовательские сценарии. При `ready` gate
run закрывается, публикуются `readiness` и `acceptance_package`, а Task Manager
атомарно переводит задачу в `awaiting_acceptance`.

Только явный `TaskManagerService.accept_task()` с текущим candidate revision
завершает задачу. Отклонение или дополнительная проверка не трактуются как
автоматическое завершение; remediation начинается новым явным циклом.

## Ограничения v1

Process state и gate sessions хранятся в памяти; durable restart/recovery и
межсессионная координация не реализованы. Общей транзакции runtime, файлов,
Artifact Repository и Task Manager нет: при ошибке синхронизации нужно читать
карточку/историю и выполнять только явную reconciliation. Git commit gates не
выполняют commit.
