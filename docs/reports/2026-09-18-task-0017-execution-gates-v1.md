# TASK-0017 — execution gates и финальная приёмка

**Дата:** 2026-09-18.  **Статус:** кандидат реализации v1.

## Реализовано

- Добавлен `execution_gates-v1`: code review, testing, documentation, knowledge
  refresh и final validation как отдельные explicit agent results.
- Gate run использует `AgentGraphRuntime`, process CAS, task definition binding,
  execution package/source/candidate guards и immutable Artifact Repository evidence.
- Readiness требует согласованных revisions, полного acceptance criteria trace,
  пустых blocking findings, валидного knowledge policy и acceptance package.
- Успешный путь закрывает gate run и публичным Task Manager API переводит задачу в
  `awaiting_acceptance`; explicit `accept_task` завершает её только для текущего
  candidate. Task Manager code/schema не менялись.
- Негативные review/testing/docs/knowledge исходы сохраняются, но readiness не
  получают; `release_gates` возвращает задачу на явную remediation.

## Проверки

Добавлены сценарии на успешный lifecycle с атомарной acceptance, `changes_required`
и required knowledge с `degraded`. Существующие AgentExecution/KnowledgeRefreshNode
регрессии сохранены.

Запуск:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_agent_execution -v
```

Результат нового среза: 3 gate-сценария и прежние execution tests проходят; полный
набор проекта будет зафиксирован после финального прогона. Ограничения: process
state in-memory, restart recovery отсутствует, final check не запускает tests и не
выполняет Git commit, semantic review остаётся ответственностью агента.
