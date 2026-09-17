# TASK-0015 — граф подготовки до ready

**Статус:** TASK-0015 принята пользователем 2026-09-17 и завершена через публичный API (`completed`, version 18); активный run закрыт, claim освобождён.

## Выполнено

Добавлен `orchestrator.preparation_workflow` с `PreparationWorkflow`/`PreparationError`. Существующий Graph Runtime объявляет маршруты Context → Analysis → Planning → Review → Package → Ready, Context expansion и Plan revision. Полные payload и immutable records публикуются через Artifact Repository; Task Manager изменяется только публичным API. Claim/исполнение после ready отсутствуют, обязательная specification.md не возвращена. Для Graph Runtime добавлена backward-compatible опция phase с прежним default request.

Неполная синхронизация явно видна и запрещает следующий шаг; повтор оставшихся действий не запускает planner/reviewer заново. Конфликт внешней версии требует явного reconcile с прочитанной версией; definition/artifact changes не принимаются. Реальный guard проверяет план, approval/package binding и blockers. Проекция защищает пользовательский документ от перезаписи.

## Критерии и проверки

| Критерий | Свидетельство |
| --- | --- |
| AC-01: structured stages/artifacts | Версионируемые request/result contracts и payloads, repository records, compact Execution Package |
| AC-02: waits/blockers/review | needs_input на всех адаптерах, identity/resume, owned blocker, revisions, ограниченные циклы |
| AC-03: реальный ready guard | Modified projection даёт guard_failed; stale binding/definition и внешний blocker не приводят к ready |
| AC-04: tests/guide/public API | 18 integration tests, русский contract/guide; нет прямого SQL или private Task Manager methods |

Предметный набор — 18/18. Покрыты happy path, вопросы на каждом этапе, invalid resume без решения/потери wait, blocker remediation, changes_required/hash revision, cycle exhaustion, context expansion limit, stale binding и AC coverage, modified plan + pending sync, внешний title mutation + explicit reconcile без повторного adapter, definition change, external blocker, сохранность пользовательского plan, malformed Plan constraints/dependencies/validation, IO fault проекции и повтор sync, malformed finding/envelope route, backward-compatible phase.

Финальный полный прогон 2026-09-17: корень — 52 теста (51 passed, 1 expected Windows file-symlink skip); Task Manager — 73/73; Onboarding — 19 (18 passed, 1 expected Windows symlink skip). Compileall успешен, git diff --check не выявил ошибок (только предупреждения LF/CRLF). Проверка живого состояния и ссылок документации фиксируется ниже. Независимый аудит TASK-0014 относится только к repository и не выдаётся за аудит новой реализации TASK-0015; самостоятельная контрактная проверка основным агентом не заменяет отдельный аудит.

Команды: `.venv/Scripts/python.exe -m unittest discover -s tests -q`, аналогичный discover для `packages/task-manager/tests` и `packages/onboarding/tests`; `python -m compileall -q orchestrator tests packages/task-manager/src packages/onboarding/src`; `git diff --check`.

Кандидатная ревизия: `preparation-workflow-v1:F2FEB627FAC9A84B40F9C6DF533550076873DE7AEA3F3CF0D7B0432CB310011B` (SHA-256 `orchestrator/preparation_workflow.py`). Дополнительные хеши: Graph Runtime `ED3DBDB90819415A3CDD2D1577B9078718F42EC73B30D5254C173581025DC121`, integration tests `6582C372298FB9D4AE7B2F9F2F31689372031D0E43B56BDC9D6DBD5FE4744D57`. Это локальный working-tree candidate, не опубликованный Git commit.

## Проверка основным агентом

После реализации проверены связи очереди побочных эффектов и cursor, binding актуального plan/review/package, защита projection и guards публичного API, отсутствие SQL/private calls, изоляция adapter inputs, wait identity и ограниченные revision loops. Найденные при тестировании ошибки преобразования TaskError, типов finding/binding и identity исправлены до финального прогона; регрессии входят в 18 тестов. Итоговая самостоятельная проверка: в пределах AC-01–AC-04 замечаний не осталось, результат готов для приёмки. Это не независимый аудит и не пользовательское одобрение.

Read-only проверка локальных Markdown-ссылок охватила 37 изменённых/новых документов и 178 ссылок: отсутствующих файлов нет. Проверены пути до файлов, не семантика всех anchors. Live `orchestrator-tasks --project . validate`: `ok=true`, result пустой.

<a id="user-acceptance"></a>

## Пользовательская приёмка

2026-09-17 пользователь ответил «Подтверждаю» на отчёт TASK-0015, показанный после реализации и проверок. Приёмка относится к указанной выше кандидатной ревизии `preparation-workflow-v1:F2FEB627FAC9A84B40F9C6DF533550076873DE7AEA3F3CF0D7B0432CB310011B`. Перед завершением повторно сверены SHA-256 workflow, Graph Runtime и integration tests: они совпадают с показанным кандидатом. Отдельный независимый аудит TASK-0015 не проводился и не заявляется как выполненный.

Решение зарегистрировано через атомарный публичный `accept_task`: `awaiting_acceptance` v17 → `completed` v18, acceptance=approved привязана к указанной кандидатной ревизии. Operation ID: `accept-task0015-user-confirmed-20260917`; completion decision ref: `docs/reports/2026-09-17-preparation-workflow.md#user-acceptance`. SQLite напрямую не изменялась, acceptance guards не отключались.

## Ограничения

Нет встроенных смысловых/LLM/PKM адаптеров, автоматического synthesis пользовательских требований, cross-session/multiprocess recovery или общей транзакции runtime/files/Task Manager. Caller отвечает за совпадение project roots, реальное содержательное review и подтверждённую source revision. Подробности: [контракт](../architecture/preparation-workflow.md), [guide](../guides/preparation-workflow.md).
