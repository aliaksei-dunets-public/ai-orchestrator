# Graph Orchestrator

В этом репозитории разрабатывается графовый оркестратор задач разработки. Прежняя реализация и её документация сохранены в [`obsolete/`](obsolete/README.md) как справочный архив, а не как действующее ядро.

Проектные материалы нового подхода находятся в [`docs/`](docs/README.md):

- [`docs/graph/`](docs/graph/) — маршрутизация запросов, состояние задач и цикл исполнения;
- [`docs/development/`](docs/development/) — подготовка и исполнение задач разработки;
- [`docs/context-knowledge/`](docs/context-knowledge/) — карта знаний проекта.

Разработка идёт поэтапно. Первый рабочий срез — [первичная настройка проекта](docs/guides/onboarding.md) с проверяемым планом `preview/apply`, включая режим self-hosted. **Graph Runtime и Task Manager Service пока не реализованы.** Код из `obsolete/` не выполняет новые контракты.

## Как подключить к своему проекту сейчас

Нужны Git, Python 3.11+ и доступ агента к целевому проекту. Пока доступна **только первичная настройка**: она создаёт конфигурацию и контекст проекта, но не запускает граф и не выполняет задачи.

1. В корне своего проекта добавьте этот репозиторий как submodule в фиксированное место:

   ```powershell
   git submodule add <URL_ЭТОГО_РЕПОЗИТОРИЯ> tools/graph-orchestrator
   git submodule update --init --recursive
   ```

   Подставьте фактический URL репозитория. Готовый пакет для ручного копирования пока не собирается.

2. Попросите агента изучить проект и создать `.tmp/project-answers.json` с названием, назначением, командами проверок и ограничениями. Формат и пример приведены в [подробном гайде](docs/guides/onboarding.md). Проверьте, что в ответах нет секретов.

3. Из корня целевого проекта постройте план без изменения проектных файлов:

   ```powershell
   python tools/graph-orchestrator/graph_orchestrator/onboarding.py preview --target . --core tools/graph-orchestrator --answers .tmp/project-answers.json --output .tmp/onboarding-plan.json
   ```

   Команда покажет точный diff и хеш плана. Проверьте предлагаемые изменения. Если хотите поручить шаги агенту, он должен показать вам diff и дождаться подтверждения **именно этого хеша**.

4. Только после подтверждения примените план:

   ```powershell
   python tools/graph-orchestrator/graph_orchestrator/onboarding.py apply --plan .tmp/onboarding-plan.json --approved-hash <ПОДТВЕРЖДЁННЫЙ_ХЕШ>
   ```

5. Проверьте созданные `.graph-orchestrator/project.json` и `.graph-orchestrator/project-context.md`, затем `git diff` и `git status`. Не коммитьте временные файлы ответов и плана из `.tmp/`; при необходимости добавьте `.tmp/` в `.gitignore` целевого проекта. Если файлы изменились между шагами 3 и 4, применение остановится: создайте новый preview.

Если целевой проект — **сам этот репозиторий**, шаг 1 пропускается. В командах используйте `graph_orchestrator/onboarding.py` вместо пути через `tools/`, а для `--core` укажите `.`. Не создавайте вложенную копию оркестратора.

Последовательность работ описана в [`docs/roadmap.md`](docs/roadmap.md). Новая документация и гайды ведутся на русском языке.
