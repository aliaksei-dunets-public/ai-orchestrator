# Как настроить Orchestrator для проекта

**Статус:** инструкция для реализованного первого среза и одноразовый порядок полного wizard-запуска.

## Сценарий первого запуска для агента

Эта инструкция используется только во время первичной настройки проекта. После завершения постоянным skill остаётся только [Task Manager](../../.agents/skills/orchestrator-task-manager/SKILL.md); повторный onboarding выполняется по этому же документу при необходимости.

1. Изучи проект, `docs/project-status.md`, корень Git, Python 3.11+, виртуальное окружение, команды тестов, `AGENTS.md`, `.gitignore`, `.orchestrator/` и `.agents/skills/`.
2. Задавай пользователю вопросы по одному: название и назначение проекта, команды проверок, ограничения, выбранный Python-интерпретатор и режим установки Task Manager (`editable` для разработки или обычная установка).
3. Подготовь в `.tmp/` UTF-8-файл ответов с `project_name`, `summary`, `test_commands` и `constraints`. Не включай секреты, токены и длинные фрагменты кода.
4. Построй `preview`: для self-hosting используй `--target . --core .`, для внешнего проекта — `--target . --core tools/orchestrator`. Покажи пользователю diff, список файлов и полный хеш плана.
5. После отдельного подтверждения именно этого хеша выполни `apply`. При изменении проекта, ядра или версии onboarding создай новый preview.
6. После успешного `apply` отдельно покажи команду установки Task Manager и запроси отдельное подтверждение. Для разработки используй `python -m pip install -e <core>/packages/task-manager`.
7. После подтверждения проверь импорт `orchestrator_task_manager`, `orchestrator-tasks --help` и `orchestrator-tasks --project . validate`. Затем выполни `orchestrator-onboarding check-task-manager --target . --python <выбранный-интерпретатор>`: команда проверяет настоящий MCP handshake, каталог инструментов и `task_health_check`. Команда `validate` и MCP health check могут создать `.orchestrator/state/tasks.sqlite3`; этот каталог не коммить.
8. Если внешний MCP-хост требует отдельный конфигурационный фрагмент, явно сгенерируй его в `.tmp/`: `orchestrator-onboarding mcp-config --target . --python <выбранный-интерпретатор> --output .tmp/task-manager-mcp.json`. Не записывай конфигурацию автоматически в глобальные настройки Codex.
9. Проверь `.orchestrator/project.json`, `.orchestrator/project-context.md`, `git diff`, доступность Task Manager skill и выдай итоговый checklist с командой создания первой задачи и способом подключения MCP.

Постоянными артефактами первого запуска являются только `project.json`, `project-context.md`, managed-блок `AGENTS.md` и правило состояния в `.gitignore`. Не создавай автоматически Plan, runtime-снимки или другие рабочие артефакты: Graph Runtime v1 используется программно после отдельной подготовки задачи.

## Перед началом

Для внешнего проекта сначала разместите ядро в `tools/orchestrator/` как submodule или копию репозитория. Код создания общего пакета ядра и его обновления ещё не реализован. Онбординг поставляется отдельным [Python-пакетом](../../packages/onboarding/README.md), но первый запуск возможен прямо из исходного файла, без установки. Для разработки самого Orchestrator используйте корень текущего репозитория как `--target` и `--core`; ничего вкладывать внутрь него не нужно.

Агент изучает проект и создаёт файл ответов в UTF-8, например:

```json
{
  "project_name": "Мой проект",
  "summary": "Краткое назначение проекта.",
  "test_commands": ["python -m unittest discover -s tests"],
  "constraints": ["Не изменять пользовательские данные без согласования."]
}
```

Сначала покажите план. При запуске из целевого проекта:

```powershell
python tools/orchestrator/packages/onboarding/src/orchestrator_onboarding/onboarding.py preview --target . --core tools/orchestrator --answers .tmp/project-answers.json --output .tmp/onboarding-plan.json
```

Для self-hosting замените путь модуля на `packages/onboarding/src/orchestrator_onboarding/onboarding.py`, а `--core` на `.`. Файл ответов и план могут находиться в `.tmp/`, который не должен попадать в Git. Команда выводит diff и хеш плана. Убедитесь, что предлагаемые сведения верны и существующие инструкции сохранены.

После явного подтверждения именно этого хеша выполните:

```powershell
python tools/orchestrator/packages/onboarding/src/orchestrator_onboarding/onboarding.py apply --plan .tmp/onboarding-plan.json --approved-hash <ПОДТВЕРЖДЁННЫЙ_ХЕШ>
```

Для self-hosting снова используйте путь `packages/onboarding/src/orchestrator_onboarding/onboarding.py`. Если пакет установлен, обе команды можно запускать через `orchestrator-onboarding` с теми же аргументами. План содержит версию формата, версию onboarding и отпечаток ядра; после обновления пакета или изменения файлов ядра старый план будет отклонён. Если какой-либо файл изменился после preview, команда не пишет ничего: создайте новый план и покажите его пользователю. Если целевой конфигурационный файл уже существует с другим содержимым, автоматическая перезапись запрещена. При обычной ошибке записи команда восстанавливает изменённые файлы; проверьте Git diff и сообщение об ошибке.

После успешного применения следуйте шагам установки и проверки Task Manager выше. Во внешнем проекте добавленный блок `AGENTS.md` указывает агенту путь к Task Manager skill внутри `tools/orchestrator`; skill выбирает MCP stdio для внешнего агента, прямой Python API для in-process оркестратора и CLI как fallback. Core Graph Runtime v1 уже реализован, но onboarding не запускает его автоматически и не связывает его с Task Manager. Если preview сообщает о широком правиле `.orchestrator/` в `.gitignore`, согласуйте его замену на `.orchestrator/state/` и создайте новый план.
