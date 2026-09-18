# Исполняемые workflow: модели, артефакты и роли

**Статус:** рабочий guide TASK-0037, 2026-09-18; Python in-process API.

## Локальный воспроизводимый пример

Из корня ядра, установленная проектная `.venv`:

```powershell
.venv\Scripts\python.exe workflow-library/examples/run-local-workflow.py --project work/workflow-execution-demo
```

Будут созданы `workflow-result.json`, `unittest-result.txt`, `docs/demo.md` и immutable repository в каталоге примера. Пять узлов: scope → настоящий unittest → summary → documentation impact → documentation update. Model transport — отдельный JSON subprocess с **local-fixture/fixture-v1**, не LLM. Выход должен быть succeeded, evidence_count=5, testing_result.status=passed, documentation_result.status=success. `workflow-result.json` содержит receipts и ссылки на все immutable evidence.

Негативный маршрут в отдельном каталоге:

```powershell
.venv\Scripts\python.exe workflow-library/examples/run-local-workflow.py --project work/workflow-execution-failed-demo --fail-test
```

Ожидается exit code 1, state=failed, evidence_count=3; Documentation не запускается, `docs/demo.md` не создаётся. Это штатный failed workflow, не ошибка transport.

## Подключение модели и capability

Для своего host wrapper используйте `ExecutorRegistry`, `ModelAdapter` или `process_model_adapter`. Wrapper получает selected_executor и обязан выполнить именно выбранные provider/model и вернуть подтверждённые identity. Probe должен проверить фактическую доступность. Настройте реальные model profiles через TOML/overlay до подготовки; библиотечные `current-host-model`/`project-expert-model` — заполнители, которые не становятся доступными автоматически.

```python
from pathlib import Path
from orchestrator.workflow_binding import WorkflowSource
from orchestrator.workflow_execution import ExecutorRegistry, WorkflowExecutor
from orchestrator.model_process_adapter import process_model_adapter

# Все paths/argv задаёт доверенный host. model-host-wrapper — ваш установленный adapter.
source = WorkflowSource(Path("workflow-library/workflows/testing-and-documentation.toml"),
                        (Path("workflow-library"),), Path("workflow-library/examples/project-overlay.toml"))
resolved = source.load()
executors = ExecutorRegistry()
executors.register_model(process_model_adapter(executor_ref="configured-model-host", provider="host",
    argv=["model-host-wrapper"], timeout=60))
# test_runner — ваш callable, реально выполняющий проверки и возвращающий execution_record.
# executors.register_capability("project-test-runner", test_runner, executor_ref="project-tests")
# executor = WorkflowExecutor(target_root, resolved, executors, fallbacks={"expert": ["standard"]})
```

Это шаблон подключения, не обещание наличия команды model-host-wrapper. Реальный runnable subprocess — local-model-host.py из примера выше. Без доступного adapter/capability step отклонится до эффекта. Fallback включайте только при явном разрешении host policy; timeout не повторяет вызов.

Вызов `executor.start(inputs)` возвращает run/revision; `executor.request()` показывает effective config, inputs, schemas и выбранный узел. Выполняйте один `step(expected_revision=state["run"]["revision"])`, затем перечитывайте inspect. Если pending_effect не пуст, сверяйте host logs и подавайте `recover_result(verified_response, expected_revision=..., resolution_ref="...")`; второй вызов модели запрещён. После перезапуска pending/history в памяти не восстанавливаются.

## Привязка к подготовке и исполнению задачи

```python
from orchestrator import AgentPreparation, AgentExecution, ExecutionPreflight

preparation = AgentPreparation(target_root, workflow_source=source)
# prepared_source_revision берётся через ExecutionPreflight(target_root).source_revision().
# start/submit используют свежие task/process versions, как в guide подготовки.
# request(run_id)["workflow_binding"] содержит закреплённый digest.
# При approved Review добавьте workflow_digest в approved_binding.
execution = AgentExecution(target_root, workflow_source=source)
```

Structured Plan получает binding автоматически; Review и Package обязаны подтверждать его. После изменения workflow/overlay/library нужна новая подготовка перед claim. Отсутствующий WorkflowSource для такого package — ошибка workflow_required. После claim редактирование файла не меняет активный snapshot, но immutable corruption или code drift запрещают продолжение.

## Зарегистрированные роли

Следующий шаблон регистрирует Testing: ожидаемые контрактные ссылки — фиксированный role contract, который replacement обязан сохранить.

```python
from orchestrator.workflow_roles import ComponentRole, WorkflowRoleRegistry, testing_gate_handler

roles = WorkflowRoleRegistry()
roles.register(ComponentRole("testing", "execution", "testing",
    inputs={"task": "task-request/v1", "project_profile": "project-profile/v1"},
    outputs={"result": "testing-summary/v1"},
    outcomes={"passed": ["result"], "failed": ["result"]},
    handler=testing_gate_handler(execution.repository)))
# state = execution.gate_inspect(gate_id)
# component = execution.start_component(gate_id, roles=roles, executors=executors, inputs=testing_inputs,
#     expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
# Выполните component.executor через explicit steps.
# execution.submit_component(gate_id, component, expected_revision=state["run"]["revision"],
#                            expected_task_version=state["task"]["version"])
```

Для Documentation аналогично задайте inputs task/project_profile/testing_result, output result=documentation-summary/v1, outcomes success/no_change/failure с result и `documentation_gate_handler(repository, source_adjacent_changed=False)` для заведомо несмежных docs. Не скрывайте влияние на исходники этим флагом. Testing result для отдельной Documentation role предоставляет caller; внутри составного workflow bindings материализуются автоматически.

Preparation принимает те же start_component/submit_component с preparation role и своим handler-ом, возвращающим обычный context/analysis/planning/plan_review envelope. Package/ready и Knowledge gate заменять нельзя. Не включайте Task Manager mutations в component executor. Final validation с AC/evidence, knowledge policy, readiness и отдельная пользовательская приёмка остаются прежними.

Проверки интеграции:

```powershell
.venv\Scripts\python.exe -m unittest tests.test_workflow_execution tests.test_workflow_integration -v
```

[Контракт](../architecture/workflow-execution.md), [builder guide](workflow-builder.md), [preparation guide](agent-preparation.md), [execution guide](agent-execution.md).
