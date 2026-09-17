# Граф подготовки задачи до ready — проект решения TASK-0015

**Статус:** реализованный минимальный дизайн TASK-0015; критерии фактического поведения закреплены в [контракте](../architecture/preparation-workflow.md). TASK-0015 принята пользователем и завершена (version 18).

## Объём и выбор архитектуры

Рекомендуется интеграционный `PreparationWorkflow` поверх существующего `GraphRuntime`: он вызывает смысловые адаптеры Context, Analysis, Planning и независимого Plan Review, проверяет их структурированные результаты, публикует артефакты и меняет задачу только через публичный `TaskManagerService`. Отдельный FSM отклонён как дублирование runtime; перенос процессной логики в Task Manager отклонён как смешение владельцев состояния. MCP остаётся интерфейсом внешнего агента, но не нужен между Python-компонентами одного процесса.

## Процесс и артефакты

Последовательность: Context → Analysis → Planning → Plan Review → Build Execution Package → Ready. Отдельная обязательная `specification.md` не возвращается. Адаптеры получают карточку, Project Profile и необходимые результаты предыдущих этапов; они не выбирают следующий узел напрямую. Ядро не уточняет требования по своей инициативе: материал для согласованного уточнения формирует Analysis, а подтверждённое изменение карточки выполняет caller через публичный API. Смена definition version требует нового запуска подготовки; старое одобрение нельзя переиспользовать.

`needs_context` возвращает Analysis к Context с ограничением расширений; `changes_required` возвращает Review к Planning с обратной связью и максимумом двух циклов. `needs_input` и `blocked` сохраняют шаг в текущем in-memory run и фиксируют ожидание/блокер публичным Task Manager API. Ответ требует актуальных `wait_id` и `node_id`; подготовка возобновляется с той же точки без повторного выполнения уже принятых этапов. Нет автоматического восстановления между сессиями.

Context/Analysis — рабочие артефакты repository, не новые Task Manager artifact roles. Plan, Review и Execution Package — проверяемый устойчивый handoff. Одобрение связывается с точной версией/хешем Plan и актуальной версией определения задачи; смена определения аннулирует прежний handoff.

## Граница с Task Manager

Сначала `start_preparation`, затем прикрепление реального plan и approved review, построение компактного Execution Package с `prepared_source_revision`, закрытие активной ссылки и вызов `mark_ready`. Guard Task Manager остаётся обязательным, блокеры и конфликт версии не обходятся.

Task Manager принимает plan только из `.orchestrator/tasks/<ID>/`: immutable payload repository должен иметь безопасную проверенную проекцию в каталоге задачи. Метаданные сохраняют repository key и SHA-256; проекция проверяется повторно перед `ready`. Нельзя подавать repository payload path непосредственно как Task Manager plan path.

Оба handoff-mode в этом компоненте заканчиваются на `ready`: claim/исполнение — TASK-0016, а не автоматический побочный эффект подготовки. Неизвестный outcome, malformed adapter result или неактуальная привязка отклоняются до публикации handoff. Принятый runtime-result синхронизируется отдельной очередью действий; сбой сохраняет cursor, запрещает следующий узел и позволяет явно повторить только оставшиеся действия. Конфликт версии не перечитывается автоматически: `reconcile` требует явно прочитанную caller-ом версию и запрещает менять definition/подготовительные артефакты. Общей транзакции файлов/runtime/Task Manager и защиты от неопределённого commit outcome v1 не обещает.

## Проверки и документация

Интеграционные tests в TemporaryDirectory: happy path до `ready`; Context/Analysis/Review waits и правильный resume; blocker и разрешение; revision cycle и его предел; stale review/plan/definition; modified plan; открытый внешний blocker; Task Manager version conflict; malformed results без ready; deferred без claim/исполнения; проверяемые repository refs. Русский контракт и guide должны отражать фактическую семантику и ограничения. Полные root, Task Manager и Onboarding suites запускаются перед передачей на пользовательскую приёмку.
