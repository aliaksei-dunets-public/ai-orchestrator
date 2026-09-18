# Агент-центричная оркестрация

**Статус:** принятое направление; [дизайн миграции](../plans/2026-09-17-agent-centric-graphify-migration-design.md) подтверждён пользователем 2026-09-17. Первый явный Python API процесса реализован в [AgentGraphRuntime](agent-runtime-contract.md); [Knowledge Service/Graphify adapter](project-knowledge-service.md) реализован отдельно; сквозная миграция пока не завершена.

## Решение

Глобальный Orchestrator Agent ведёт активную сессию: понимает запрос, выбирает контекст, применяет skills и инструменты, выбирает допустимый маршрут, оценивает свидетельства и взаимодействует с пользователем. Workflow Graph задаёт разрешённые действия, переходы, обязательные проверки и лимиты, но не заменяет рассуждение агента Python-контроллером.

Детерминированное ядро проверяет предлагаемые изменения и предоставляет примитивы хранения, версионирования и исполнения. Оно не решает, достаточен ли анализ, какая стратегия реализации лучше или какие файлы семантически релевантны.

```text
Пользователь → Orchestrator Agent
                 ├─ Workflow Graph / политика
                 ├─ Skills / инструменты / необязательное делегирование
                 ├─ Project Knowledge Service → Graphify
                 └─ Детерминированные сервисы
                      ├─ Task Manager: задача и lifecycle
                      ├─ Artifact Repository: версии тел артефактов
                      └─ Graph Runtime: состояние конкретного процесса
```

## Неизменяемая граница Task Manager

Пользователь отдельно подтвердил: текущий Task Manager актуален и не изменяется в этой миграции. Его код, схема SQLite v5, API, guards, MCP/CLI и ресурсы пакета сохраняются. Использование публичного API для ведения задач не является изменением архитектуры пакета.

Каноническое состояние задачи остаётся в `.orchestrator/state/tasks.sqlite3`. `task.yaml`, TaskML и `events.jsonl` не вводятся. Каноническое определение задачи — карточка Task Manager; обязательная отдельная specification не возвращается. Старые документы и артефакты сохраняются как исторические свидетельства, а не становятся новыми требованиями.

`ready` остаётся границей подготовки и исполнения. `ready → active` требует существующий claim даже в одной агентской сессии. Версии, привязки плана/review/Execution Package, blockers и явная пользовательская приёмка не ослабляются ради автономности агента. Состояние процесса не переносится в SQLite задач или историю разговора.

## Роли компонентов

| Компонент | Ответственность |
| --- | --- |
| Orchestrator Agent | Выбор цели следующего действия, маршрута внутри политики, контекста, skills и инструментов |
| Workflow Graph | Объявление допустимых переходов, gates, ожиданий и ограничений |
| Graph Runtime / будущий интерфейс процесса | Проверка и регистрация выбранного агентом шага; не самостоятельный reasoning loop |
| Task Manager | Уже реализованное детерминированное состояние задачи без изменений |
| Artifact Repository | Immutable payload, версия, SHA-256 и проверенное чтение |
| Project Knowledge Service | Независимая от провайдера граница доступа к структурным знаниям и их свежести |
| Graphify | Первый provider единого Project Knowledge Graph для кода и отобранной долговечной документации; не workflow engine и не источник истины задачи |
| Project Memory | Отдельная будущая оперативная память решений с provenance; не часть Project Knowledge Graph и не Task Manager |
| Платформенные адаптеры | Особенности Codex, Claude, Copilot и других хостов, разрешений и инструментов |

Один глобальный агент означает владельца активной сессии, а не глобальный daemon или блокировку всех проектов. Sub-agents необязательны; возможность их запуска зависит от платформы, разрешений и принятой review-политики.

## Ограничения детерминизма

Инструкции агенту не обеспечивают программное enforcement сами по себе. Проверка перехода не предотвращает любую запись, которую агент может выполнить мимо сервиса. Реальные ограничения filesystem, Git и внешних действий должны обеспечиваться средствами хоста и адаптерами; нельзя объявлять наличие таких ограничений по одному тексту skill.

Хеш подтверждает целостность артефакта, но не качество анализа. Приёмка не выводится из разрешения начать реализацию. При неизвестном результате побочного эффекта агент проверяет фактическое состояние, а не повторяет действие вслепую.

## Совместимость и приоритет

Это решение заменяет controller-centric направление дальнейшего развития, но не стирает факты реализации TASK-0002–0004, TASK-0014–0015. Callback GraphRuntime/PreparationWorkflow удалены в TASK-0034 после реализации заменяющего агентского пути; их прежние гайды стали инструкциями миграции. TASK-0028 добавляет отдельный явный process API AgentGraphRuntime без callback dispatch, с revision/definition/wait guards и budgets. TASK-0029 добавляет [AgentPreparation](agent-preparation.md), общий deterministic validation/publication/sync и агентские инструкции в [гайде](../guides/agent-preparation.md). TASK-0030 добавляет [Knowledge Service/Graphify adapter](project-knowledge-service.md), initial load и explicit refresh/query. TASK-0016 добавляет [AgentExecution](agent-execution.md): preflight до claim и явные work units с dependencies/checkpoints/lease/pending guards. TASK-0020 добавляет явный `AgentExecution.precommit_gate` для code-only incremental knowledge refresh. TASK-0033 реализует configurable `KnowledgeRefreshNode` Workflow Graph с explicit full-refresh authorization; node остаётся executor-free и возвращает результат для обычного AgentGraphRuntime CAS/wait flow.

TASK-0017 реализует [execution gates](execution-gates.md): code review, testing, documentation, knowledge refresh, final validation и подготовку acceptance package; результаты предоставляет агент. TASK-0036 добавляет [конструктор определений](workflow-builder.md), композицию подграфов и builder skill с HTML-инспектором. TASK-0037 добавляет отдельный [explicit WorkflowExecutor](workflow-execution.md), доверенные model adapters, заменяемые роли фасадов и workflow snapshot binding к preflight; runtime остаётся executor-free. Полный installed Orchestrator Agent execution skill и durable runtime checkpoints остаются будущими этапами.

В вопросах состояния задачи приоритет имеет [неизменяемый контракт Task Manager](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md). В вопросах нового распределения ответственности — этот документ; реализованные детали явного процесса закреплены в [контракте AgentGraphRuntime](agent-runtime-contract.md). Импортированные англоязычные материалы остаются исходниками для сверки; их controller logic и примеры файловой задачи не переносятся автоматически.

Источники решения: [документ пользователя об агенте](../development/01-agent-centric-orchestrator-architecture.md), [документ о Graphify](../development/01-graphify-integration-ai-orchestrator.md). Факты и пробелы: [архитектурная оценка](../reports/2026-09-17-agent-centric-graphify-assessment.md).
