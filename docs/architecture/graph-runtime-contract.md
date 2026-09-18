# Контракт Graph Runtime v1

> **Совместимость от 2026-09-17:** этот контракт описывает сохранённый callback API. Новый явный Python путь уже реализован отдельно в [AgentGraphRuntime](agent-runtime-contract.md), переиспользует модели ниже и общий validator, не изменяя legacy WorkflowRun serialization. Произвольный route.target и обход Task Manager guards не разрешены; новый процессный API не означает готовность сквозной агентской подготовки.

**Статус:** действующий контракт v1, согласован в TASK-0002; минимальный in-memory runtime реализован в TASK-0003, 2026-09-17.

Контракт описывает один запуск графа для одного агента в одной real-time сессии. Он дополняет [архитектуру Workflow Run](workflow-run.md) и [протокол паузы](workflow-pause-resume.md). Внешняя координация, фоновый Executor Loop и восстановление между сессиями находятся за пределами v1.

## Владельцы данных

| Объект | Владелец | Правило |
| --- | --- | --- |
| Задача, её lifecycle, claim, блокеры, решения и ссылки | Task Manager | Изменяется только через публичный API `orchestrator-task-manager` |
| Текущий запуск, узел, входы, принятые результаты и ожидание | Graph Runtime | В памяти текущей сессии; не записывается в SQLite Task Manager |
| Тело артефакта и его хеш | Artifact Repository v1 | Runtime получает проверенную ссылку/метаданные; он не владеет payload и не делает артефакт состоянием задачи |
| Выполнение операции | Платформенный/LLM-адаптер | Возвращает структурированный результат; не выбирает следующий узел |

## Определения

### Graph

```yaml
graph:
  graph_id: development-v1
  version: 1
  entry_node: request
  nodes:
    - node_id: request
      input_contract: request-input/v1
      output_contract: node-result/v1
      outcomes: [success, needs_input, blocked, failure]
      transitions:
        success: next_node
```

Обязательные поля: `graph_id`, целочисленный `version`, существующий `entry_node` и непустая коллекция уникальных `nodes`. Каждый переход ссылается на существующий узел либо на терминальный исход `succeeded`, `failed` или `cancelled`. Graph неизменен в течение запуска.

### Node

```yaml
node:
  node_id: string
  input_contract: string
  output_contract: string
  outcomes: [success]
  transitions:
    success: next_node
```

Обязательны уникальный `node_id`, ссылки на контракты входа и выхода, непустой список допустимых `outcomes` и явная таблица `transitions`. Узел выполняется не более одного раза одновременно. Узел не изменяет маршрут напрямую и не возвращает произвольный `route.target` как команду runtime.

### Artifact

```yaml
artifact:
  ref: ARTIFACT-0001-v1
  contract: plan/v1
  role: plan
  sha256: hex-string
  value: structured-or-external-reference
```

Обязательны устойчивые `ref`, `contract`, `role`, 64-значный hex `sha256` тела или подтверждённой внешней версии и `value` либо непустой `uri`. Версия хранения Artifact Repository является частью его ключа `ref + role + version`, но не обязательным полем минимальной runtime-ссылки. Artifact Repository v1 проверяет фактический payload по SHA-256 и возвращает immutable metadata; Runtime проверяет только минимальную структурную форму результата и наличие ключей обязательных выходов. Семантическую схему `input_contract`/`output_contract` и соответствие роли выполняет владелец контракта. Произвольные тела не становятся автоматически Task Manager state.

### WorkflowRun

```yaml
workflow_run:
  run_id: RUN-0001
  task_ref: TASK-0001-or-null
  graph_ref: development-v1
  graph_version: 1
  phase: request | preparation | execution
  state: created | running | waiting_input | blocked | succeeded | failed | cancelled
  current_node: node-id-or-null
  inputs: structured-object
  results: map[node-id, node-result]
  wait: wait-state-or-null
```

