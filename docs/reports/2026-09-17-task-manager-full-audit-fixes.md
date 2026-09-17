# Полный аудит Task Manager: результаты и исправления

**Дата:** 2026-09-17  
**Область:** прямой Python API, MCP stdio, onboarding, полный lifecycle от создания до архивации  
**Источник замечаний:** отдельный агент-аудитор на `gpt-5.6-luna/high`  
**Статус:** исправления реализованы, регрессионные проверки пройдены

## Итог

Task Manager пригоден для стабильного взаимодействия внешнего агента через MCP stdio и внутреннего Python-оркестратора через прямой `TaskManagerService`. Аудит не выявил P0-проблем. Четыре P1-проблемы исправлены, три замечания меньшего приоритета закрыты кодом или явно зафиксированы как ограничение платформы.

## Найденные и исправленные проблемы

1. **MCP не исполнял опубликованную схему входов.** Строки вроде `"false"` и `"one-ref"` могли попасть в сервис и быть неявно приведены. Добавлен локальный строгий validator для object/array/string/integer/boolean/enum/required/additionalProperties. Проверка выполняется до handler и не добавляет внешней зависимости.
2. **Нестабильный `structuredContent`.** Списки и текст возвращались не-объектами. Теперь каждый успешный результат — объект: исходные объекты сохраняются, списки и строки обёрнуты в `{"value": ...}`; ошибки остаются в `{"error": ...}`.
3. **Неполный MCP lifecycle.** `notifications/initialized` больше не активирует сервер без предыдущего `initialize`. Запросы без ненулевого `id` не получают ответ и не вызывают инструменты или мутации. Добавлена проверка согласования версии `2026-07-28`.
4. **Сырой `TypeError` в прямом API.** `link_workflow_run(relation=[])` теперь даёт предметный `TaskError(validation_failed)`.
5. **Fingerprint операции не учитывал event context.** Нормализованный контекст включён в отпечаток; одинаковый `operation_id` с изменённым actor/source теперь корректно даёт `operation_conflict`.
6. **Неполная валидация direct API.** `evidence_refs` требует список строк, `blocking` — настоящий boolean; `evidence_refs` можно передать как единственное изменение определения.
7. **Недостаточная диагностика повреждённого blocker payload.** `health_check` сообщает `blocker_shape_invalid`, если `blocking` или `evidence_refs` имеют неверную форму.
8. **Windows symlink.** Пропуск одного onboarding-теста оставлен ожидаемым ограничением Windows и не маскируется под успешную проверку.

## Сценарии аудита

Проверены создание, чтение, история, подготовка, уточнение, артефакты, execution package, ready guard, claim/lease, workflow run, блокировка/разблокировка, user decision, awaiting acceptance, accept/complete, archive, restart, изоляция разных project root, ошибки версий, export/backup/restore, MCP handshake и onboarding health check.

## Проверки

- Task Manager: **73 теста, OK**.
- Onboarding: **19 тестов, OK; 1 ожидаемый skip** на Windows symlink.
- Корневой Orchestrator: проверка сохраняется отдельным набором проекта.
- Реальный MCP subprocess handshake: `initialize → notifications/initialized → tools/list → tools/call`.
- Проверены object-shaped `structuredContent`, строгая schema validation и отсутствие побочного эффекта у notification без `id`.
- После сборки wheel нужно повторно проверить содержимое и запуск в изолированном окружении; stale wheel не считается результатом проверки.

## Архитектурный вывод

Для внешнего агента остаётся один общий пакет MCP-кода и отдельный stdio-процесс на каждый проект с фиксированным корнем и отдельной SQLite-базой. Для Python-оркестратора в том же процессе оптимален прямой `TaskManagerService`; CLI — резервный интерфейс диагностики. MCP не дублирует guards и не получает прямого доступа к SQLite.
