---
language: ru
translation_of: docs/guides/deployment-to-target-project.md
---

# Развёртывание AI Orchestrator в целевом проекте

[English version](deployment-to-target-project.md)

**Версия гайда:** 2.0
**Целевая версия оркестратора:** 1.2.0
**Основной сценарий:** agent-led onboarding с core, подключённым на месте

## 1. Что получится в результате

Пользователь добавляет AI Orchestrator в проект как Git submodule либо копирует
его пакет в отдельный каталог. Этот каталог сразу становится активным core:
онбординг не копирует core в `.orchestrator/core` и не требует устанавливать
Python-пакет глобально.

После этого пользователь указывает агенту путь к
`skills/system/project-onboarding/SKILL.md`. Агент:

1. без записи исследует core и целевой проект;
2. задаёт вопросы только там, где данные неоднозначны;
3. показывает один полный preview всех изменений;
4. непосредственно перед записью запрашивает подтверждение;
5. применяет утверждённый план;
6. проверяет конфигурацию, Health Check и идемпотентность;
7. автоматически выполняет rollback при `ERROR` или `CRITICAL`;
8. сообщает итог и пути к отчёту.

Core остаётся переносимым и platform-neutral. Различия Codex, Google
Antigravity, GitHub Copilot VS Code и Claude VS Code задаются platform
profiles, а не ветвлениями в Python-коде.

## 2. Что нужно заранее

- целевой проект и права на запись в него;
- Python 3.11 или новее;
- Git, если выбран submodule;
- локальная копия AI Orchestrator;
- агент, способный прочитать skill и выполнить локальную команду Python.

Желательно заранее проверить исходное состояние:

```powershell
git status --short
python --version
```

Незакоммиченные пользовательские изменения допустимы, но агент обязан
сохранить их. Если существующий файл конфликтует с ownership-маркерами
оркестратора, запись блокируется вместо автоматического разрешения конфликта.

## 3. Подключите core

Выберите один способ.

### Вариант A. Git submodule — рекомендуется

Из корня целевого проекта:

```powershell
git submodule add <ORCHESTRATOR_REPOSITORY_URL> tools/ai-orchestrator
git submodule update --init --recursive
```

Преимущества:

- версия core закреплена Git commit;
- обновление и rollback прозрачны;
- код оркестратора отделён от кода проекта;
- одна и та же структура работает на разных агентных платформах.

Ожидаемый путь к skill:

```text
tools/ai-orchestrator/skills/system/project-onboarding/SKILL.md
```

### Вариант B. Скопированный пакет

Скопируйте полный репозиторий или поставляемый пакет в отдельный каталог,
например:

```text
target-project/
└── tools/
    └── ai-orchestrator/
        ├── orchestrator/
        ├── config/
        ├── profiles/
        ├── registries/
        ├── skills/
        └── workflows/
```

Не смешивайте каталоги core с одноимёнными каталогами целевого проекта.
Обновление такой копии остаётся ответственностью проекта.

Core может находиться и рядом с целевым проектом. Внешний абсолютный путь менее
переносим, поэтому агент отдельно запросит подтверждение такого выбора.

## 4. Запустите онбординг через агента

Передайте агенту короткий запрос:

```text
Проведи онбординг этого проекта по skill:
tools/ai-orchestrator/skills/system/project-onboarding/SKILL.md
```

Если core расположен вне проекта, передайте его абсолютный путь. Пользователю
не нужно запускать `orchestrator.release.install_artifact`, добавлять core в
`PYTHONPATH` или вручную вызывать внутренние Python API.

Skill предписывает агенту использовать детерминированный script:

```text
skills/system/project-onboarding/scripts/onboard_project.py
```

Script возвращает JSON и не ведёт диалог через `input()`. Диалогом владеет
агент: он переводит структурированные вопросы в интерфейс текущей платформы и
возвращает выбранные ответы script.

## 5. Этап inspect: только чтение

Сначала агент выполняет `inspect`. На этом этапе файловые изменения запрещены.
Проверяются:

- расположение и версия core;
- обязательные каталоги core;
- признаки доступных agent platforms;
- признаки технологического стека;
- структура, документация и команды проекта;
- существующие Project Context и ownership-маркеры;
- возможность записать переносимый относительный `core_path`.

