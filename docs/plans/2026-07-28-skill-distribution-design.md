# Изоляция ядра и распределение навыков

**Дата:** 2026-07-28
**Статус:** согласовано

## Контекст

Сейчас `skills/` является единым каноническим каталогом, все entries в
`registries/skills.json` включены, `install_registered_skills` устанавливает
весь реестр, а release artifact содержит весь каталог. Канонический source и
platform-проекции уже разделены, но поставка не различает навыки, обязательные
для ядра, стандартный рабочий набор и специализированные навыки.

Цель изменения — сохранить работоспособный orchestrator из коробки, уменьшить
число ненужных навыков в целевом проекте и разрешить project-owned навыки без
изменения поставляемых оригиналов.

## Решение

Остаётся один репозиторий и один совместимый release. Канонические навыки
делятся на три категории:

- `system` — обязательны для корректной работы ядра;
- `bundled` — универсальный набор, устанавливаемый по умолчанию;
- `optional` — специализированные навыки, устанавливаемые после approval.

Категория является явным полем `distribution` в `registries/skills.json`.
Для читаемости канонические sources располагаются в
`skills/system/`, `skills/bundled/` и `skills/optional/`.

Release artifact содержит все категории. В platform-каталог целевого проекта
installer по умолчанию проецирует только `system` и `bundled`. Поэтому
библиотека остаётся доступной для последующей установки, но не загружает
целевой проект ненужными инструкциями.

## Начальное распределение

### System

- `project-onboarding`
- `task-creator`
- `task-context-validator`
- `security-reviewer`

Task Manager и Health Check остаются runtime-компонентами, а не навыками.
`security-reviewer` относится к system из-за immutable security routing.

### Bundled

- `task-analyzer`
- `plan-writer`
- `plan-reviewer`
- `implementation-runner`
- `coding-discipline`
- `test-designer`
- `test-runner`
- `task-reviewer`
- `code-reviewer`
- `security-gate`
- `documentation-manager`
- `session-reporter`
- `memory-manager`
- `knowledge-curator`
- `orchestrator-auditor`
- `improvement-designer`

### Optional

- `python-code-review`
- `optimizer`
- будущие technology- и domain-specific навыки, включая ABAP.

## Конфигурация целевого проекта

Выбранные optional-навыки хранятся в версионируемом
`.orchestrator/skills.json`:

```json
{
  "schema_version": 1,
  "optional_skills": [
    "python-code-review"
  ]
}
```

Файл не управляет system или bundled: они устанавливаются всегда. Неизвестный
ID или ID не из категории optional является ошибкой конфигурации.

Project-owned навыки находятся в
`.orchestrator/project-skills/<skill-id>/`. Пользователь может скопировать
поставляемый навык, назначить новый ID и изменять копию как самостоятельный
навык. Поставляемые sources и их platform-проекции не редактируются вручную.
Для первой версии нет inheritance, overlay, automatic rebase, package versions
или dependency solver.

## Installation flow

1. Core и полная библиотека копируются из release artifact.
2. Installer валидирует registry и конфигурацию проекта.
3. В staging-каталог копируются все system и bundled навыки.
4. Добавляются optional-навыки, явно перечисленные в
   `.orchestrator/skills.json`.
5. Добавляются валидные project-owned навыки с уникальными ID.
6. Готовая проекция атомарно заменяет текущую platform-проекцию.
7. Health Check проверяет полноту, выбор optional, коллизии и drift.

Onboarding использует активные technology profiles для рекомендации optional
skills. Например, Python profile рекомендует `python-code-review`. Рекомендация
не изменяет проект: запись в конфигурацию и установка выполняются только после
approval пользователя. `optimizer` остаётся доступным в списке optional и
может быть выбран явно.

## Ошибки и безопасность

- Отсутствующий или невалидный system/bundled skill отменяет всю синхронизацию.
- Ошибка optional или project-owned skill сохраняет предыдущую рабочую
  проекцию.
- System skill нельзя отключить project override.
- Коллизия project-owned ID с поставляемым ID запрещена.
- Optional skill без approval не появляется в platform-проекции.
- Ручной drift platform-копии обнаруживается Health Check и устраняется только
  повторной синхронизацией из канонических sources.

## Не входит в scope

- удалённый registry или marketplace;
- Git/path dependencies;
- независимое версионирование отдельных навыков;
- dependency resolution;
- наследование, overlay и automatic rebase;
- автоматическая установка optional-навыков по результатам detection.

## Критерии приёмки

- Чистая установка содержит все и только system + bundled skills.
- `python-code-review` и `optimizer` не проецируются без выбора пользователя.
- Выбранный optional skill устанавливается и повторная синхронизация
  идемпотентна.
- Отказ от рекомендации не изменяет файлы проекта.
- Project-owned skill с новым ID проецируется без изменения оригинала.
- Конфликты ID, неизвестный optional ID и отсутствующий `SKILL.md` отклоняются.
- Неуспешная синхронизация не повреждает предыдущую проекцию.
- Registry, workspace и release artifact согласованы.
- Health Check не возвращает `ERROR` или `CRITICAL`.
- Полная regression suite и workspace/release acceptance matrices проходят.
