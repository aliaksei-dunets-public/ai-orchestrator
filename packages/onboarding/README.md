# Onboarding

Пакет первичной настройки проекта для Orchestrator. Он формирует проверяемый план изменений и применяет его только после подтверждения хеша. В отличие от Task Manager Service, пакет связан со структурой ядра и интеграционными файлами целевого проекта; это не универсальный инструмент настройки произвольных приложений.

## Установка и запуск

При разработке из корня этого репозитория:

```powershell
python -m pip install -e .\packages\onboarding
orchestrator-onboarding --help
```

Во внешнем проекте с ядром в `tools/orchestrator/` пакет можно установить командой `python -m pip install -e .\tools\orchestrator\packages\onboarding`. Для первого запуска установка необязательна: тот же CLI доступен по пути `python tools/orchestrator/packages/onboarding/src/orchestrator_onboarding/onboarding.py`.

## Протокол

Агент сначала изучает проект и готовит UTF-8 JSON с `project_name`, `summary`, списками `test_commands` и `constraints`. Затем из корня целевого проекта:

```powershell
orchestrator-onboarding preview --target . --core tools/orchestrator --answers .tmp/project-answers.json --output .tmp/onboarding-plan.json
orchestrator-onboarding apply --plan .tmp/onboarding-plan.json --approved-hash <ПОДТВЕРЖДЁННЫЙ_ХЕШ>
```

Между командами пользователь проверяет показанный diff и подтверждает именно его хеш. План также фиксирует версию onboarding и отпечаток содержимого ядра; `apply` отклоняет план другой версии или после изменения ядра. `apply` повторно сверяет хеш и текущее содержимое затрагиваемых файлов, пишет только управляемые файлы и блоки, проверяет результат и при ошибке восстанавливает записанные файлы. При изменении проекта после preview составьте новый план. Не применяйте старый план после обновления пакета или изменения смысловых ответов.

Для self-hosting ядро и проект совпадают: укажите `--target . --core .`. Пакет не создаёт вторую копию ядра и не меняет существующий `AGENTS.md` в этом режиме. Полный wizard-порядок описан в [инструкции первого запуска](../../docs/guides/onboarding.md); пакет не устанавливает Task Manager автоматически.

Публичный Python API: `from orchestrator_onboarding import build_plan, apply_plan, OnboardingError`. Действующие ограничения и владельцы файлов описаны в [контракте](../../docs/architecture/onboarding.md), а пример ответов — в [гайде](../../docs/guides/onboarding.md).

## Проверка при разработке

```powershell
python -m unittest discover -s packages/onboarding/tests -v
```
