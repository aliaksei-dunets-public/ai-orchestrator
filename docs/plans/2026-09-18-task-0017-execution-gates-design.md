# TASK-0017 — дизайн execution gates и финальной приёмки

**Статус:** реализация v1, 2026-09-18.

## Цель

Добавить агентский слой после handoff work units: независимые результаты code review,
testing и documentation, явное обновление Project Knowledge, детерминированный
readiness gate и пакет для пользовательской приёмки. Task Manager остаётся владельцем
lifecycle; semantic review и выбор результата остаются у агента.

## Архитектура

`AgentExecution.start_gates()` создаёт отдельный in-memory process run с графом
`code_review → testing → documentation → knowledge_refresh → final_validation`.
Каждый gate принимает только структурированный JSON envelope с outcome и payload.
Положительные и отрицательные результаты публикуются в Artifact Repository как
immutable evidence; для ролей, поддерживаемых Task Manager, добавляется ссылка через
публичный `TaskManagerService.attach_artifact`.

Gate run сохраняет candidate revision, исходную code-corpus revision, definition
version и execution package binding. Перед каждым gate проверяются task version,
собственный claim/run и отсутствие source drift. Результаты `changes_required`,
`failure`, `blocked`, `stale` и `fallback_required` не могут пройти readiness.

## Knowledge policy

Knowledge refresh вызывается отдельным методом и делегируется `KnowledgeRefreshNode`.
Политика явно передаётся как `advisory` или `required`: при advisory проверенный
`degraded` разрешён только как warning, при required разрешены только fresh
`success`/`not_required`. Failed/stale/confirmation/fallback исходы всегда запрещают
readiness. Git и Task Manager не изменяются самим refresh node.

## Final validation и acceptance

`final_validation` не повторяет semantic review и не запускает тесты. Он сверяет
наличие и outcome предыдущих evidence, точное совпадение candidate/source revision,
полное покрытие acceptance criteria и отсутствие blocking findings. При `ready` агент
подаёт acceptance scenarios и automated evidence; они публикуются отдельным
`acceptance_package`. Затем закрывается gate run и через публичный lifecycle Task
Manager выполняется `mark_awaiting_acceptance`. Только явный пользовательский
`accept_task(candidate_revision=...)` завершает задачу.

## Проверки

Предметные tests покрывают порядок gates, immutable evidence, revision/CAS guards,
негативные outcomes, knowledge policy, final traceability и несовпадение candidate
revision. Документация обновляет действующий guide/architecture/status и сохраняет
ограничения in-memory, отсутствие auto-accept и отсутствие выполнения тестов самим
Final Check.
