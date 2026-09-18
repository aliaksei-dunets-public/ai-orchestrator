# Orchestrator

В этом репозитории разрабатывается агент-центричный оркестратор задач разработки: глобальный Orchestrator Agent ведёт процесс, Workflow Graph ограничивает допустимые маршруты, а детерминированные сервисы проверяют и хранят состояние. Прежняя реализация и её документация сохранены в [`obsolete/`](obsolete/README.md) как справочный архив, а не как действующее ядро.

Новое [архитектурное направление](docs/architecture/agent-centric-orchestration.md) и [Project Knowledge Service с Graphify](docs/architecture/project-knowledge-service.md) зафиксированы 2026-09-17. Task Manager с SQLite сохраняется без изменений. Пользователь подтвердил [поэтапный дизайн миграции](docs/plans/2026-09-17-agent-centric-graphify-migration-design.md); первый Python-срез [AgentGraphRuntime](docs/guides/agent-runtime.md) уже принимает явные результаты без executor callback и проверяет process revision, waits и budgets. [Отчёт среза](docs/reports/2026-09-17-agent-runtime-v1.md) дополняет [исходную оценку](docs/reports/2026-09-17-agent-centric-graphify-assessment.md). Добавлен [AgentPreparation](docs/guides/agent-preparation.md): агент явно подаёт Context/Analysis/Plan/Review, primitives публикуют artifacts и доводят задачу до ready без claim. [Отчёт подготовки](docs/reports/2026-09-18-agent-preparation-v1.md). Реализован [Project Knowledge Service с Graphify adapter](docs/guides/project-knowledge.md), initial load и explicit refresh/query; [отчёт знаний](docs/reports/2026-09-18-project-knowledge-service-v1.md). Добавлен [AgentExecution/preflight и work units](docs/guides/agent-execution.md); [отчёт TASK-0016](docs/reports/2026-09-18-agent-execution-v1.md). Installed Agent skill и full execution gates ещё не реализованы; существующие runtime/preparation callbacks ниже описывают legacy API.

Проектные материалы нового подхода находятся в [`docs/`](docs/README.md). Актуальный снимок реализованного состояния — [`docs/project-status.md`](docs/project-status.md):

- [`docs/graph/`](docs/graph/) — маршрутизация запросов, состояние задач и цикл исполнения;
- [`docs/development/`](docs/development/) — подготовка и исполнение задач разработки;
- [`docs/context-knowledge/`](docs/context-knowledge/) — карта знаний проекта.

Разработка идёт поэтапно. Сейчас доступны два устанавливаемых пакета: [Onboarding](packages/onboarding/README.md) с проверяемым планом `preview/apply` и [Task Manager Service](packages/task-manager/README.md) с SQLite и локальной панелью просмотра; независимый [Artifact Repository v1](docs/guides/artifact-repository.md) поставляется в корневом пакете `orchestrator`. [Инструкция первого запуска](docs/guides/onboarding.md) проводит агента через вопросы, настройку, отдельное подтверждение установки Task Manager и проверку готовности. В корневом исходном пакете реализованы первый входной срез [Request Router → Task Creator](docs/guides/request-flow.md) и минимальный in-memory [Graph Runtime](docs/architecture/workflow-run.md); адаптеры классификации и смысловой подготовки передаются извне. Внутри Task Manager поставляются полный контракт, инструкция и пример skill; [проектный skill задач](.agents/skills/orchestrator-task-manager/SKILL.md) указывает на них. Автоматическое связывание входного потока с исполнением, многосессионность и восстановление пока не реализованы. Код из `obsolete/` не выполняет новые контракты.

Минимальный [Preparation Workflow](docs/guides/preparation-workflow.md) связывает Context → Analysis → Planning → Review → Package → Ready с реальным публичным Task Manager API и Artifact Repository. Его запускает caller с четырьмя смысловыми адаптерами; автоматического claim или исполнения нет. TASK-0015 принята пользователем и завершена (version 18), независимый аудит этой новой реализации ещё не проводился.

## Как подключить к своему проекту сейчас

Нужны Git, Python 3.11+ и доступ агента к целевому проекту. Настройка создаёт конфигурацию и контекст проекта. После неё можно вручную создавать и просматривать задачи через [Task Manager](docs/guides/tasks.md); core runtime используется программно, а автоматическое связывание входного потока с исполнением пока не запускается.

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
   orchestrator-onboarding check-task-manager --target . --python .\.venv\Scripts\python.exe
   ```

   Панель доступна на `http://127.0.0.1:8765/` только локально и только для чтения. Команды и ограничения описаны в [инструкции](docs/guides/tasks.md).

Если целевой проект — **сам этот репозиторий**, шаг 1 пропускается. В командах используйте `packages/onboarding/src/orchestrator_onboarding/onboarding.py` вместо пути через `tools/`, а для `--core` укажите `.`. Не создавайте вложенную копию оркестратора. Установленный пакет также предоставляет команду `orchestrator-onboarding` с теми же `preview/apply`.

Для self-hosting установите пакет командой `python -m pip install -e .\packages\task-manager`. Skill находится в `.agents/skills/` и доступен агенту при работе из этого репозитория. Во внешнем проекте блок в `AGENTS.md`, добавленный онбордингом, укажет агенту путь к skill внутри submodule.

Для внешнего агента подключайте MCP stdio через отдельный процесс на проект. Если MCP-хосту нужен явный фрагмент конфигурации, создайте его командой `orchestrator-onboarding mcp-config --target . --python .\.venv\Scripts\python.exe --output .tmp\task-manager-mcp.json`; глобальные настройки хоста онбординг не изменяет.

Последовательность работ описана в [`docs/roadmap.md`](docs/roadmap.md). Новая документация и гайды ведутся на русском языке.
