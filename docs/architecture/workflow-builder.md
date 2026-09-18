# Конструктор workflow v1

**Статус:** реализованный и принятый контракт TASK-0036, 2026-09-18. Конструктор проектирует, проверяет и экспортирует определения; отдельное исполнение добавлено в [TASK-0037](workflow-execution.md).

## Ответственность

`orchestrator.workflow_builder` предоставляет `ComponentLibrary`, `WorkflowBuilder`, `ResolvedWorkflow`, `WorkflowBuildError` и CLI. Python 3.12, только стандартная библиотека. Компиляция не выполняет инструкции узлов, команды тестов, LLM, ready/claim или изменение состояния задачи. TASK-0037 добавляет optional snapshot/role integration в AgentPreparation/AgentExecution; Task Manager не изменён.

Skill `orchestrator-workflow-builder` ведёт совместное проектирование с пользователем, выбирает библиотечные блоки, создаёт определения при необходимости и использует детерминированные проверки. Канонический переносимый skill находится в `workflow-library/skills/orchestrator-workflow-builder`; проектная копия подключена в `.agents/skills/orchestrator-workflow-builder`.

## Каталог и контракты

Явно заданный каталог содержит `contracts/*.json` и `components/*.toml`. Несколько каталогов объединяются без повторяющихся ID контрактов или ссылок компонентов. Это не поиск произвольных установленных Python plugins. Компоненты ссылаются друг на друга через фиксированный `id@version`; неизвестные ссылки и `latest` отклоняются.

Контракт JSON имеет поля `id` и `schema`. Поддерживается ограниченное подмножество схем: `type`, `properties`, `required`, boolean `additionalProperties`, `items`, `enum`, `minimum`, `maximum`, `minItems`, `minLength`. Типы: object, array, string, integer, number, boolean, null. Необъявленные свойства по умолчанию запрещены; boolean не считается integer. `$ref`, oneOf, pattern и остальные ключи не поддерживаются и отклоняются. Это не полный JSON Schema validator.

Входной/выходной порт связывается с конкретным ID зарегистрированной схемы. Совместимость соединения и replacement требует точного равенства контрактов портов; более широкая subtype compatibility не выводится. Схема фиксирует структуру, но смысловая корректность свидетельств остаётся ответственностью агента/reviewer.

## TOML

Обязательны `schema_version=1` и `[component]`: `id`, положительная `version`, `kind` (`node`, `subgraph`, `workflow`), `title`, `description`. Составной блок также имеет `entry`. Таблицы `inputs` и `outputs` отображают имена портов в ID контрактов; `outcomes` отображает исход в список обязательных выходных портов. Этот список используется как `Node.required_outputs_by_outcome` при компиляции.

Атомарный узел объявляет `execution.kind`: agent, tool или deterministic. Agent требует instruction или skill; tool/deterministic требует capability и не принимает model_profile. Все три эффекта узла задаются явно boolean: writes_repository, writes_task_manager, external_actions. Эффекты составного блока объединяют эффекты его внутренних узлов; они информируют о политике, а не обеспечивают filesystem enforcement.

`config_schema.<параметр>` содержит `schema` и необязательный `default`. Значения `config` проверяются против схем; отсутствие значения и default является ошибкой. Неизвестные параметры запрещены. Профиль модели может наследоваться от составного блока; instruction, skill и capability не наследуются. Конкретное значение экземпляра имеет приоритет. Для agent без профиля используется standard; он должен присутствовать в model_profiles корневого workflow. У tool/deterministic модель не появляется вследствие наследования.

Корневое компилируемое определение имеет kind=workflow, `model_profiles`, `runtime` и `terminal_states`. Профиль содержит непустые provider/model и необязательный reasoning; это descriptors, без проверки доступности провайдера. `terminal_states` явно отображает каждый outcome корня в succeeded, failed или cancelled. Подграф компилируется при подключении к workflow; его внутренний exit не завершает родителя сам по себе.

## Композиция и артефакты

Каждый `nodes.<имя>` имеет ref, bindings `inputs`, все `transitions` и необязательные config/execution overrides. Имя экземпляра не содержит точек; вложенные runtime IDs формируются как `testing.run`. Имена succeeded/failed/cancelled зарезервированы. Максимальная глубина композиции 20, разворачивание одного дерева ограничено 2000 экземплярами. Рекурсивная композиция компонентов запрещена; routing loops допускаются с конечным общим runtime budget.