Эквивалентная диагностическая команда:

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py inspect --target .
```

Команда приведена для диагностики и автоматизации. В обычном сценарии её
вызывает агент.

## 6. Как агент задаёт вопросы

Если доказательств достаточно, агент не спрашивает уже известное. Вопрос
появляется только при неоднозначности, например:

- обнаружено несколько agent platforms;
- найдено несколько подходящих technology profiles;
- core находится вне целевого проекта;
- автоматическая рекомендация небезопасна.

Каждый вопрос содержит:

- понятную формулировку;
- два или более допустимых варианта;
- описание последствий каждого варианта;
- одну рекомендацию, когда её можно сделать безопасно.

Неизвестные идентификаторы вопросов и ответов отклоняются. Ответы, похожие на
credentials или секреты, не принимаются и не сохраняются.

## 7. Этап plan: полный preview

После разрешения неоднозначностей агент запускает `plan`. Результат имеет
статус `preview_ready` и включает:

- выбранный core, platform profile и technology profiles;
- полный diff каждого создаваемого или изменяемого файла;
- команды и проверки после установки;
- rollback manifest;
- fingerprint исходного состояния;
- детерминированный `plan_hash`.

План обычно охватывает:

| Файл | Назначение |
| --- | --- |
| `.orchestrator/config.json` | версия схемы, in-place core и выбранные profiles |
| `.orchestrator/project-context.md` | подтверждённые факты о проекте |
| platform instruction file | короткий managed bootstrap block |
| platform skill projection | тонкая ссылка-инструкция на канонический skill |
| `.gitignore` | исключение operational state |

Для Codex instruction target — `AGENTS.md`, для Copilot —
`.github/copilot-instructions.md`, для Claude — `CLAUDE.md`. Antigravity
использует repository skill projection; постоянный instruction target не
назначается, пока он не подтверждён profile.

Содержимое вне маркеров
`<!-- ai-orchestrator:start -->` и `<!-- ai-orchestrator:end -->` принадлежит
пользователю и сохраняется.

## 8. Единственное подтверждение перед записью

Агент показывает preview и запрашивает подтверждение непосредственно перед
первой записью. Подтверждение означает согласие:

- применить именно показанный `plan_hash`;
- создать резервные копии затрагиваемых файлов;
- выполнить проверки после записи;
- автоматически откатить изменения при `ERROR` или `CRITICAL`.

Если пользователь отменяет операцию, онбординг завершается без записи.

Если после preview изменился любой планируемый входной файл, fingerprint уже
не совпадает. Apply возвращает `stale_preview`, ничего не записывает, а агент
строит и показывает новый preview.

## 9. Этап apply

После подтверждения агент передаёт утверждённый hash:

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py apply `
  --target . `
  --answers .orchestrator/onboarding-answers.json `
  --approved-plan-hash <PLAN_HASH>
```

Файл ответов — необязательный transport для headless-сценария. Агент может
передать те же ответы через `--answers-json`; credentials туда не помещаются.

Перед публикацией workflow создаёт backup manifest. Файлы записываются через
временный файл в том же каталоге и атомарную замену.

## 10. Проверки и автоматический rollback

После записи workflow проверяет:

1. контракт `.orchestrator/config.json`;
2. managed block в platform instruction file;
3. ownership-маркеры Project Context;
4. Health Check core;
5. здоровье project Task Registry;
6. пустой diff повторного onboarding plan.

Успех возвращает статус `completed`. Если проверка даёт `ERROR` или
`CRITICAL`, workflow без нового вопроса использует ранее выданное разрешение
на rollback:

- восстанавливает прежние версии файлов;
- удаляет только файлы, созданные этой onboarding session;
- сверяет hashes восстановленного состояния;
- возвращает `rolled_back` либо `rollback_failed`.

Ручной повтор rollback доступен агенту:

```powershell
python tools/ai-orchestrator/skills/system/project-onboarding/scripts/onboard_project.py rollback --target .
```

## 11. Результирующая структура

Типичный проект после успешного onboarding:

```text
target-project/
├── AGENTS.md                         # либо instruction file другой платформы
├── .gitignore
├── .orchestrator/
│   ├── config.json                   # tracked
│   ├── project-context.md            # tracked
│   ├── skills.json                   # approved optional skills, tracked
│   ├── project-skills/               # project-owned skill sources, tracked
│   ├── tasks/
│   │   ├── contexts/                 # Task Context, tracked
│   │   ├── checkpoints/              # execution state, ignored
│   │   ├── drafts/                   # Task Context drafts
│   │   └── tasks.json                # registry, ignored
│   └── onboarding/
│       ├── report.json               # итог
│       ├── session.json              # operational state
│       └── backups/                  # operational state
└── tools/
    └── ai-orchestrator/              # активный in-place core
