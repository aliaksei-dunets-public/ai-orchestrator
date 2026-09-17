# Усиление интеграции Task Manager MCP и onboarding

**Статус:** реализовано и проверено; пользовательская приёмка TASK-0026 ещё впереди.

## Причина изменений

Аудит показал, что MCP уже был реализован, но проектный skill продолжал направлять внешнего агента в CLI, а onboarding проверял только наличие skill и CLI. В результате MCP мог быть установлен, но его доступность, stdio handshake и выбор Python-окружения не проверялись.

## Изменения

- Skill Task Manager теперь явно выбирает MCP stdio для внешнего агента, прямой `TaskManagerService` для Python-оркестратора и CLI как fallback.
- В skill добавлены правила `initialize`/`tools/list`, фиксированного `project_root`, обязательного `expected_version`, `operation_id` и обработки структурированных ошибок.
- Onboarding preview проверяет не только skill, но и MCP entry point `orchestrator-task-manager-mcp` в подключённом ядре.
- Добавлена read-only команда `orchestrator-onboarding check-task-manager`. Она запускает реальный MCP subprocess, выполняет `initialize`, `tools/list` и `task_health_check` выбранным Python-интерпретатором.
- Добавлена команда `orchestrator-onboarding mcp-config`. Она по явному вызову создаёт только внутри проекта host-neutral JSON-фрагмент с абсолютным Python и фиксированным корнем. Глобальная конфигурация Codex или другого MCP-хоста не меняется.
- MCP stdio теперь перенастраивает и вход, и выход в UTF-8 до чтения сообщений. Это устраняет ошибки Unicode на Windows при русских запросах и при `--help` в legacy code page.

## Архитектурное решение

Новый MCP-сервер или отдельная реализация на каждый проект не создаются. Пакет и код общие; отдельными остаются только MCP-процесс, `project_root` и база проекта. Onboarding не пытается автоматически редактировать глобальные настройки хоста, потому что их формат и область действия зависят от конкретного MCP-клиента.

## Проверки

- Onboarding: 19 тестов, 18 прошли, 1 пропущен из-за ограничения Windows на symlink.
- Task Manager: 66 тестов прошли.
- Проверен реальный onboarding MCP handshake с `initialize`, `tools/list` и `task_health_check`.
- Проверена генерация конфига с выбранным Python и отказ вывода за пределы проекта.
- Добавлен регрессионный тест UTF-8 `--help` MCP при `PYTHONIOENCODING=cp1252`.
- Добавлена проверка Unicode-ввода через MCP при перезапуске процесса.

## Использование

```powershell
orchestrator-onboarding check-task-manager --target . --python .\.venv\Scripts\python.exe
orchestrator-onboarding mcp-config --target . --python .\.venv\Scripts\python.exe --output .tmp\task-manager-mcp.json
```

Полученный JSON-фрагмент передаётся MCP-хосту вручную. Онбординг не выполняет регистрацию автоматически.
