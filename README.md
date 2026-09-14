# Orchestrator

В этом репозитории разрабатывается графовый оркестратор задач разработки. Прежняя реализация и её документация сохранены в [`obsolete/`](obsolete/README.md) как справочный архив, а не как действующее ядро.

Проектные материалы нового подхода находятся в [`docs/`](docs/README.md):

- [`docs/graph/`](docs/graph/) — маршрутизация запросов, состояние задач и цикл исполнения;
- [`docs/development/`](docs/development/) — подготовка и исполнение задач разработки;
- [`docs/context-knowledge/`](docs/context-knowledge/) — карта знаний проекта.

Разработка идёт поэтапно. Сейчас доступны два пакета: [Onboarding](packages/onboarding/README.md) с проверяемым планом `preview/apply` и [Task Manager Service](packages/task-manager/README.md) с SQLite и локальной панелью просмотра. Внутри Task Manager поставляются полный контракт, инструкция и пример skill; [проектный skill](.agents/skills/orchestrator-task-manager/SKILL.md) указывает на них. **Graph Runtime и автоматическое выполнение задач пока не реализованы.** Код из `obsolete/` не выполняет новые контракты.

## Как подключить к своему проекту сейчас

Нужны Git, Python 3.11+ и доступ агента к целевому проекту. Настройка создаёт конфигурацию и контекст проекта. После неё можно вручную создавать и просматривать задачи через [Task Manager](docs/guides/tasks.md), но граф и автоматическое выполнение пока не запускаются.

1. В корне своего проекта добавьте этот репозиторий как submodule в фиксированное место:

   ```powershell
   git submodule add <URL_ЭТОГО_РЕПОЗИТОРИЯ> tools/orchestrator
   git submodule update --init --recursive
   ```

   Подставьте фактический URL репозитория. Готовый архив всего ядра для ручного копирования пока не собирается; отдельные Python-пакеты Onboarding и Task Manager уже собираются.

2. Попросите агента изучить проект и создать `.tmp/project-answers.json` с названием, назначением, командами проверок и ограничениями. Формат и пример приведены в [подробном гайде](docs/guides/onboarding.md). Проверьте, что в ответах нет секретов.

3. Из корня целевого проекта постройте план без изменения проектных файлов:

   ```powershell
   python tools/orchestrator/packages/onboarding/src/orchestrator_onboarding/onboarding.py preview --target . --core tools/orchestrator --answers .tmp/project-answers.json --output .tmp/onboarding-plan.json
   ```

   Команда покажет точный diff и хеш плана. Проверьте предлагаемые изменения. Если хотите поручить шаги агенту, он должен показать вам diff и дождаться подтверждения **именно этого хеша**.

4. Только после подтверждения примените план:

   ```powershell
   python tools/orchestrator/packages/onboarding/src/orchestrator_onboarding/onboarding.py apply --plan .tmp/onboarding-plan.json --approved-hash <ПОДТВЕРЖДЁННЫЙ_ХЕШ>
   ```

5. Проверьте созданные `.orchestrator/project.json` и `.orchestrator/project-context.md`, затем `git diff` и `git status`. Не коммитьте временные файлы ответов и плана из `.tmp/`; при необходимости добавьте `.tmp/` в `.gitignore` целевого проекта. Если файлы изменились между шагами 3 и 4, применение остановится: создайте новый preview.

6. Чтобы создавать и просматривать задачи, установите независимый пакет в Python-окружение проекта:

   ```powershell
   python -m pip install -e .\tools\orchestrator\packages\task-manager
   orchestrator-tasks --project . list
   orchestrator-tasks-web --project . --port 8765
   ```

   Панель доступна на `http://127.0.0.1:8765/` только локально и только для чтения. Команды и ограничения описаны в [инструкции](docs/guides/tasks.md).

Если целевой проект — **сам этот репозиторий**, шаг 1 пропускается. В командах используйте `packages/onboarding/src/orchestrator_onboarding/onboarding.py` вместо пути через `tools/`, а для `--core` укажите `.`. Не создавайте вложенную копию оркестратора. Установленный пакет также предоставляет команду `orchestrator-onboarding` с теми же `preview/apply`.

Для self-hosting установите пакет командой `python -m pip install -e .\packages\task-manager`. Skill находится в `.agents/skills/` и доступен агенту при работе из этого репозитория. Во внешнем проекте блок в `AGENTS.md`, добавленный онбордингом, укажет агенту путь к skill внутри submodule.

Последовательность работ описана в [`docs/roadmap.md`](docs/roadmap.md). Новая документация и гайды ведутся на русском языке.
