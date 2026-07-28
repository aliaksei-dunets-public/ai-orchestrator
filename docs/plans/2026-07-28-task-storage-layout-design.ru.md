# Разделение Task Context и checkpoint

**Дата:** 2026-07-28
**Статус:** утверждено пользователем

## Цель

Разделить версионируемые Task Context и локальные execution checkpoints по
отдельным общим каталогам, сохранив плоское именование по Task ID:

```text
.orchestrator/tasks/
├── contexts/
│   └── TASK-0001.md
├── checkpoints/
│   └── TASK-0001.checkpoint.lock
├── drafts/
└── tasks.json
```

## Контракт хранения

- `contexts/` содержит зарегистрированные Task Context и остаётся tracked в Git.
- Поле `context` в Task Registry хранит POSIX-путь
  `contexts/<TASK-ID>.md` относительно `.orchestrator/tasks/`.
- `checkpoints/` содержит operational execution state и полностью исключается
  из Git.
- Checkpoint задачи вычисляется как
  `.orchestrator/tasks/checkpoints/<TASK-ID>.checkpoint.lock`.
- Регистрация создаёт `contexts/` при необходимости и атомарно откатывает
  созданный Context при ошибке записи registry.
- Registry validation разрешает Context только внутри `contexts/` и ищет
  незарегистрированные `TASK-*.md` только в этом каталоге.

## Жизненный цикл checkpoint

Implementation Runner получает canonical checkpoint path через Task Manager и
передаёт его в `orchestrator.execution.execute_plan`. Runner не собирает путь
самостоятельно.

При успешном переходе задачи в `done` Task Manager сначала атомарно записывает
новый статус в registry, затем удаляет checkpoint. Ошибка удаления не
откатывает завершённый статус и возвращается как `cleanup_warning`. При
`cancelled` checkpoint сохраняется для диагностики.

## Миграция

Существующий `.orchestrator/tasks/TASK-0001.md` переносится в `contexts/`, а
поле `context` локального registry обновляется. Поскольку `TASK-0001` уже имеет
статус `done`, существующий checkpoint удаляется.

Onboarding обновляет managed ignore block с правила
`.orchestrator/tasks/*.lock` на
`.orchestrator/tasks/checkpoints/`. Временные atomic-write файлы registry
продолжают исключаться правилом `.orchestrator/tasks/*.tmp`.

## Проверка

- unit-тесты Task Manager покрывают новый путь Context, ограничение каталога,
  удаление checkpoint при `done`, warning при ошибке удаления и сохранение при
  `cancelled`;
- CLI-сценарий проверяет project-relative Context и ignore каталога;
- backlog-сценарий подтверждает отсутствие tracked diff после completion;
- implementation-runner и skill projection tests подтверждают единый
  checkpoint path и отсутствие drift;
- strict Health Check и проверка локальных документационных ссылок завершаются
  без ошибок.
