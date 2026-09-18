# Дизайн KnowledgeRefreshNode

**Статус:** согласованный дизайн; подтверждён пользователем 2026-09-18. Реализация не входит в этот документ и оформляется отдельной задачей.

## Решение

Обновление единого Project Knowledge Graph выполняется отдельной нодой Workflow Graph, а не скрытым вызовом внутри work unit или Git-адаптера. В обычном development flow нода является последним обязательным шагом после завершения всех work units, тестов и финальной проверки, непосредственно перед разрешением commit.

Нода может быть размещена и в других графах процессов. Оркестратор выбирает момент запуска и policy, а `ProjectKnowledgeService` выполняет Graphify refresh, проверку snapshot, публикацию immutable версии и возвращает structured result. Task Manager, SQLite и физический Git commit нода не изменяет.

## Режимы обновления

| Режим | Поведение |
| --- | --- |
| `auto` | Для pre-commit выбирает native incremental update; no-op возвращает `not_required`. Full refresh автоматически не запускается. |
| `incremental` | Разрешает только обновление по changed/added/renamed/deleted code sources. Невозможность продолжить возвращается как `failed` или `fallback_required`. |
| `full` | Полная переиндексация запускается только после отдельного explicit decision, если authorization policy не разрешает automatic execution. |

`auto` и `incremental` никогда не эскалируют ошибку в full refresh молча. Full нужен для initial build, восстановления повреждённого/несовместимого baseline, изменения provider/corpus policy или явной maintenance/recovery операции.

## Авторизация

Без настройки действует безопасный default:

```yaml
authorization: required
```

При `required` full-нода создаёт `WaitState` и ждёт подтверждения пользователя через Graph Runtime. При `automatic` full refresh разрешён только для конкретной доверенной `knowledge_refresh`-ноды, явно объявленной в конфигурации graph. Runtime-agent не может поменять `required` на `automatic` во время выполнения. Решение и его provenance сохраняются в Graph Runtime history.

Общий graph default может оставаться `required`; конкретная нода может явно переопределить его на `automatic`. Для обычного pre-commit рекомендуется `mode=auto`, `authorization=required`. Для доверенной maintenance-ноды допустим `mode=full`, `authorization=automatic`.

## Контракт ноды

```yaml
type: knowledge_refresh
mode: auto | incremental | full
authorization: required | automatic
purpose: pre_commit | maintenance | recovery
expected_source_revision: code-corpus/v1:<sha256>
expected_graph_version: v<immutable-version>
explicit_decision_ref: <required for full/required>
```

Результат использует контракт `knowledge-refresh-node/v1` и содержит `status`, `effective_mode`, `commit_allowed`, `source_revision`, `graph_version`, change-set, fallback/error details и provenance решения. Возможные статусы: `not_required`, `success`, `degraded`, `stale`, `failed`, `fallback_required`, `awaiting_confirmation`.

`commit_allowed=true` возможен только для fresh graph: обычный incremental `success`, `not_required` или подтверждённый full `success/degraded`. `stale`, `failed`, `fallback_required` и `awaiting_confirmation` запрещают переход к commit.

## Границы и миграция

Текущий `ProjectKnowledgeService.refresh_incremental()` и `AgentExecution.precommit_gate()` остаются совместимыми API TASK-0020. Новая задача должна вынести orchestration policy и wait/resume в отдельную reusable node, сохранив provider/storage ownership сервиса. Semantic document refresh через host-agent Graphify skill, новые backends, Git hooks и изменения Task Manager не входят в этот срез.

