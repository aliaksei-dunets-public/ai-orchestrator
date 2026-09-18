# Исправления после повторного аудита Agent Runtime

**Статус:** рабочий дизайн в рамках поручения пользователя создать новую задачу и приступить к подтверждённым исправлениям, 2026-09-18. Приёмка результата отдельная. Основание — [оценка аудита](../reports/2026-09-18-agent-runtime-audit-followup-triage.md).

## Требования к выходам

Выбран совместимый вариант: новый параметр Node `required_outputs_by_outcome` содержит mapping объявленного outcome в список обязательных ключей data/artifacts. Запись для конкретного outcome полностью заменяет базовый `required_outputs`; пустой список явно снимает требования к выходам этого исхода. Если записи нет, действует прежний список. Наборы нормализуются в tuple, mapping копируется и становится неизменяемым. Неизвестный outcome и неправильная форма списка отклоняются при создании Node. Graph.from_dict и available_actions поддерживают поле.

Пример: `required_outputs=("plan",)`, overrides `needs_input: []`, `blocked: []`, `failure: ["diagnostics"]`. Успех требует plan, вопрос не требует готового плана, ошибка требует диагностику. Доменные outcomes задаются явно и не классифицируются по похожему имени.

Альтернатива с пропуском проверки для трёх встроенных имён короче, но меняет существующие требования к ошибкам и не выражает доменные исходы. Полная замена старого поля mapping дала бы чистый API, но потребовала бы миграции всех callers. Выбранное дополнение сохраняет действующие графы и позволяет адресно исправить ограничение.

Проверки формы артефактов, JSON, node/outcome, wait identity/revision, бюджета и definition binding остаются обязательными. Тесты должны проверять готовый результат и паузу отдельно, включая неизменность отвергнутых действий и отсутствие обхода guards через пустой override.

## Подтверждение KnowledgeRefresh

Результат запроса разрешения получает runtime outcome `needs_input`, а `data.result.status` остаётся `awaiting_confirmation`. Graph KnowledgeRefreshNode и knowledge stage execution gates объявляют needs_input с self-target. Стандартный runtime сохраняет wait; узел исполняется повторно только после явного ответа. Фасад gates использует runtime outcome узла, а не доменный status, для submit.

Фасад сохраняет исходный request ожидания и использует его при продолжении без request; изменить policy при активном ожидании нельзя. Ошибочный/неодобренный ответ или отсутствие decision ref не запускают full refresh. Проверки на терминальный run, доступный budget и некорректный request выполняются до запуска refresh. Это необходимо, чтобы операция не выполняла внешний эффект, который runtime уже не способен принять.

Повторная publication knowledge evidence использует новую immutable version вместо перезаписи v1: запрос, повторный отказ/запрос и успешный результат не должны конфликтовать в Artifact Repository. Доменный status сохраняется для readiness/commit policy. Остальные gate outcomes и Task Manager lifecycle не расширяются.

Альтернатива с новым специальным runtime outcome `awaiting_confirmation` расширяет generic протокол без необходимости: стандартный needs_input уже выражает эту паузу. Adapter вне reusable узла оставлял бы его собственный graph несовместимым с runtime.

## Проверки, документация и границы

Предметные тесты: overrides/loader/изоляция описания; полный submit→resume→success/failure для узла с итоговым output; реальный KnowledgeRefreshNode→runtime, одобрение/отказ/decision ref; AgentExecution gates→confirmation→refresh→final stage с immutable evidence и сохранением policy.

Обновляются структурный и агентский контракты, agent-runtime и project-knowledge guides, execution-gates guide/контракт, docs README, project-status, roadmap, MANIFEST и worklog. Исторический аудит сохраняет факт первоначального отказа; исправления описываются новым отчётом. Проверяются ссылки и runnable примеры.

Не входят: бесплатные бюджетные slots, перепривязка definition, MCP delivery, persistence, scheduler, SQL/schema Task Manager, публикация знаний production проекта, изменение соседних задач и приёмка без решения пользователя. Проверки — профильные suites, затем полный root suite с real pinned Graphify fixture при доступном interpreter; Task Manager/Onboarding затрагиваются только через публичные интеграционные контракты.
