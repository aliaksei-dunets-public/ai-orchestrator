# Artifact Repository v1 — интеграционный guide

**Статус:** действующий guide; TASK-0014 завершена после независимого аудита и исправлений, 2026-09-17.

## Назначение

`ArtifactRepository` хранит тело структурированных или бинарных артефактов отдельно от состояния задач и запусков. Он отвечает за устойчивую публикацию, immutable-версию, размер и SHA-256. Task Manager по-прежнему является владельцем lifecycle задачи и получает только ссылку и метаданные через публичный API.

Реализация экспортируется из `orchestrator`:

```python
from orchestrator import ArtifactRepository

repository = ArtifactRepository(project_root=".")
record = repository.put_json(
    ref="PLAN-TASK-0014",
    role="plan",
    version="v1",
    value={"objective": "Проверить репозиторий артефактов"},
    contract="plan/v1",
)
print(record.to_dict())
```

Для чтения и проверки используется полная тройка идентификаторов:

```python
stored = repository.get("PLAN-TASK-0014", "plan", "v1")
assert stored.record.sha256 == record.sha256
assert repository.verify("PLAN-TASK-0014", "plan", "v1") == record
```

## Ключ и структура хранения

Уникальным ключом является `ref + role + version`. Поэтому один `ref` может иметь независимые роли `plan`, `plan_review`, `testing` и `acceptance_package`, а разные версии не перезаписывают друг друга.

```text
.orchestrator/artifacts/<ref>/<role>/<version>/
├── manifest.json
└── payload.bin
```

Все сегменты — безопасные одноуровневые идентификаторы. Пути с `/`, `\\`, `..`, управляющими символами и абсолютные пути отклоняются. На всех платформах также отклоняются Windows reserved names, trailing dot и case-insensitive aliases уже существующих сегментов. Регистр идентификаторов сохраняется. Payload не редактируется после публикации. Повторная публикация идентичных payload и метаданных идемпотентна; другое тело или метаданные под тем же ключом возвращают `artifact_exists`.

## Безопасность и целостность

- Payload и manifest сначала записываются во временный staging-каталог, выполняются `flush` и `fsync`; вся версия публикуется единым атомарным rename каталога. Обычный отказ очищает staging, остаток после аварийной потери процесса не попадает в `list`.
- Manifest фиксирует `ref`, `role`, `version`, `contract`, `media_type`, размер, SHA-256 и имя payload.
- `get` и `verify` повторно вычисляют SHA-256 и отклоняют повреждённые manifest/payload с `integrity_error`.
- Все symlink/junction/reparse-компоненты пути запрещены при записи, чтении и list. Отказы доступа и ввода-вывода возвращают `repository_failure`, неизвестный ключ — `artifact_not_found`, отсутствующий файл опубликованной версии — `integrity_error`.
- Репозиторий не импортирует Task Manager, не выполняет SQL и не хранит lifecycle задачи, claim, события или `WorkflowRun`.
- `.orchestrator/artifacts/` относится к локальному runtime-хранилищу и игнорируется Git; проектные документы и отчёты остаются обычными файлами в `docs/`.

Удаление и retention, внешнее object storage и многопроцессная координация сознательно не входят в v1. Защита от конкурентной подмены файловой системы злоумышленником и гарантии при отказе питания также не заявляются.

## Связь с Task Manager и Graph Runtime

Публикация тела и регистрация ссылки — отдельные действия:

1. агент записывает payload через `ArtifactRepository` и получает `ArtifactRecord`;
2. для `plan` агент создаёт проверенную проекцию payload в `.orchestrator/tasks/<TASK-ID>/plan.md`, не перезаписывая посторонний пользовательский файл; путь repository напрямую передавать нельзя — Task Manager его отвергнет;
3. агент передаёт в Task Manager `ref`, `role="plan"`, путь проекции и `record.sha256` через публичный `attach_artifact`; `record.to_dict()` сохраняется в `metadata.repository` (отдельного аргумента `version` у `attach_artifact` нет);
4. Task Manager проверяет свои lifecycle guards и хранит ссылку в карточке и истории;
5. Graph Runtime получает структурированную ссылку на артефакт и не становится владельцем его хранения.

Прямой доступ к SQLite Task Manager запрещён. Если публикация прошла, а регистрация ссылки завершилась конфликтом версии, нужно перечитать задачу и повторить только API-операцию с актуальным `expected_version`; payload повторно записывать не требуется.

## Проверки

Предметные тесты находятся в `tests/test_artifact_repository.py` и покрывают запись/чтение, canonical JSON, роли и версии, отказ от перезаписи, traversal, malformed manifest, hash tampering, частичный отказ публикации, файловые ошибки, root/entry junction, Windows identifier aliases и реальную регистрацию plan-проекции через Task Manager API. Прямой file-symlink test пропускается только при недоступных Windows-привилегиях; junction checks выполняются. Перед приёмкой дополнительно выполняются корневые тесты, тесты Onboarding, тесты Task Manager, `compileall`, `git diff --check` и `orchestrator-tasks --project . validate`.
