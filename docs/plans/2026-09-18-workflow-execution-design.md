# Исполнение конфигурируемых workflow — TASK-0037

**Статус:** решение реализации в рамках согласованной задачи; 2026-09-18.

Пользователь поручил продолжить принятый конструктор TASK-0036: исполнять модельные профили, передавать артефакты и интегрировать заменяемые блоки с существующей подготовкой/исполнением.

Рассмотрены три варианта. Выбран отдельный explicit WorkflowExecutor с доверенным реестром host adapters и role handlers. Он оставляет AgentGraphRuntime executor-free и не возвращает удалённый callback GraphRuntime. Встраивание dispatch внутрь runtime смешало бы физические эффекты с процессным CAS. Полная замена фиксированных фасадов произвольным графом потребовала бы повторно реализовать publication/sync/ready/claim/acceptance guards и вышла бы за пределы задачи.

Один step вызывает один узел. Модель выбирается до эффекта по provider/model/reasoning и подтверждается ответом доверенного transport; автоматически подставлять текущего агента вместо неизвестной модели нельзя. Fallback задаётся host-ом явно и фиксируется в run policy/evidence; fallback при timeout и эскалация по качеству отсутствуют. Один subprocess JSON transport поддерживает подключение внешнего host wrapper без зависимости ядра от конкретного API/SDK. Локальный пример использует честно названный fixture, а не заявляет вызов LLM.

Исполнитель хранит стек scopes: новый вход в подграф создаёт новые локальные outputs, exit материализует объявленные aliases и возвращает их caller. Значения проверяются по JSON-схемам и связываются с immutable node evidence. При неизвестном эффекте, ошибке результата или публикации повтор transport запрещён; caller может подать сверенный ответ через recover_result. Межсессионное recovery не реализуется.

WorkflowSource задаётся доверенным host-ом. AgentPreparation сохраняет snapshot в Artifact Repository, добавляет binding в Plan, требует workflow_digest в Review и переносит binding в Package. Preflight заново читает именно настроенные host-ом источники; несовпадение блокирует claim. После claim пакет проверяется на целостность, а component slices строятся из immutable snapshot, без подмены текущими TOML.

Role registry выбирает qualified instance и ожидаемые inputs/outputs/outcomes; несовместимый replacement отклоняется. Компоненты не изменяют Task Manager. Их handler возвращает обычный envelope, который принимает прежний validator фасада. Package, ready и Knowledge gate остаются отдельными детерминированными actions. Учебные Testing/Documentation получают предметные handlers: testing totals берутся из tool evidence; documentation impact сверяется с результатом. Final validation и приёмка не выводятся автоматически из summary.

Проверки: реальные локальные unittest и subprocess fixtures, positive/failed Testing→Documentation, identity mismatch/fallback/timeout/unknown effects, nested exports/waits/budgets, immutable corruption/config drift, role mismatch и normal publication/acceptance lifecycle. Исторические артефакты TASK-0036 не переписываются.
