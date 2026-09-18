# Guide: execution gates и финальная приёмка

**Статус:** исполняемый guide TASK-0017, Python API v1.

После завершения work units и `handoff` получите gate request:

```python
state = execution.inspect(run_id)
gate = execution.start_gates(
    run_id,
    expected_revision=state["run"]["revision"],
    expected_task_version=state["task"]["version"],
    knowledge_required=False,
)
gate_id = gate["run"]["run_id"]
request = execution.gate_request(gate_id)
```

Перед каждым действием заново читайте `gate_inspect()` и передавайте обе текущие
версии. Результаты не выполняются ядром; их подаёт агент:

```python
execution.submit_gate(gate_id, {
    "outcome": "approved",
    "payload": {
        "summary": "Review завершён",
        "implementation_revision": request["source_revision"],
        "candidate_revision": request["candidate_revision"],
        "findings": [],
        "evidence_refs": ["review-output"],
    },
}, expected_revision=execution.gate_inspect(gate_id)["run"]["revision"],
   expected_task_version=execution.gate_inspect(gate_id)["task"]["version"])
```

Для `testing` используются исходы `passed`/`passed_with_warnings` и totals с
нулём failed; для `documentation` — `success` или `no_change`. Все они должны
ссылаться на ту же source и candidate revision. Любой отрицательный исход
сохраняется как evidence, но завершает gate run без readiness. После failed или
blocked run вызовите `release_gates(..., target_status="preparing")`; это требует
явного remediation и не переписывает файлы.

Knowledge обновляется отдельно:

```python
current = execution.gate_inspect(gate_id)
execution.refresh_knowledge(
    gate_id,
    expected_revision=current["run"]["revision"],
    expected_task_version=current["task"]["version"],
)
```

Для full refresh с `authorization="required"` первый результат получает runtime
outcome `needs_input`, состояние `waiting_input` и доменный status
`awaiting_confirmation`. После фактического ответа вызовите `refresh_knowledge`
с текущими revision/task version и `decision={"approved": True, "ref": "..."}`.
Фасад возобновляет точный wait и повторно вызывает узел. Исходный request
сохраняется: при продолжении его можно не передавать; переданный request обязан
совпадать с сохранённым. Менять authorization/mode во время ожидания нельзя.
Отказ/одобрение без decision ref не запускает full refresh; при отказе можно
отменить gate runtime и освободить gates. Каждый результат knowledge stage
публикуется новой immutable version, связанной с process revision, поэтому
запрос подтверждения и итог не перезаписывают друг друга. Неверный request,
неактивный stage или исчерпанный budget отклоняются до refresh. Status
`stale`/`failed`/`fallback_required` не может пройти readiness.

Final payload обязан указать `candidate_revision`, implementation/review/test/docs
revisions, knowledge status/policy, все acceptance criteria со статусом
`satisfied`, пустой `blocking_findings`, evidence refs и непустой
`acceptance_package.scenarios`. После успешного результата задача становится
`awaiting_acceptance`. Пользовательскую приёмку регистрируйте только после показа
пакета:

```python
task = execution.service.get_task(task_id)
execution.service.accept_task(
    task_id, task["version"],
    candidate_revision=task["artifacts"]["readiness"]["metadata"]["candidate_revision"],
    completion_decision_ref="user-acceptance/TASK-xxxx/2026-09-18",
    artifact_ref=task["artifacts"]["acceptance_package"]["ref"],
)
```

`accept_task` — единственный шаг, который завершает задачу; runtime success или
готовность пакета сами по себе не являются пользовательской приёмкой.
