# Обзорный граф Orchestrator

**Статус:** схема фактически реализованного агентского пути, 2026-09-18.

Схема объединяет три связанных графа: подготовку задачи до `ready`, исполнение work units и post-work-unit execution gates. Смысловые решения принимает внешний агент; runtime проверяет результаты, revision, waits, budgets и переходы. `Task Manager` хранит состояние задачи, а `AgentGraphRuntime` — состояние текущего in-memory запуска.

```mermaid
flowchart TD
    request[Запрос пользователя]
    task[(Task Manager<br/>карточка и definition)]

    request --> task
    task --> startPrep[AgentPreparation.start]

    subgraph PREP[Подготовка задачи — AgentPreparation]
        context[context]
        analysis[analysis]
        planning[planning]
        review[plan_review]
        package[package]
        ready[ready]
        prepFailed((failed))
        prepSucceeded((succeeded))

        context -->|success| analysis
        analysis -->|success| planning
        analysis -->|needs_context| context
        planning -->|success| review
        review -->|approved| package
        review -->|changes_required| planning
        package -->|success| ready
        ready -->|success| prepSucceeded

        context -.->|needs_input / blocked| context
        analysis -.->|needs_input / blocked| analysis
        planning -.->|needs_input / blocked| planning
        review -.->|needs_input / blocked| review
        package -.->|needs_input / blocked| package
        ready -.->|needs_input / blocked| ready

        context -->|failure| prepFailed
        analysis -->|failure| prepFailed
        planning -->|failure| prepFailed
        review -->|failure| prepFailed
        package -->|failure| prepFailed
        ready -->|failure| prepFailed
    end

    startPrep --> context
    prepSucceeded -->|mark_ready| taskReady[(Task Manager: ready)]
    prepFailed -.->|release / cancel| cancelled((cancelled))

    taskReady -->|AgentExecution.start + claim| work

    subgraph EXEC[Исполнение work units — AgentExecution]
        work[work_unit]
        workDone((succeeded<br/>handoff))
        workFailed((failed))
        work -->|success| work
        work -->|handoff| workDone
        work -.->|needs_input / blocked| work
        work -->|failure| workFailed
    end

    workDone -->|start_gates| gateReview
    workFailed -.->|release_gates / cancel| cancelled

    subgraph GATES[Post-work-unit execution gates]
        gateReview[code_review]
        gateTests[testing]
        gateDocs[documentation]
        knowledge[knowledge_refresh]
        final[final_validation]
        gatesFailed((failed))
        gatesReady((succeeded / ready))

        gateReview -->|approved| gateTests
        gateReview -->|other outcome| gatesFailed
        gateTests -->|passed / passed_with_warnings| gateDocs
        gateTests -->|failed / blocked / inconclusive| gatesFailed
        gateDocs -->|success / no_change| knowledge
        gateDocs -->|other outcome| gatesFailed
        knowledge -->|not_required / success / degraded| final
        knowledge -->|stale / failed / fallback_required| gatesFailed
        knowledge -.->|needs_input: confirmation| knowledge
        final -->|ready| gatesReady
        final -->|not_ready / blocked| gatesFailed
    end

    gatesFailed -.->|release_gates / cancel| cancelled
    gatesReady -->|mark_awaiting_acceptance| acceptance[(Task Manager: awaiting_acceptance)]
    acceptance -->|user accepts candidate| completed((completed))

    context -.->|cancel| cancelled
    work -.->|cancel| cancelled
    knowledge -.->|cancel| cancelled

    classDef state fill:#e8f0fe,stroke:#4f6fad,color:#17233c;
    classDef terminal fill:#edf7ed,stroke:#4f8a4f,color:#173517;
    classDef error fill:#fbecec,stroke:#b85c5c,color:#4a1f1f;
    class task,taskReady,acceptance state;
    class prepSucceeded,workDone,gatesReady,completed terminal;
    class prepFailed,workFailed,gatesFailed,cancelled error;
```

## Как читать схему

- Пунктирные стрелки показывают паузу или отмену. `needs_input` и `blocked` сохраняют текущий узел; после `resume_wait` агент повторно подаёт обычный результат того же узла.
- `required_outputs_by_outcome` влияет на проверку результата внутри любого узла, но не меняет маршрутизацию.
- Подтверждение полной переиндексации в `knowledge_refresh` имеет runtime-outcome `needs_input`; доменный статус внутри результата остаётся `awaiting_confirmation`.
- `succeeded` процесса ещё не означает завершение задачи. После gates создаётся acceptance candidate, а `completed` появляется только после явной пользовательской приёмки.
- `cancelled` доступен из любого нетерминального запуска через актуальные revision/task guards; файлы агента автоматически не откатываются.

Источники переходов: `orchestrator/preparation_primitives.py`, `orchestrator/agent_execution.py`, `orchestrator/execution_gates.py`, `orchestrator/knowledge_refresh_node.py` и действующие контракты в `docs/architecture/`.
