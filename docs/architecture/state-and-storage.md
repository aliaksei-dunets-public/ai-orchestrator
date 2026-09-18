# Состояние и хранение Orchestrator

> **Новое распределение ответственности:** [Orchestrator Agent](agent-centric-orchestration.md) выбирает маршрут, Graph Runtime хранит process state. Task Manager с SQLite не изменяется. [Knowledge Service](project-knowledge-service.md) хранит immutable graph/index в Artifact Repository и current pointer отдельно; это не хранилище задач и не checkpoint. Durable process store пока не реализован.

**Статус:** согласованная архитектурная граница, актуализирована 2026-09-18 после удаления callback-пути TASK-0034. Хранилище задач, core in-memory Graph Runtime и Artifact Repository v1 реализованы. Подготовка реализована в [AgentPreparation](agent-preparation.md); прежний callback PreparationWorkflow удалён.

## Владельцы данных

| Данные | Владелец | Расположение | Git |
| --- | --- | --- | --- |
| Снимок задачи, события, версии, claim, блокеры, решения пользователя | Task Manager Service | `.orchestrator/state/tasks.sqlite3` | Нет |
| Тело артефакта, роль, версия и SHA-256 | Artifact Repository v1 | `.orchestrator/artifacts/<ref>/<role>/<version>/` | Нет, локальное runtime-хранилище |
| Plan и каноническое определение задачи | Task Manager + проектные документы | `.orchestrator/tasks/TASK-xxxx/plan.md` и ссылка/хеш в карточке | Документ можно версионировать |
| Текущий узел, results, revision, response и history агентского запуска | AgentGraphRuntime v1 | В памяти единственного AgentGraphRuntime | Не применимо |
| Execution checkpoint, completed units и pending/unknown effect cursor | AgentExecution | В памяти сессии; immutable preflight/results отдельно в Artifact Repository | Не применимо |
| Будущие контрольные точки и рабочие материалы запуска | Будущий Graph Runtime | `.orchestrator/runs/` — пространство для расширения, не обязательное хранилище v1 | Политика будет определена при реализации сохранения |
| Profile и Context проекта | Onboarding | `.orchestrator/project.json`, `project-context.md` | Да |
| Project Knowledge Graph (код + отобранная долговечная документация), indexed snapshot, provider identity/coverage | ProjectKnowledgeService + Artifact Repository | `.orchestrator/artifacts/project-knowledge/` | Нет |
| Current knowledge pointer, writer lock, temporary build | ProjectKnowledgeService | `.orchestrator/knowledge/` | Нет |

SQLite — единственный источник истины о состоянии задачи. `task.yaml` и `events.jsonl` не являются активным контрактом хранения. Git-версия документа не заменяет версию задачи и её событий. Внешние трекеры могут быть только проекциями.

## Публичная граница Task Manager

Orchestrator использует публичный API пакета `orchestrator-task-manager`, а не SQL или внутреннюю структуру таблиц. Действующая форма возвращаемого снимка определяется [контрактом пакета](../../packages/task-manager/src/orchestrator_task_manager/resources/docs/contract.md) и его API. Вложенные YAML-модели импортированных документов не являются альтернативным API.

Каждая мутация требует актуальную `expected_version`. При конфликте вызывающая сторона перечитывает задачу и повторно оценивает намерение. Состояние запуска не помещается в метаданные задачи: Task Manager хранит только `active_run_ref` и историю ссылок `workflow_runs`.

## Документы и готовность

Task Manager не создаёт plan и дополнительные артефакты. Каноническое определение задачи находится в карточке Task Manager; вызывающая сторона публикует тело через `ArtifactRepository`, затем регистрирует только ссылки и метаданные через публичный `attach_artifact`. Для `plan` Task Manager требует проверенную проекцию payload внутри `.orchestrator/tasks/<TASK-ID>/`, а не repository path; проекция имеет тот же SHA-256, repository key/path/version сохраняются в metadata. Перед `ready` сервис повторно проверяет plan и привязку одобрения и Execution Package к той же версии плана. Старые `specification.md` сохраняются для совместимости, но не являются обязательными.

Artifact Repository v1 хранит JSON-манифест и payload отдельно от SQLite, готовит оба файла во staging-каталоге с `fsync` и публикует всю версию одним атомарным rename. Он не перезаписывает опубликованную версию и проверяет размер/SHA-256 при чтении. Symlink/junction/reparse-пути запрещены; trailing dot, Windows reserved names и aliases другого регистра отклоняются. Отказ записи до публикации не оставляет видимой неполной версии. Наличие хеша подтверждает целостность тела, но не достаточность определения задачи или качество плана. Минимальные границы артефактов для Graph Runtime описаны в [контракте Graph Runtime v1](graph-runtime-contract.md); семантическая проверка остаётся у владельца контракта.

Изменение зарегистрированного документа требует повторной регистрации и подготовки нового одобрения и пакета. Нельзя вручную переписать SQLite или считать задачу готовой по наличию файлов.

## Граница процесса

TASK-0030 добавляет optional max_bytes в repository get/verify без изменения старых вызовов; JSON manifest ограничен 64 KiB, payload читается bounded и проверяется по размеру/SHA-256. Knowledge Service задаёт свои budgets 2 MiB для index и 32 MiB для graph. Это изменение core repository, не пакета Task Manager.

Task Manager отвечает на вопрос «в каком состоянии задача?». Graph Runtime отвечает «на каком шаге находится конкретный запуск?». `ready` остаётся устойчивой границей между подготовкой и исполнением; `active` достигается только атомарным claim.

Первый runtime — простой движок переходов для одного агента в реальном времени, со состоянием запуска в памяти. Отдельная SQLite runtime и инфраструктура конкурирующих исполнителей не требуются. Запись ссылки через Task Manager не сохраняет текущий узел графа и не обеспечивает восстановление после потери сессии. Закрытие ссылки само по себе не доказывает завершение процесса. [Контракт запуска](workflow-run.md) и [пауза](workflow-pause-resume.md) определяют минимальный объём v1.

TASK-0028 добавляет [AgentGraphRuntime](agent-runtime-contract.md) с explicit result submission, отдельным принятием response, revision/definition/wait guards и in-memory action history. История не помещается в Task Manager и не durable. Публичная task definition читается caller-ом; process revision не заменяет task.version. TASK-0029 добавляет [AgentPreparation](agent-preparation.md): явные results, immutable publication, защищённая plan projection, публичные ready guards и pending effects. Неизвестный task effect требует отдельной сверки истории; общей транзакции и restart recovery по-прежнему нет.

## Приоритет документов

Этот документ заменяет предложения о файловом каноническом состоянии задач в импортированных материалах `docs/graph/` и `docs/development/`. Их процессные идеи остаются материалом для дальнейшего согласования, но примеры `task.yaml`, `events.jsonl` и `FilesystemTaskRepository` не должны использоваться для новой реализации.

AgentPreparation связывает подготовительные runtime results, immutable payload и публичные Task Manager transitions до реального `mark_ready`. Общей транзакции этих владельцев нет: pending sync запрещает следующий шаг; восстановление после обычной ошибки явно выполняет caller. Execution gates, автоматическое восстановление между сессиями и checkpoints пока не реализованы.
