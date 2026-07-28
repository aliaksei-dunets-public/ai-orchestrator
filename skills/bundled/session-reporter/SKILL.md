---
name: session-reporter
description: Формировать компактный отчёт сессии из структурированных изменений, проверок, решений, рисков и следующих действий; редактировать credentials до записи и не сохранять пустые секции. Использовать после остановки task execution или backlog loop.
---

# Session Reporter

After evidence is validated, build structured, secret-safe candidates with
`orchestrator.session_report.session_memory_candidates`. Candidates remain
proposals; never bypass source-authority or approval policy.

1. Получить только подтверждённые дельты текущей сессии.
2. Передать данные в `orchestrator.session_report.render_session_report`.
3. Проверить отсутствие secrets и пустых секций.
4. Сохранить отчёт только после успешной redaction.
5. Вернуть путь отчёта и краткий summary; не менять Task Registry.
6. Invoke this skill once after execution or backlog stops. Persist session-derived
   memory only as idempotent proposals; because a session report is
   non-authoritative, never auto-promote its candidates and never retroactively
   change an already completed task status.
