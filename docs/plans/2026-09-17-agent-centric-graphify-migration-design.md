# Проект миграции к Orchestrator Agent и Graphify

**Статус:** дизайн поэтапной миграции подтверждён пользователем сообщением «Подтверждаю» 2026-09-17. Базовое агент-центричное направление и неизменность Task Manager подтверждены. Это не свидетельство готовности нового runtime; предметные implementation plans создаются для каждого среза.

**Задача:** TASK-0027. **Дата:** 2026-09-17.

## Варианты

| Вариант | Преимущества | Ограничения |
| --- | --- | --- |
| Поэтапный агентский интерфейс поверх сохранённых сервисов — рекомендуется | Сохраняет проверенные guards, артефакты и тесты; позволяет сравнить старый и новый путь | Временно существуют legacy callbacks и новый интерфейс; нужен явный выбор пути |
| Одномоментная замена runtime/preparation | Быстро убирает старый mental model из API | Большая область регрессий, сложнее подтвердить совместимость и восстановление |
| Только инструкции агенту, без нового process API | Меньше Python-кода | Текущий callback flow остаётся прежним; нет явной проверки action/revision и состояния процесса для внешнего агента |

Переименование Python-контроллера в Agent недостаточно. Обратная крайность — убрать все проверки из кода — также не реализует выбранную границу agent/core.

## 1. Ответственность и взаимодействие

Сохраняем Task Manager полностью, Artifact Repository и модели Graph/Node/Result там, где они не требуют controller semantics. Агент читает определение workflow и снимок процесса, получает допустимые действия, выбирает одно, выполняет работу доступными tools/skills и явно подаёт результат на проверку. Детерминированное ядро не вызывает planning/review callbacks, не выбирает достаточность контекста и не делает содержательный review вместо агента.

Предлагаемый процессный интерфейс: inspect, available_actions, submit_result, request_wait, resume_wait, cancel. Конкретные имена и сигнатуры уточняются в первом implementation contract. Graph задаёт допустимые цели и gates; агент не передаёт произвольную команду route.target вне графа. Для v1 можно сохранить однозначные transitions по outcome: агент выбирает действие и подтверждённый outcome, ядро проверяет соответствие. Множественные допустимые цели требуют явного choice-контракта, а не неограниченного target.

Версия процесса отделена от expected_version задачи. Старый результат, повтор submit, чужой wait или changed definition отклоняются без изменения снимка. Limits остаются программными. Существующие step/resume сохраняются временно для совместимости, но перестают быть рекомендуемым способом агентской оркестрации. PreparationWorkflow не расширяется новыми reasoning branches.

Task Manager используется только через публичный API. Его каноническая карточка, review/plan/Execution Package bindings, ready, claim и приёмка остаются прежними. Локальный workflow требует лишь одного агента; scheduler, worker pool и обязательные sub-agents не добавляются.

## 2. Состояние, артефакты и побочные эффекты

Task lifecycle, process state и payload остаются разными владельцами. Новый интерфейс не помещает текущий узел в SQLite задач и не объявляет переписку источником истины. Immutable artifacts публикуются через существующий repository; plan projection сохраняет требования Task Manager. Старые принятые планы и отчёты не перезаписываются новой архитектурой: новые результаты имеют новые версии и ссылки.

Первый срез сохраняет in-memory runtime, честно без restart recovery. Следующим самостоятельным срезом можно добавить checkpoint store в пространстве runs, отдельно от Task Manager, с версией формата, graph version, task definition binding, ссылками на артефакты, wait identity и pending effects. После потери памяти продолжение допустимо только после сверки checkpoint, карточки и фактических файлов.

Общей транзакции SQLite/файлов/Graphify нет. Нужен явный протокол accepted result → pending effects → completed effects; пока pending не разрешён, следующий action запрещён. Внешние действия не получают обещание exactly-once. При timeout после возможной записи ядро возвращает unknown outcome, а агент проверяет историю/снимок вместо слепого retry. Для уже поддерживаемых Task Manager операций сохраняются operation_id и первоначальная версия.

