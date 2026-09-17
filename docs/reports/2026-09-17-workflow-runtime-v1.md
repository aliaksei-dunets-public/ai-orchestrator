# TASK-0003: минимальный in-memory Workflow Runtime v1

**Статус:** аудит завершён, замечания исправлены, задача принята и завершена (Task Manager version 22).  
**Объём:** один граф, одна real-time сессия, состояние только в памяти.

## Реализовано

- `orchestrator.workflow_runtime` с публичными `GraphRuntime`, `Graph`, `Node`, `WorkflowRun`, `NodeResult`, `WaitState` и структурированной ошибкой `RuntimeError`;
- проверка graph/node contract, уникальности узлов, entry node и переходов;
- `create_run`, `inspect_run`, `step`, `resume`, `resume_blocked`, `cancel`;
- ровно один узел на вызов `step`;
- детерминированные переходы и terminal states `succeeded`, `failed`, `cancelled`;
- pause/resume через `needs_input`, `WaitState`, `wait_id` и проверку текущего узла;
- blocked state с явным `resume_blocked`, node mismatch, stale wait, unknown outcome, contract violation и execution failure;
- атомарная публикация состояния: невалидный результат при `resume` не теряет ожидание и допускает безопасный повтор;
- deep-copy входов, снимков и принятых результатов, чтобы внешний код не мог случайно изменить внутреннее состояние запуска;
- структурная проверка артефактов (`ref`, `contract`, `role`, SHA-256 и `value`/`uri`); семантические input/output-схемы остаются ответственностью вызывающей стороны;
- экспорт основных классов через `orchestrator`.

## Границы

Runtime не создаёт SQLite, не пишет Task Manager напрямую, не содержит Executor Loop, фоновых workers, многосессионности, checkpoints или автоматического восстановления. Исполнитель узла передаётся вызывающей стороной; runtime проверяет его результат и выбирает маршрут.

## Проверки

- `tests/test_workflow_runtime.py`: 10 сценариев, включая переходы, pause/resume, атомарный повтор, `resume_blocked`, stale wait, блокировку, отмену, ошибки контракта, дубликаты/некорректные узлы, структурированные артефакты и глубокую изоляцию;
- корневой Orchestrator: **15/15**;
- Task Manager: **73/73**;
- Onboarding: **19 тестов, 1 ожидаемый skip** на Windows symlink.
- `compileall -q orchestrator tests`: успешно;
- `git diff --check`: успешно, только предупреждения о смешанном LF/CRLF;
- `orchestrator-tasks --project . validate`: успешно (`ok: true`).

## Независимый аудит

Независимый read-only аудит выполнен отдельным агентом на `gpt-5.6-terra` с высоким уровнем рассуждений. P0 не найдено. Исправлены все выявленные замечания P1–P3:

- `resume` теперь атомарен: невалидный результат не переводит ожидание в промежуточное состояние и допускает повтор;
- добавлен `resume_blocked` с проверкой `wait_id`/`node_id`;
- входы, snapshots и принятые результаты глубоко копируются;
- загрузчик графа отклоняет дубликаты и malformed nodes структурированной ошибкой;
- добавлена минимальная структурная проверка Artifact (`ref`, `contract`, `role`, 64-значный `sha256`, `value`/`uri`);
- дизайн и контракт приведены к фактическому API `NodeResult | WaitState`; семантические input/output-схемы явно оставлены вызывающей стороне.

По итогам исправлений аудиторский вывод: P0/P1/P2/P3 замечаний не осталось. Новая ревизия принята через публичный Task Manager API; TASK-0003 завершена.

Интеграция runtime с Task Manager, Artifact Repository и сквозной release-readiness остаются в следующих задачах (`TASK-0014+`). Пользовательский guide добавлен в рамках TASK-0004.