Обязательны `run_id`, `graph_ref`, `graph_version`, `phase`, `state`, `current_node`, `inputs`, `results` и `wait`; `task_ref` может быть `null` до регистрации задачи. `graph_version` закрепляется при создании запуска. В каждый момент выполняется один узел.

### NodeResult

```yaml
node_result:
  node_id: current-node
  outcome: success | needs_input | blocked | retryable_failure | failure | domain-outcome
  artifacts:
    result:
      ref: ARTIFACT-0001-v1
      contract: result/v1
      role: result
      sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
      value: structured-value
  data: structured-object
  error: error-or-null
```

`node_id` обязан совпадать с текущим узлом, `outcome` — входить в его список `outcomes`, а обязательные артефакты и `data` должны соответствовать output-контракту. Неизвестный исход, чужой `node_id` или неполный output отклоняются до выбора перехода. `retryable_failure` повторяется только по политике узла и до побочного эффекта либо после явного подтверждения безопасности повтора.

### WaitState

```yaml
wait:
  wait_id: WAIT-0001
  kind: user_input | blocker
  question: string-or-null
  reason: string-or-null
  answer: structured-value-or-null
```

При `needs_input` runtime сохраняет `wait`, переводит запуск в `waiting_input` и не выполняет следующий узел. Ответ проверяется относительно `wait_id` и текущего `node_id`, после чего тот же узел получает ответ. При `blocked` сначала устраняется причина; автоматическое снятие блокера запрещено.

## Минимальный API движка

```text
create_run(graph, inputs, task_ref=None, *, run_id=None, phase="request") -> WorkflowRun
inspect_run(run_id) -> WorkflowRun
step(run_id, node_executor) -> NodeResult | WaitState
resume(run_id, answer, node_executor, wait_id=None, node_id=None) -> NodeResult | WaitState
resume_blocked(run_id, node_executor, wait_id=None, node_id=None, answer=None) -> NodeResult | WaitState
cancel(run_id, reason) -> WorkflowRun
```

`step` проверяет состояние запуска, входы текущего узла, результат и маршрут, затем атомарно в памяти обновляет `current_node`, `results` и `state`; при ошибке проверки исходное состояние не меняется. `resume` допустим только для актуального `wait_id`, а `resume_blocked` повторно запускает тот же узел после устранения внешней причины и также проверяет `wait_id`/`node_id`. Повторный ответ по завершённому ожиданию отклоняется. Ошибки возвращаются структурированно: `run_not_found`, `invalid_state`, `node_mismatch`, `unknown_outcome`, `contract_violation`, `stale_wait`, `blocked` или `execution_failure`.

Интеграционный адаптер Task Manager отдельно выполняет `start_preparation`, `link_workflow_run`, `transition_status`, `claim_task` и другие публичные операции с актуальной `expected_version`. Graph Runtime не меняет SQLite и не считает запись ссылки доказательством завершения запуска.

`phase` допускает `request`, `preparation`, `execution`; default `request` сохранён. Минимальный [Preparation Workflow](preparation-workflow.md) реализует интеграцию подготовки до `ready`, вопросы и blockers через публичный API. Интеграция исполнения/claim остаётся следующим этапом.

## Инварианты и исключённый объём

- Graph и его версия неизменны во время запуска.
- Следующий узел не выполняется до принятого результата текущего узла.
- Ожидание пользователя продолжает тот же узел и ту же сессию.
- Отмена прекращает текущую работу и не откатывает уже выполненные побочные эффекты.
- Нет отдельной runtime SQLite, индекса продолжений, lease runtime, второго worker или автоматического восстановления.
- Нельзя обещать exactly-once для внешних побочных эффектов; исполнитель обязан явно проверять безопасность повтора.

## Связанные материалы

- [состояние и хранение](state-and-storage.md);
- [Workflow Run](workflow-run.md);
- [пауза и возобновление](workflow-pause-resume.md);
- [backlog развития v1](../plans/2026-09-16-orchestrator-roadmap-backlog-design.md).
