# TASK-0020 — Incremental Refresh Graphify v1

**Статус:** реализация завершена; TASK-0020 передана в `awaiting_acceptance`, пользовательская приёмка ещё не зарегистрирована. Код, схема и SQLite Task Manager не изменялись; evidence обновлена через публичный API.

## Что реализовано

`ProjectKnowledgeService.refresh_incremental()` вычисляет разницу между текущим и indexed `SourceSnapshot`, классифицирует `added`, `changed`, `deleted` и одинаковые по хешу `renamed` sources. Для code-only corpus он подготавливает isolated staging с текущими файлами, прежним Graphify `graph.json` и сохранённым manifest, затем вызывает установленный Graphify 0.9.63:

```text
graphify update <staging-corpus> --no-cluster
```

Нативный Graphify выполняет AST extraction затронутых файлов, dependency update и pruning удалённых файлов. Неповреждённые nodes/evidence переносятся из базового графа. Full `refresh()` остаётся отдельной операцией. `precommit_refresh()` — gate для агента: возвращает результат, но не запускает Git commit.

`AgentExecution.precommit_gate()` теперь является явным orchestration boundary: после всех work units он вызывает этот service, проверяет `GraphStatus`, классифицирует результат как `success`, `degraded`, `stale` или `failed` и возвращает `commit_allowed`. При stale/failed commit запрещён; при validated full fallback возвращается degraded и commit разрешён. Git и Task Manager остаются вне метода.

## Гарантии

- No-op возвращает `status=not_required`, новую immutable version не создаёт.
- Успех возвращает `mode=incremental`, change-set и новый immutable graph/index с atomic current pointer.
- Source drift, invalid output, provider failure и publication failure не меняют старый current pointer.
- Старые индексы без manifest получают `mode=full-rebuild-fallback` с причиной `manifest_missing`; это явно диагностируемый fallback, не incremental claim.
- Изменения только в исключённых каталогах (`docs/plans`, `docs/reports`, `.orchestrator`, `obsolete`, scratch) не попадают в snapshot и не запускают incremental update.
- Upstream `links` от native update нормализуется в сервисный `edges`, исходное поле сохраняется для Graphify MCP/query.

## Проверки

- Root: `157 tests`, `155 passed`, `2 Windows skip` (Graphify/onboarding optional environments).
- Knowledge suite: 27 tests, включая реальный pinned Graphify fixture: no-op, changed/add, rename/delete, unchanged node retention, source drift, provider failure, legacy fallback и pre-commit gate.
- Onboarding: 19 tests, `18 passed`, `1 Windows skip`.
- Task Manager: 73 tests passed.
- `python -m compileall -q orchestrator` и `git diff --check` прошли.

AgentExecution suite: 35 тестов, включая orchestration gate success/stale.

## Не входит в этот срез

Semantic document refresh через host-agent Graphify skill, отдельный headless backend, automatic Git hooks и обновление Task Manager остаются отдельными задачами/этапами. Incremental Refresh здесь означает только разрешённый code corpus и не является документной переиндексацией. Gate подключён к `AgentExecution` явно, но вызывающий агент всё ещё обязан вызвать его и выполнить Git commit только при `commit_allowed=true`.
