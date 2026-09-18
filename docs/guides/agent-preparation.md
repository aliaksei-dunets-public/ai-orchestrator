# Подготовка задачи внешним агентом

**Статус:** guide реализованного AgentPreparation TASK-0029, 2026-09-18. Пример Python использует временный проект и демонстрационные payload, не анализ текущего репозитория.

## Протокол агента

1. Прочитайте каноническую карточку через Task Manager. Уточнения требований регистрируйте его публичным API; не создавайте TaskML/specification вместо карточки.
2. Запустите AgentPreparation для фиксированного project root с прочитанной task version и фактически установленной source revision. Проверяйте состояние через request/inspect, не по переписке.
3. В Context осмотрите реальные исходники и дайте evidence refs; в Analysis сформулируйте constraints/invariants/unknowns. Отдельный [Knowledge Service/Graphify](project-knowledge.md) доступен через caller: проверяйте snapshot/freshness и citations, при отказе используйте direct discovery. Facade не делает query/refresh автоматически.
4. Составьте структурированный Plan с work units и проверками. Проверьте план отдельно по карточке и evidence; approved должен быть связан с опубликованным plan SHA-256 и текущей definition_version. Self-review не называйте независимым аудитом.
5. Явно подтвердите Package и Ready gates. Убедитесь, что sync_pending=false, task.status=ready, active run и claim отсутствуют. Исполнение после ready требует отдельного preflight и Task Manager claim; данный интерфейс его не делает.

Система программно проверяет структуры и bindings, но не заменяет смысловую работу агента. Наличие evidence_ref не доказывает факт; не используйте фиктивные review или пользовательскую приёмку ради guards.

## Исполняемый пример

Запускайте из корня репозитория с установленным Task Manager (`.venv\Scripts\python.exe`). Ядро пока не поставляется самостоятельным wheel.

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from orchestrator import AgentPreparation

with TemporaryDirectory() as folder:
    flow = AgentPreparation(Path(folder))
    task = flow.service.create_task(
        title="Демонстрация подготовки", task_type="implementation",
        objective="Проверить демонстрационный сценарий",
        original_request="Демонстрационный сценарий",
        acceptance_criteria=["Демонстрационные проверки проходят"],
        constraints=["Не менять публичный API"],
    )
    run = flow.start(task["id"], expected_task_version=task["version"],
                     prepared_source_revision="demo-fixture-v1")

    # Помощник только передаёт прочитанные версии, не выбирает semantic работу.
    def submit(envelope):
        snapshot = flow.inspect(run.run_id)
        return flow.submit(run.run_id, envelope,
            expected_revision=snapshot["run"]["revision"],
            expected_task_version=snapshot["task"]["version"])

    submit({"outcome": "success", "payload": {
        "summary": "Демонстрационный проект", "evidence_refs": []}})
    submit({"outcome": "success", "payload": {
        "objective_interpretation": "Проверить сценарий", "constraints": [],
        "invariants": [], "unknowns": []}})
    submit({"outcome": "success", "payload": {
        "goal": "Проверить сценарий", "scope": {"in": ["Демонстрация"], "out": ["Другие изменения"]},
        "global_constraints": ["Не менять публичный API"], "global_validation": ["Проверить результат"],
        "work_units": [{"id": "WU-1", "goal": "Демонстрация", "files_objects": ["demo.py"],
            "expected_result": ["Сценарий проходит"], "validation": ["Запустить проверку"], "depends_on": []}]}})
    snapshot = flow.inspect(run.run_id)
    submit({"outcome": "approved", "payload": {
        "findings": [], "criterion_ids": ["AC-01"], "zero_context_executable": True,
        "approved_binding": {"plan_sha256": snapshot["artifacts"]["plan"]["sha256"],
                             "definition_version": snapshot["task"]["definition_version"]}}})
    submit({"outcome": "success"})  # Package: payload формирует deterministic primitive.
    submit({"outcome": "success"})  # Ready: реальные guards, без claim.
    final = flow.inspect(run.run_id)
    assert final["task"]["status"] == "ready" and not final["sync_pending"]
    assert final["task"]["active_claim"] is None and final["task"]["active_run_ref"] is None
    assert flow.service.health_check() == []
    print(final["task"]["id"], final["task"]["status"])
```

## Ожидания и ошибки

Для вопроса подайте `{"outcome":"needs_input","question":"…"}`. Получив реальный ответ пользователя, вызовите resume_wait с wait_id/node_id и свежими process/task версиями; передайте answer явно, включая None, если это фактический ответ. Для blocker подайте reason; resume принимает resolution без answer. Затем заново осмысленно выполните текущий узел и submit: resume его не запускает.

При sync error принятый result уже может продвинуть процесс. Не повторяйте submit: сначала inspect. Для обычной исправимой publication/projection ошибки устраните причину и synchronize. Пользовательский plan.md не удаляйте и не заменяйте автоматически.

При task_version_conflict перечитайте карточку/историю и вызовите reconcile только если исходное намерение всё ещё применимо. Definition drift требует новой подготовки; cancel текущего процесса допустим для cleanup без отмены самой задачи.

При effect_outcome_unknown никакой слепой retry. Сопоставьте неизвестный method/kwargs/before в inspect с task history и файлом. Вызовите reconcile_effect с фактически прочитанной task version и applied=true/false, затем synchronize. Код подтверждает только точный unchanged snapshot либо единственный соответствующий successor event; при дополнительных внешних событиях остановитесь для ручного аудита. Наличие намерения в unknown_effect не является evidence выполнения.

Run.state=succeeded при sync_pending=true — не готовность. После потери памяти нельзя продолжить тот же процесс по одной task link: checkpoints пока нет. [Полный контракт и ограничения](../architecture/agent-preparation.md).
