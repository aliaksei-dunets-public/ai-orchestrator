# Как настроить Orchestrator для проекта

**Статус:** инструкция для реализованного первого среза (только настройка проекта).

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

Для self-hosting снова используйте путь `packages/onboarding/src/orchestrator_onboarding/onboarding.py`. Если пакет установлен, обе команды можно запускать через `orchestrator-onboarding` с теми же аргументами. Если какой-либо файл изменился после preview, команда не пишет ничего: создайте новый план и покажите его пользователю. Если целевой конфигурационный файл уже существует с другим содержимым, автоматическая перезапись запрещена. При обычной ошибке записи команда восстанавливает изменённые файлы; проверьте Git diff и сообщение об ошибке.

После успешного применения проверьте `.orchestrator/project.json`, `.orchestrator/project-context.md` и `git diff`. Затем [установите отдельный пакет Task Manager Service](tasks.md) для ручного создания и просмотра задач. Во внешнем проекте добавленный блок `AGENTS.md` указывает агенту путь к skill внутри `tools/orchestrator`. Graph Runtime и автоматическая обработка задач ещё не реализованы. Если preview сообщает о широком правиле `.orchestrator/` в `.gitignore`, согласуйте его замену на `.orchestrator/state/` и создайте новый план.
