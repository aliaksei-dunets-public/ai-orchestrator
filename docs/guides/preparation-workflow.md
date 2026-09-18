# Подготовка задачи до ready

> **Граница использования от 2026-09-17:** примеры ниже работают с прежним реализованным callback API. Они не запускают новый Orchestrator Agent. Целевое распределение ответственности — [агент-центричная архитектура](../architecture/agent-centric-orchestration.md); новый [AgentPreparation](agent-preparation.md) реализован в TASK-0029 и является рекомендуемым путём для новых агентских запусков. Task Manager сохраняется без изменений.

**Статус:** guide реализованного минимального Preparation Workflow v1; TASK-0015 принята пользователем и завершена (version 18).

## Подключение

Нужен установленный Task Manager и корневой исходный пакет `orchestrator`. Четыре адаптера — функции, принимающие объект request и возвращающие envelope по [контракту](../architecture/preparation-workflow.md). Они отвечают за обнаружение контекста, анализ, план и реальный review; workflow не заменяет их фиктивными результатами.

```python
from pathlib import Path
from orchestrator import ArtifactRepository, PreparationWorkflow
from orchestrator_task_manager import TaskManagerService

root = Path(".").resolve()
service = TaskManagerService(root)
repository = ArtifactRepository(root)
flow = PreparationWorkflow(service, repository, {
    "context": discover_context,
    "analysis": analyze_task,
    "planning": build_plan,
    "plan_review": review_plan,
})
run = flow.start(
    "TASK-0001",  # фактическая created/preparing карточка без active run/claim
    prepared_source_revision="<подтверждённая ревизия исходников>",
    project_profile={"context": {"knowledge_map": {"enabled": False}}},
)
```

Функции `discover_context` и остальные нужно определить/подключить самим; пример не содержит встроенного LLM и не обещает работающую PKM. `False` означает, что Context adapter должен работать через Direct Discovery без PKM. Значение profile передаётся адаптеру; выбор стратегии остаётся его ответственностью.

## Один шаг и остановка

`flow.step(run.run_id)` выполняет ровно один узел и синхронизирует принятую публикацию. Перед следующим шагом проверьте `flow.inspect(run.run_id)`:

- `sync_pending` означает незавершённые побочные эффекты — двигаться дальше нельзя;
- `run.state=waiting_input` — покажите вопрос из `run.wait.question`;
- `run.state=blocked` — выясните причину из WaitState/карточки;
- `task.status=ready` и `sync_pending=false` — устойчивый handoff построен; здесь остановитесь.

`run.state=succeeded` сам по себе не доказывает Task Manager ready: финальная синхронизация ещё может быть pending. Никакого автоматического claim нет, в том числе при handoff-mode immediate.

## Ответ и blocker

```python
snapshot = flow.inspect(run.run_id)
wait = snapshot["run"]["wait"]
flow.resume(
    run.run_id, {"confirmed": True},
    wait_id=wait["wait_id"], node_id=wait["node_id"],
)
```

Не используйте `None` вместо identity и не подставляйте ответ от другого вопроса. Invalid result сохраняет runtime wait и не регистрирует решение в Task Manager. Для blocker после реальной remediation:

```python
flow.resume_blocked(
    run.run_id, resolution="Доступ восстановлен",
    wait_id=wait["wait_id"], node_id=wait["node_id"],
    answer={"access_restored": True},
)
```

Workflow разрешает только зарегистрированный им blocker. Чужие blockers не снимаются автоматически. Повтор после исчерпания review/context лимита допустим только после явного root-cause решения, а не слепого продолжения цикла.

## Ошибки и продолжение синхронизации

После `repository_failure`/`projection_conflict` устраните конкретную причину и вызовите `flow.synchronize(run.run_id)`. Planner/reviewer не будет повторён. Посторонний `plan.md` нельзя удалять или присваивать автоматически: согласуйте сохранение/перенос документа с пользователем.

После `task_version_conflict` перечитайте карточку и историю через публичный API. Если изменение совместимо (например, только title), явно примите прочитанную версию:

```python
current = service.get_task("TASK-0001")
flow.reconcile(run.run_id, expected_version=current["version"])
flow.synchronize(run.run_id)
```

Смена definition или подготовительных артефактов запрещает это продолжение. Требования уточняются caller-ом после реального подтверждения через публичный API; workflow не меняет acceptance criteria по выводу модели. Для нового определения нужна новая подготовка и новое одобрение. Не исправляйте SQLite напрямую, не обходите guard новыми фиктивными хешами. При неопределённом исходе commit или потере процесса сначала вручную сверяйте карточку/историю/файлы: автоматического recovery нет.

## Проверки

`python -m unittest tests.test_preparation_workflow -q` — integration tests в TemporaryDirectory с реальным Task Manager, repository и Graph Runtime. Сценарии и полный результат находятся в [отчёте](../reports/2026-09-17-preparation-workflow.md).
