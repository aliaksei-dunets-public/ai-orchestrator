# Как настроить Graph Orchestrator для проекта

**Статус:** инструкция для реализованного первого среза (только настройка проекта).

## Перед началом

Для внешнего проекта сначала разместите ядро в `tools/graph-orchestrator/` как submodule или копию подготовленного пакета. Код создания пакета и его обновления ещё не реализован. Для разработки самого Graph Orchestrator используйте корень текущего репозитория как `--target` и `--core`; ничего вкладывать внутрь него не нужно.

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
python tools/graph-orchestrator/graph_orchestrator/onboarding.py preview --target . --core tools/graph-orchestrator --answers .tmp/project-answers.json --output .tmp/onboarding-plan.json
```

Для self-hosting замените путь модуля на `graph_orchestrator/onboarding.py`, а `--core` на `.`. Файл ответов и план могут находиться в `.tmp/`, который не должен попадать в Git. Команда выводит diff и хеш плана. Убедитесь, что предлагаемые сведения верны и существующие инструкции сохранены.

После явного подтверждения именно этого хеша выполните:

```powershell
python tools/graph-orchestrator/graph_orchestrator/onboarding.py apply --plan .tmp/onboarding-plan.json --approved-hash <ПОДТВЕРЖДЁННЫЙ_ХЕШ>
```

Для self-hosting снова используйте `graph_orchestrator/onboarding.py`. Если какой-либо файл изменился после preview, команда не пишет ничего: создайте новый план и покажите его пользователю. Если целевой конфигурационный файл уже существует с другим содержимым, автоматическая перезапись запрещена. При обычной ошибке записи команда восстанавливает изменённые файлы; проверьте Git diff и сообщение об ошибке.

После успешного применения проверьте `.graph-orchestrator/project.json`, `.graph-orchestrator/project-context.md` и `git diff`. Это лишь настройка проекта: Graph Runtime, Task Manager Service и обработка задач ещё не реализованы.
