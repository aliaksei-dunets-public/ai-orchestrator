# Request Router → Task Creator

**Статус:** реализованный первый срез входного потока; Graph Runtime и автоматическое выполнение ещё не реализованы.

Входной поток находится в исходном пакете `orchestrator/` и не привязан к конкретному LLM-провайдеру:

```text
RequestRouter (классификация адаптера)
        ↓ managed_work
TaskCreator (проверка Task Artifact)
        ↓
TaskManagerService.create_task()
```

Для `direct_response` поток завершается на Router и задачу не создаёт. Для `managed_work` Router обязан вернуть тип задачи из существующего набора: `implementation`, `analysis`, `investigation`, `incident` или `exploration`.

## Подключение адаптеров

Адаптер классификации Router и адаптер смысловой подготовки Task Creator передаются через конструктор. Ядро проверяет только контракт и не принимает решений за адаптер:

```python
from pathlib import Path

from orchestrator import RequestFlow, RequestRouter, TaskCreator
from orchestrator_task_manager import TaskManagerService

service = TaskManagerService(Path("."))

router = RequestRouter(lambda request, context: {
    "route": "managed_work",
    "suggested_type": "implementation",
    "confidence": "high",
})

creator = TaskCreator(service, lambda request, task_type, context: {
    "title": "Исправить расчёт",
    "objective": "Исправить сценарий X",
    "acceptance_criteria": ["X возвращает ожидаемое значение"],
    "constraints": [],
})

result = RequestFlow(router, creator).handle("Исправь расчёт X")
```

Результат имеет форму `result.route` и, для управляемой работы, `result.creation`. Возможные результаты Creator: `success` (возвращена созданная задача), `needs_input` (вопросы пользователю, запись не выполняется) и `failure` (ошибка контракта или Task Manager).

Task Creator не создаёт Specification, Plan или Execution Package и не запускает Graph Runtime. Для состояния задачи используется только публичный API `orchestrator-task-manager`; прямой доступ к SQLite запрещён.
