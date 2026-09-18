# TASK-0036: конструктор процессов v1

**Статус:** реализованный и проверенный кандидат, пользовательская приёмка не получена. Дата: 2026-09-18. Содержательные review выполнены самим агентом; независимый аудит не заявляется.

## Задачи и объём

По поручению пользователя публичным TaskManagerService созданы TASK-0036 «Конструктор workflow v1: библиотека, skill и HTML-инспектор» и TASK-0037 «Исполнение конфигурируемых workflow: модели, фасады и preflight binding». Подпункты оформлены критериями и constraints карточек, а первый план содержит три work units: compiler/library, skill/viewer и документация/проверки.

TASK-0036 прошла реальную AgentPreparation: context/analysis/plan/self-review/package/ready. Первый preflight отклонил `.agents` в work-unit files scope. Guards сохранены: переносимый skill включён в `workflow-library/skills`, его подключение в защищённый каталог проекта выполнено отдельным разрешённым файловым действием. Собственный неизменённый исходный plan сохранён в `.tmp` и immutable Repository; старая потерянная in-memory ссылка закрыта публично после projection conflict. Повторная preparation с актуальным definition binding и планом прошла preflight; получен claim с worker codex-workflow-builder-v1. SQLite напрямую не изменялась.

## Результат

- `orchestrator/workflow_builder.py`: публичные ComponentLibrary/WorkflowBuilder/ResolvedWorkflow/WorkflowBuildError, строгие TOML/контрактные схемы, descriptors и CLI catalog/validate/export.
- Compiler разворачивает подграфы в Graph с namespace и явными выходами в caller, сохраняет дерево композиции и bindings. Data-flow guards отклоняют результаты, не гарантированные на каждом пути, включая первый вход в цикл.
- Project overlay поддерживает patch/replace, проверяет точную совместимость interfaces, не переносит параметры прежней реализации; overrides внутренних узлов применяются после overrides родителя. Снимок фиксирует эффективную политику, provenance и digests.
- Библиотека: пять атомарных блоков, два подграфа Testing/Documentation, семь схем портов. Отдельная проектная библиотека демонстрирует replacement узла без копирования всей композиции.
- Builder skill создан в переносимой библиотеке и подключён в `.agents/skills/orchestrator-workflow-builder`, включая UI metadata и reference. Skill ведёт беседу и использует tooling, не выдавая построение процесса за исполнение.
- `orchestrator/workflow_viewer.py` и HTML asset: самостоятельный локальный inspector с карточками узлов/переходов/exits, раскрытием подграфов, breadcrumbs, вложенным поиском, масштабом и перемещением. Карточки показывают instruction, контракты, config, модельные profiles, provenance и effects. HTML генерируется из того же snapshot, что Graph.
- [Пример инспектора](../../work/workflow-builder/process.html), [снимок JSON](../../work/workflow-builder/process.json), [контракт](../architecture/workflow-builder.md), [guide](../guides/workflow-builder.md).

## Проверки

| Проверка | Результат |
| --- | --- |
| Новый предметный набор | 22/22 passed: реальные compiled Graph/runtime результаты и waits, parent exit routing, независимые экземпляры, replacement, profile/config/budget/provenance, schema/ports/branch/ref/cycle negative cases, export protection |
| Полный root с явным pinned Graphify interpreter | 181 tests; 180 passed, 1 Windows file-symlink skip; 0 failures; 23,901 s |
| Browser smoke, headless Edge через bundled Playwright | Подграф, node config/provenance, edge artifacts, zoom/fit, nested search, profile binding, narrow viewport, hostile instruction как текст; 0 page errors и 0 HTTP(S) requests |
| CLI | Catalog, validate, JSON/HTML export с patch; validate с двумя библиотеками и настоящим project replacement |
| Guide Python | Пример исполнен; создаёт in-memory runtime без действий узлов |
| Compileall, ссылки, diff | Проверены |

Браузерная проверка обнаружила наложение transition на узел из-за алфавитного порядка snapshot. Исправлена раскладка: порядок обхода начинается с entry, exits размещаются отдельным рядом. Повторный smoke прошёл; просмотрены реальные screenshots основного и вложенного графов.

Bundled quick_validate.py был запущен, но существующие Python interpreters не содержат PyYAML. Вместо установки зависимостей выполнены проверки конкретного ограниченного frontmatter/UI формата: name/description, допустимые ключи и длины, отсутствие placeholders, JSON-quoted строки metadata, default_prompt и reference links. Это не успешный запуск официального validator; результат и причина сохранены в skill-checks evidence. `.venv` не изменялась.

## Границы кандидата

Model/capability descriptors не исполняются. Generic runtime не вызывает schema validator автоматически; caller может использовать validate_outputs. Автоматическая материализация payload, публикация aliases результата подграфа, roles фасадов и workflow binding preflight входят в TASK-0037. Skill может использоваться для authoring уже сейчас, но полный устанавливаемый Orchestrator execution skill этим не поставляется.

Library Testing/Documentation — учебные definitions с отдельными summary contracts, не полные действующие execution gates. Не реализованы extends/autoload конфигурации, live statuses, визуальное редактирование, провайдерные fallback/escalation и durable nested runs. Для больших графов раскладка базовая; используется navigation/zoom/pan.

Task Manager, существующие runtime/facade guards, production knowledge pointer, obsolete, .venv и изменения предыдущих этапов сохранены. Claim освобождается публичной передачей настоящих readiness/acceptance artifacts в awaiting_acceptance; разрешение реализовать работу не регистрируется как acceptance.
