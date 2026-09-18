# Как исполнять work units агентом

**Статус:** исполняемый guide Python-среза TASK-0016. [Контракт](../architecture/agent-execution.md), [результаты](../reports/2026-09-18-agent-execution-v1.md). Это не установленный host skill и не полный production execution loop.

В self-hosted проекте используйте установленную `.venv` и публичный Task Manager API. Получите source revision **перед** AgentPreparation, выполните context/analysis/planning/review/package/ready. После ready preflight должен пройти до claim. Не подставляйте Git HEAD или историческую строку вместо fingerprint. При drift требуется новая подготовка, не ручное редактирование SQLite или approved package.

Следующий пример создаёт только временный отдельный проект и демонстрирует один проверочный no-op unit. Он не меняет задачи настоящего проекта и не завершает их автоматически.

```python
import tempfile
from pathlib import Path
from orchestrator import AgentPreparation, AgentExecution

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / "orchestrator").mkdir()
    (root / "orchestrator" / "example.py").write_text("VALUE = 1\n", encoding="utf-8")
    execution = AgentExecution(root)
    prep = AgentPreparation(root)
    task = prep.service.create_task(title="Проверка", task_type="implementation",
        objective="Проверить пример", original_request="Проверить пример",
        acceptance_criteria=["Python компилируется"])
    run = prep.start(task["id"], expected_task_version=task["version"],
        prepared_source_revision=execution.source_revision())
    payloads = {
        "context": {"summary": "Пример прочитан", "evidence_refs": ["orchestrator/example.py:1"]},
        "analysis": {"objective_interpretation": "Проверить", "constraints": [], "invariants": [], "unknowns": []},
        "planning": {"goal": "Проверить", "scope": {"in": ["Пример"], "out": ["Другие файлы"]},
            "global_constraints": [], "global_validation": ["compile"], "work_units": [{
                "id": "WU-1", "goal": "Проверить Python", "files_objects": ["orchestrator/example.py"],
                "expected_result": ["Компилируется"], "validation": ["compile"], "depends_on": []}]},
    }
    for _ in range(6):
        state = prep.inspect(run.run_id)
        stage = state["run"]["current_node"]
        if stage == "plan_review":
            envelope = {"outcome": "approved", "payload": {"findings": [], "criterion_ids": ["AC-01"],
                "zero_context_executable": True, "approved_binding": {
                    "plan_sha256": state["artifacts"]["plan"]["sha256"], "definition_version": 1}}}
        elif stage in {"package", "ready"}:
            envelope = {"outcome": "success"}
        else:
            envelope = {"outcome": "success", "payload": payloads[stage]}
        prep.submit(run.run_id, envelope, expected_revision=state["run"]["revision"],
                    expected_task_version=state["task"]["version"])
    task = prep.service.get_task(task["id"])
    run = execution.start(task["id"], expected_task_version=task["version"], worker_ref="example-agent")
    request = execution.request(run.run_id)
    assert [unit["id"] for unit in request["available_units"]] == ["WU-1"]
    compile((root / "orchestrator/example.py").read_text(encoding="utf-8"), "example.py", "exec")
    state = execution.inspect(run.run_id)
    execution.submit(run.run_id, {"outcome": "success", "payload": {
        "unit_id": "WU-1", "summary": "compile выполнен", "source_before": request["source_before"],
        "source_after": execution.source_revision(), "changed_files": [], "evidence_refs": ["compile:ok"],
        "validation": {"status": "passed", "checks_run": ["compile"], "failed": []}, "unresolved": []}},
        expected_revision=state["run"]["revision"], expected_task_version=state["task"]["version"])
    state = execution.inspect(run.run_id)
    execution.submit(run.run_id, {"outcome": "handoff"}, expected_revision=state["run"]["revision"],
                     expected_task_version=state["task"]["version"])
    state = execution.inspect(run.run_id)
    assert state["task"]["status"] == "active" and state["task"]["active_run_ref"] is None
    assert state["task"]["active_claim"] is not None
    # В примере следующий gate отсутствует: явно освобождаем lease, не объявляем completed.
    execution.service.release_claim(task["id"], state["task"]["version"], claim_ref=state["claim_ref"],
                                    target_status="ready", reason="Пример завершён, gates ещё не выполнены")
    assert execution.service.health_check() == []
    print("agent execution guide: ok")
```

Для code-only изменений перед `handoff` подключите тот же `ProjectKnowledgeService` через `AgentExecution(..., knowledge_service=knowledge)` и вызовите `precommit_gate` после последнего успешного work unit. `status=success` означает native incremental refresh и fresh graph; `status=degraded` допустим только для проверенного диагностического full-rebuild fallback. При `stale` или `failed` `commit_allowed=false`, поэтому физический commit выполнять нельзя. Facade не вызывает Git и не меняет Task Manager.

Для реальных изменений сохраните request.source_before, выполните unit и проверки, вычислите source_after; changed_files должны отражать всю выбранную code delta. Не вызывайте новый request между partial edits и submit: checkpoint guard обнаружит незарегистрированное изменение. Docs/config не входят в code delta; проверяйте их отдельно и сохраняйте evidence.

При pause подайте needs_input/question либо blocked/reason, затем используйте точные wait_id/node_id и актуальные обе версии в resume_wait. Resume получает новый claim; возвращённый answer/resolution остаётся доступным следующему unit. При истёкшем lease work/renew запрещены, но cleanup собственных ресурсов разрешён.

При sync error прочитайте inspect и public history. Known pending: synchronize либо explicit cancel с причиной. Unknown: только reconcile_effect с доказанной актуальной task version и boolean applied, потом synchronize. Не повторяйте work unit или claim вслепую. Дополнительные события требуют ручной оценки; автоматический restart recovery не обещается.

После handoff агент должен отдельно пройти review/tests/docs/knowledge/final-validation и подготовить acceptance package по [guide execution gates](execution-gates.md). До этого нельзя объявлять задачу принятой за пользователя.