```

Также создаётся repository skill projection по пути из platform profile.
Полная логика не дублируется в instruction file: bootstrap указывает агенту
на config и канонический skill.

System и bundled skills устанавливаются автоматически. После подтверждения
technology profiles агент показывает `recommended_optional_skills`, но не
изменяет проект до явного approval. Одобренные IDs записываются в
`.orchestrator/skills.json`, после чего installer синхронизирует platform
projection. Пользовательский навык создаётся в
`.orchestrator/project-skills/<новый-id>/` и не изменяет поставляемый оригинал.

## 12. Что коммитить

Обычно версионируются:

- способ подключения core и его закреплённая версия;
- `.orchestrator/config.json`;
- `.orchestrator/project-context.md`;
- `.orchestrator/skills.json`;
- `.orchestrator/project-skills/`;
- managed block в platform instruction file;
- repository skill projection;
- изменения `.gitignore`.

Operational state исключается:

```gitignore
# AI Orchestrator operational state: start
.orchestrator/onboarding/session.json
.orchestrator/onboarding/backups/
.orchestrator/tasks/tasks.json
.orchestrator/tasks/*.tmp
.orchestrator/tasks/checkpoints/
.orchestrator/telemetry/
# AI Orchestrator operational state: end
```

Проверьте фактический diff до commit:

```powershell
git status --short
git diff
```

## 13. Повторный запуск и обновление

Повторный onboarding использует тот же skill. Если config и проект не
изменились, preview не содержит файловых изменений. Ручной текст вне managed
blocks сохраняется.

Для submodule обновление core выполняется обычным Git-процессом:

```powershell
git -C tools/ai-orchestrator fetch
git -C tools/ai-orchestrator checkout <APPROVED_VERSION_OR_COMMIT>
```

После обновления снова попросите агента провести onboarding. Он покажет
миграционный diff и запросит подтверждение только перед записью.

Для скопированного пакета сначала обновите его отдельным контролируемым
процессом, затем повторите тот же agent-led onboarding.

## 14. Проверка отдельных workflows

После onboarding можно ограничить тестовую конфигурацию одной или несколькими
workflow, если immutable security gates остаются включёнными. Такое ограничение
нужно хранить как явный project override и отражать в тестовом evidence.

Для продуктивного тестирования:

1. выберите workflow под проверкой;
2. оставьте обязательные security и completion gates;
3. выполните позитивный, отказной и rollback-сценарии;
4. верните полный набор workflow перед общей приёмкой;
5. запустите strict Health Check.

Локальная настройка не может ослабить immutable security policies.

## 15. Диагностика

### Агент снова задаёт уже разрешённый вопрос

Убедитесь, что агент передал одинаковый versioned answers object в `plan` и
`apply`. После изменения ответов нужен новый preview и новый `plan_hash`.

### Apply сообщает `stale_preview`

Один из планируемых файлов изменился после preview. Это защита от применения
устаревшего согласия. Попросите агента повторить inspect/plan и покажите новый
diff.

### Core не найден

Проверьте, что передан именно путь к
`skills/system/project-onboarding/SKILL.md`, а выше него существуют
`orchestrator`, `config`, `profiles`, `registries`, `skills` и `workflows`.

### Конфликт ownership-маркеров

Не удаляйте пользовательский текст. Исправьте непарные или вложенные markers
вручную либо выберите другой instruction target, затем повторите preview.

### Получен `rolled_back`

Откройте `.orchestrator/onboarding/report.json`: изменения проекта уже
восстановлены и проверены. Устраните причину validation failure и начните новый
onboarding.

### Получен `rollback_failed`

Автоматическое восстановление не доказано. Не продолжайте task execution.
Сохраните session/report, сравните backup manifest с рабочим деревом и
восстановите файлы вручную.

## 16. Критерии готовности

Онбординг завершён, когда:

- результат имеет статус `completed`;
- `.orchestrator/config.json` указывает на фактический in-place core;
- выбранные profiles соответствуют проекту;
- Project Context основан на evidence и не содержит секретов;
- пользовательский текст вне managed blocks сохранён;
- повторный plan не предлагает изменений;
- Health Check не содержит `ERROR` или `CRITICAL`;
- onboarding report доступен пользователю.
- canonical memory/knowledge stores существуют и не исключены из Git;
- `.orchestrator/memory/proposals/`, `.orchestrator/knowledge/indexes/` и
  `.orchestrator/migrations/backups/` исключены из Git;
- `python -m orchestrator context --root . --mode standard` возвращает bounded
  schema-version-1 context pack.

Во время первого onboarding `knowledge-curator` дополнительно выполняет
read-only inventory проекта и возвращает `answers.knowledge_graph`. Proposal
показывается в полном preview рядом с остальными file diffs и входит в тот же
`plan_hash`. После approval onboarding создаёт canonical nodes/edges, перестраивает
ignored graph index и откатывает graph вместе с остальными файлами при
`ERROR`/`CRITICAL`. Пустой proposal допустим и не создаёт выдуманных сущностей.

Нормативные контракты: [английская архитектура оркестратора](../architecture/orchestrator-core.md),
[Task Layer](../architecture/task-layer.md) и
[контракты компонентов](../architecture/component-contracts.md).