Binding имеет вид `input:port` или `instance.port` в текущем графе. Каждый вход получает binding совместимого контракта. Переход имеет вид имени соседнего экземпляра или `exit:outcome`. `exits.<outcome>` явно отображает обязательные внешние выходы в bindings. Все узлы и объявленные exits должны быть достижимы.

Проверка data flow пересекает гарантированные результаты всех путей к узлу и выходу. Порт, который не произведён на одной из ветвей, не может служить обязательным входом. При повторном выполнении источника старое наличие его портов не считается подтверждением нового результата. Для wait outcomes needs_input/blocked переход остаётся на текущем экземпляре; явные WaitState/CAS/resume контролирует AgentGraphRuntime.

Compiler заменяет ссылку на подграф его entry, формирует qualified IDs внутренних узлов и отображает внутренние exits на переходы caller. Дерево композиции и bindings сохраняются вместе с плоским Graph. Builder проверяет передачу декларативно; фактические payload/aliases/результаты подграфов материализует отдельный [WorkflowExecutor](workflow-execution.md), generic runtime этого не делает.

## Проектный overlay

Overlay — отдельный TOML с schema_version=1 и таблицами nodes, model_profiles, runtime. CLI принимает его через `--overlay`; автоматической загрузки `.orchestrator/workflow.toml` и `extends` пока нет. `.orchestrator/project.json` сохраняет роль подключения проекта.

Ключ nodes адресует полный qualified ID экземпляра; для внутренних узлов в TOML используются кавычки: `[nodes."testing.summary"]`.

- `operation="patch"`: inputs/transitions/config/execution объединяются по ключам; скаляры и списки заменяются целиком. ref запрещён.
- `operation="replace"`: ref выбирает новый node/subgraph с точно теми же inputs/outputs/outcomes, включая обязательные порты. Внешние inputs/transitions сохраняются, config/execution прежней реализации не сохраняются. Новые значения берутся из replacement, наследования и явного patch внутри replacement operation.

Override родителя применяется раньше override потомка независимо от порядка таблиц в файле. Неизвестные экземпляры, поля и несовместимые замены отклоняются. Модельные bindings и runtime tables также объединяются по ключам. v1 не интерпретирует Project Profile как слой model defaults; он остаётся типизированным входом процесса.

## Снимок и инспектор

ResolvedWorkflow хранит immutable сериализованный снимок и Graph. `to_dict()` возвращает отделённые JSON-контейнеры; runtime_options также отделены. Снимок включает дерево компонентов, runtime узлы/структурные bindings, effective config/execution, происхождение значений, загруженные контрактные схемы и digests использованных библиотечных manifests.

Digest `workflow/v1:<sha256>` покрывает снимок, включая provenance и загруженные схемы; изменение неиспользуемой загруженной схемы или путей provenance также может его изменить. Это не code-corpus revision; optional [WorkflowSource binding](workflow-execution.md) закрепляет его в Plan/Review/Package/preflight. `validate_outputs(node_id, outcome, outputs)` явно проверяет результат по портам и схемам; generic AgentGraphRuntime проверяет ключи и свой структурный контракт, но не вызывает этот дополнительный validator автоматически. WorkflowExecutor вызывает его перед принятием.

`orchestrator.workflow_viewer.render_workflow` экспортирует самостоятельный HTML с встроенным snapshot. Инспектор работает локально без сервера/CDN: выбор узлов/переходов/exits, раскрытие подграфов, breadcrumbs, поиск во вложенности, масштабирование и перемещение. Инструкции и схемы выводятся как текст; HTML в payload не становится исполняемой разметкой. Viewer показывает сохранённое определение, а не реальные runtime статусы. Для больших графов используется базовая раскладка; оптимизированная трассировка рёбер и browser editing не входят в v1.

## Примеры и дальнейшая интеграция

Библиотека содержит пять атомарных блоков и два подграфа Testing/Documentation. Это учебный вертикальный срез с контрактами `testing-summary/v1` и `documentation-summary/v1`; он не заменяет полные testing-result/documentation-result execution gates и не ослабляет их evidence guards.

TASK-0037 добавляет host adapters, model dispatch с проверкой transport identity, роли/обработчики фасадов, workflow package/preflight binding и передачу артефактов; [контракт](workflow-execution.md), [guide](../guides/workflow-execution.md). Это исходный in-process пакет, не полная устанавливаемая поставка TASK-0021 и не весь backlog сквозных проверок TASK-0022.

[Пользовательский guide](../guides/workflow-builder.md), [история дизайна](../plans/2026-09-18-workflow-config-subgraphs-model-policy-design.md).
