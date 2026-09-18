# Review плана AgentGraphRuntime

**Статус:** самостоятельный предметный review плана TASK-0028 до реализации, 2026-09-17. Не независимый аудит кода и не пользовательская приёмка.

Проверен [план TASK-0028](../../.orchestrator/tasks/TASK-0028/plan.md) по подтверждённому [дизайну миграции](2026-09-17-agent-centric-graphify-migration-design.md), существующим Graph/Node/Result контрактам и unchanged Task Manager границе.

## Результат: approved

- Новый runtime принимает готовые результаты, не запускает reasoning callbacks. Это сервис процесса, не второй оркестратор.
- Для одного нового run есть один canonical in-memory снимок; legacy runtime сохраняется отдельно для legacy runs.
- Task version и process revision разделены. Актуальность внешнего task definition обеспечивает caller через публичный API; runtime не обещает автоматической проверки базы.
- Валидация результата, лимитов и JSON выполняется до публикации. Lock внутри процесса обеспечивает compare-and-publish; tests проверяют duplicate/concurrent submission и неизменность rejected snapshot.
- Generic process success не приравнивается к ready/active/completed задачи. Integration tests должны это показать через реальный публичный Task Manager.
- Wait resume не запускает работу. Evidence будущего решения принадлежит последующему NodeResult; факт пользовательского ответа не должен теряться при ошибке выполнения узла.
- Общая validation функция не ужесточает legacy требования. Старые подписи и сериализация WorkflowRun сохраняются.
- Критерии покрыты work units 1–4, командами проверок и контрактом/guide. Graphify/persistence/agent skills явно вне среза, поэтому их отсутствие не выдается за готовность.

Открытых major/critical замечаний к плану нет. Отдельная независимая code review и проверка реального внешнего агента не выполнены и не заявляются.
