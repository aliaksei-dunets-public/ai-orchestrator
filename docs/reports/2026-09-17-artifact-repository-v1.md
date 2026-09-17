# Отчёт TASK-0014 — Artifact Repository v1

**Дата:** 2026-09-17  
**Статус:** завершено после Luna High аудита и исправлений, Task Manager version 21  
**Задача:** `TASK-0014`

## Итог

Реализован независимый файловый репозиторий артефактов в `orchestrator.artifact_repository`. Он не смешивает тело артефакта с lifecycle Task Manager или состоянием Graph Runtime и предоставляет проверяемые immutable-версии по ключу `ref + role + version`.

## Изменения

- `ArtifactRepository.put` принимает bytes, bytearray, memoryview и UTF-8 text.
- `put_json` создаёт canonical JSON с детерминированным порядком ключей.
- `get`, `verify` и `list` предоставляют проверенное содержимое или метаданные.
- Манифест хранит контракт, media type, размер, SHA-256 и фиксированное имя payload.
- Оба файла версии записываются со `flush`/`fsync` в staging-каталог; вся версия публикуется единым атомарным `os.rename`.
- Повторная идентичная публикация идемпотентна; другая публикация той же версии отклоняется без перезаписи.
- Некорректные сегменты пути, повреждённый манифест и tampering payload приводят к структурированному `ArtifactError`.
- Добавлен русский guide по использованию и границе с Task Manager/Graph Runtime.

## Проверки

Предметный набор после независимого аудита: 19 тестов, 18 успешных и 1 ожидаемый Windows skip для file symlink. Root/entry junction checks выполняются и проходят. Добавлены fault injection записи manifest и публикации каталога, файловых ошибок, malformed manifest, Windows aliases/reserved names и интеграция plan-проекции с реальным публичным Task Manager API.

Финальные проверки:

- корневой Orchestrator: 34 теста, 33 успешных и 1 ожидаемый Windows skip для file symlink;
- Onboarding: 19 тестов, 18 успешных и 1 ожидаемый skip из-за ограничения Windows на symbolic link;
- Task Manager: 73/73;
- `compileall` для `orchestrator` и `packages`: успешно;
- `git diff --check`: успешно, только стандартные предупреждения Git о переводе LF/CRLF;
- `orchestrator_task_manager.task_cli --project . validate`: `ok: true`, нарушений нет.

Кандидатная ревизия реализации: `artifact-repository-v1:4E46FE48FFD4FD76FF9E883B4F0000F7A3933CE95ED5100BAF47CC8DB4CC9589`.

## Независимый аудит и исправления

Отдельный read-only агент Pascal (`gpt-5.6-luna`, reasoning `high`) выявил 2 P1, 5 P2 и замечание P3 о точности evidence. Все подтверждённые дефекты устранены:

| Замечание | Исправление | Регрессия |
| --- | --- | --- |
| P1: root junction выходит за project_root | Проверяются project boundary и все symlink/junction/reparse-компоненты | Root и entry junction отклоняются; внешний каталог пуст |
| P1: payload остаётся после отказа manifest | Staging всей версии, единый rename, очистка после обычного отказа | Manifest/commit fault не ломает list; повтор put проходит |
| P2: list принимает invalid ref/version; ошибки схемы неверного типа | Валидируются все сегменты и поля; повреждённая схема даёт integrity_error | Invalid directories и manifest поля |
| P2: raw filesystem errors | Публичные IO-операции дают repository_failure; missing version/file различаются | Permission/fault injection, missing payload/manifest |
| P2: Windows identifier aliases | Reserved names/trailing dot запрещены; alias другого регистра отклоняется | Ref/role/version case aliases, reserved names |
| P2: list/payload следуют symlink | Проверка каждого компонента и обоих файлов | Entry junction; file symlink при наличии привилегий |
| P2: guide передаёт несовместимый plan path | Описана проверяемая проекция в task directory и metadata.repository | Repository path отвергается, projection принимается |
| P3: заявленное покрытие шире тестов | Добавлены предметные регрессии и точные результаты | 19 предметных тестов, явный expected skip |

Delta-вердикт Luna: **no findings**. Повторно подтверждены staging/rename, отсутствие partial version, безопасный root/entry path, Windows-safe identifiers, manifest/IO error codes и plan-проекция. Предметные tests: 19, 18 passed + 1 expected Windows file-symlink skip; root/entry junction tests прошли. Архитектура не расширена: ограничения v1 сохранены.

<a id="user-acceptance"></a>

## Пользовательская приёмка

Пользователь поручил после независимого Luna High аудита устранить все замечания и закрыть задачу. Условие выполнено: delta-аудит не выявил новых замечаний, полный набор проверок прошёл. Это явное условное поручение является основанием регистрации приёмки исправленной кандидатной ревизии через публичный `accept_task`; агент не выдаёт собственный review за решение пользователя.

## Граница задачи

В v1 намеренно не входят удаление, retention, внешнее object storage, многопроцессная координация и автоматическая регистрация ссылок в Task Manager. Следующий этап должен связать repository с readiness/execution gates через публичный API Task Manager.