Разрешения workspace и Git остаются у хоста/адаптеров. Наличие workflow gate не мешает агенту физически писать через другой tool; это ограничение должно быть явно отражено в гайдах и тестах. Необратимые действия требуют соответствующих разрешений пользователя независимо от выбранного этапа.

## 3. Знания и интеграция

Project Knowledge Service — независимая граница query/status/refresh, а не собственный graph engine. Для конкретизации предлагается upstream Graphify-Labs/graphify; перед установкой нужно подтвердить идентичность, зафиксировать version/commit и проверить capabilities. MCP client отвечает за query, indexer boundary — за initial load/update. Нельзя выводить существование MCP refresh из MCP traversal tools.

Service возвращает bounded context, evidence/citations, provenance, indexed snapshot, freshness и ограничения. Typed Node/Edge API вводится только после подтверждения реального output провайдера. Источники не обрабатываются как инструкции. Project root фиксирован, переключение к чужому графу исключено wrapper-ом. PR/network tools и global hooks не входят в базовый query adapter.

Freshness сравнивает corpus fingerprint, а не только Git HEAD. Include/exclude policy версионируется; dirty и untracked исходники входят в snapshot, служебные и генерируемые outputs исключены. Снимок после индексации проверяется повторно: если исходники изменились в процессе, результат stale. Code freshness и document semantic freshness независимы.

Начинаем с code-only локального корпуса, без семантической отправки документов внешней модели и без глобального install. Graphify refresh выполняется явно после документации перед final validation, без обязательного commit. Отказ навигационного графа по умолчанию допускает direct discovery с видимым degraded status; required policy согласуется отдельно. Memory service и ABAP не блокируют первый Graphify срез.

## 4. Проверки и последовательность

Сначала фиксируем распределение ответственности и показываем миграционную матрицу. Затем реализуем explicit process-result API и tests: rejected action не меняет state; stale revision/definition/wait запрещены; limits работают; нельзя обойти ready/claim; legacy runtime tests сохранены. Следом переводим подготовку в agent-driven usage с реальными artifacts и отказоустойчивой синхронизацией. Только после эквивалентного покрытия старый callback path можно пометить deprecated; удаление отдельным этапом.

Graphify вводится через provider contract и тестовый transport, затем реальный version-pinned subprocess/MCP smoke test. Fixtures проверяют Python и frontend, rename/delete, source drift, Unicode, исключения секретов и obsolete, отказ refresh и сохранность старого графа. Fake provider tests не считаются подтверждением совместимости с Graphify.

Execution preflight и gates следуют после проверки процесса и знаний: агент выбирает work units, ядро проверяет package/source revision и существующий claim; review, tests, documentation и acceptance сохраняют свидетельства. Затем packaging и end-to-end scenarios. Cross-platform claims делаются только после соответствующих запусков.

На каждом срезе обновляются русские контракт, guide, project status и worklog; старые design/report artifacts сохраняют историю. Существующие created TASK-0016–0022 требуют согласованного уточнения карточек, а не массового завершения или переоткрытия completed работ. После первичной оценки TASK-0027 переведена публичным API в awaiting_input (version 6, без active run/claim) до подтверждения дизайна; новая реализация не объявляется готовой заранее.

## Подтверждение

Пользователь подтвердил поэтапную миграцию с сохранением Task Manager и временной совместимости старого runtime, а для первого Graphify среза — Graphify-Labs/graphify с code-only локальной индексацией без глобальных hooks и обработки документов внешней моделью. Решение зарегистрировано через публичный Task Manager API в TASK-0027, задача возобновлена из awaiting_input в preparing (version 8). Это разрешение на реализацию дизайна, не приёмка будущего результата.

## Основания

- [Принятое распределение ответственности](../architecture/agent-centric-orchestration.md).
- [Направление знаний и предлагаемые контракты](../architecture/project-knowledge-service.md).
- [Оценка реализованного состояния и рисков](../reports/2026-09-17-agent-centric-graphify-assessment.md).
- [Текущий снимок проекта](../project-status.md).
