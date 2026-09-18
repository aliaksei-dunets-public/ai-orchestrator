# TASK-0037 — исполнение конфигурируемых workflow

**Дата:** 2026-09-18. **Статус:** реализованный и проверенный кандидат для отдельной пользовательской приёмки; независимый аудит не проводился.

## Результат

Добавлен отдельный explicit WorkflowExecutor поверх принятого конструктора TASK-0036. Он вызывает один зарегистрированный executor на шаг, передаёт typed payload и immutable портовые артефакты, материализует composite exits/aliases и сохраняет receipts. AgentGraphRuntime остаётся executor-free; Task Manager Service, SQLite/API, obsolete, .venv и production knowledge pointer не изменялись.

Host-neutral ModelAdapter/ExecutorRegistry проверяют доступность выбранной модели; ответ transport обязан подтвердить provider/model. Fallback разрешается только явной host policy и отражается в immutable inputs/policy/receipt. Нет подстановки current agent, повторов после timeout или автоматической эскалации по качеству. JSON subprocess adapter реально запускает зарегистрированный host wrapper без shell; регистрация Python/argv не переносится в TOML.

WorkflowSource закрепляет snapshot в Plan/Review/Execution Package. Review требует workflow_digest; ready/preflight сверяют текущие доверенные источники. После claim исполнение использует immutable snapshot и проверяет его целостность, сохраняя старую модель при редактировании TOML. Зарегистрированные component roles проходят обычные validators/publication/sync фасадов; package/ready/knowledge guards не заменяются. Gates дополнительно проверяют действующий claim/lease, blockers и package integrity.

Предметные Testing/Documentation handlers не выводят готовность из одного summary: testing totals взяты из typed tool evidence, пустые/противоречивые результаты отклоняются; documentation no_change сверяется с impact. Final validation/AC coverage и приёмка остаются явными.

## Критерии задачи

| Критерий | Реализация и подтверждение |
| --- | --- |
| AC-01 — availability, фактический executor/profile/model, явный fallback, single-agent | ModelAdapter + subprocess transport; exact request/receipt, unavailable profile без invocation, explicit fallback, identity mismatch и unknown-effect reconciliation |
| AC-02 — replaceable roles и прежние guards | ComponentRole/WorkflowRoleRegistry, preparation и execution start_component/submit_component; несовместимый contract/незавершённый компонент/невалидный envelope отклоняются; реальные immutable publications в тестовой Task Manager базе |
| AC-03 — Plan/Review/Package snapshot, stale config и frozen active run | Definition/overlay/component/schema drift до claim, missing WorkflowSource, immutable corruption, missing review digest, drift перед ready; активный slice остаётся на старой модели после редактирования TOML |
| AC-04 — Testing→Documentation, проверяемые артефакты и E2E | Настоящий stdlib unittest tool, typed scoped exports, positive и failed routes; совместимый project/testing-summary@1 исполняется с fixture-expert; normal gates доходят до awaiting_acceptance |

Проверка внешней LLM не заявляется. Model identity подтверждалась честно обозначенными fixture transports; interface допускает установленный CLI/SDK host wrapper, но конкретный провайдер и credentials здесь не подключены. Availability блокирует dispatch явной ошибкой model_unavailable/capability_unavailable; статус Task Manager автоматически не меняется и не подделывается неразрешённый blocked outcome.

## Проверки

- 25 новых предметных тестов: 13 executor/transport и 12 binding/roles integration; passed.
- Финальный root набор: **206 tests, 205 passed, 1 Windows file-symlink skip, 0 failures**, 39.682 s. Existing pinned Graphify 0.9.63 подключён через ORCHESTRATOR_GRAPHIFY_PYTHON. Пакеты Task Manager/Onboarding не менялись и их отдельные suite повторно не запускались.
- Compileall orchestrator/tests/workflow-library/examples — passed; git diff --check — passed.
- Положительный runnable guide: state=succeeded, 5 node evidence, реальный unittest OK, Documentation создал Markdown.
- Негативный runnable guide: ожидаемый exit code 1, state=failed, 3 node evidence, Documentation не запускался и Markdown отсутствует.
- Локальный пример: [результат](../../work/workflow-execution-demo/workflow-result.json), [unittest](../../work/workflow-execution-demo/unittest-result.txt), [созданное описание](../../work/workflow-execution-demo/docs/demo.md). Failed route: [результат](../../work/workflow-execution-failed-demo/workflow-result.json).
- Canonical/project skill синхронизированы; frontmatter/UI/reference checks и локальные ссылки проверены. Official skill validator не запускается без отсутствующего PyYAML; это ограничение сохранено, зависимости не устанавливались.

Тесты явно используют fixture model/knowledge transports в изолированных временных проектах. Это conformance/E2E проверка реального executor, subprocess, tool и публичного lifecycle, не independent semantic audit и не production knowledge refresh.

## Решения и ограничения

Self-review выявил необходимость standalone портовых записей с native Repository SHA/contract вместо ссылки на JSON-поле контейнера; они опубликованы отдельно, node evidence связывает их с receipt. Добавлена новая immutable версия после publication/runtime failure, чтобы recovery не перезаписывал прежний evidence и не повторял эффект. Один parent activation допускает один компонент; старый activation/owner/version не может submit результат нового этапа.

Run/history/pending находятся в памяти; durable recovery, live viewer и installed Agent delivery отсутствуют. Host adapters — доверенная граница identity/effects, не файловый sandbox. Credentials/внешние SDK и прочие configs не покрыты workflow snapshot. Fallback фиксируется отдельно в host run policy. Inner waits остаются в child runtime; автоматической task-status/decision синхронизации и input mapping между отдельными facade roles нет. Учебная библиотека не реализует все outcomes полного Testing/Documentation контракта. Между проверкой и physical effect остаётся filesystem TOCTOU; rollback не обещается.

Работа TASK-0037 подготовлена старым совместимым AgentPreparation API, содержательный self-review и preflight пройдены до изменений, получен настоящий публичный claim. Код выполнен текущим host-agent; production модельные workflow не заявляются. Readiness/acceptance artifacts публикуются публичным Task Manager API с проверенными файлами и отдельным candidate fingerprint. Исторические отчёт/readiness/acceptance TASK-0036 сохранены.

[Контракт](../architecture/workflow-execution.md), [guide](../guides/workflow-execution.md), [дизайн](../plans/2026-09-18-workflow-execution-design.md).
