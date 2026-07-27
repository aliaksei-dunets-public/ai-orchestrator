# Принятые решения по roadmap

## DEC-001 — Порядок поддержки агентных платформ

**Статус:** принято.

После базовой поддержки OpenAI Codex platform adapters реализуются и валидируются в порядке:

1. Google Antigravity;
2. GitHub Copilot VS Code;
3. Claude VS Code.

Каждая платформа обязана пройти общий capability contract до начала адаптации следующей. Фаза 22 запускает acceptance matrix на Codex и всех трёх дополнительных платформах.

## DEC-002 — Межпроцессная блокировка Task Registry

**Статус:** отложено как дополнительная capability.

Первая версия рассчитана на одного разработчика и один изменяющий Task Manager process. Она сохраняет crash-safe запись через временный файл, `flush`/`fsync` и `os.replace`, но не обещает корректность конкурентных writers.

Межпроцессный lock, конкурентный `claim-next`, timeout и stale-lock recovery добавляются только после появления подтверждённой потребности и отдельного решения.

## DEC-003 — Каноническое расположение переносимых skills

**Статус:** принято.

`skills/` является каноническим source. Platform-каталоги, включая `.codex/skills/`, являются устанавливаемыми проекциями, не редактируются вручную и проверяются на drift.

Текущий `.codex/skills/task-creator` остаётся bootstrap-установкой; в фазе 5 его source переносится в `skills/task-creator`, после чего Codex-копия создаётся installer.

## DEC-004 — Хранение Task Registry вне Git

**Статус:** принято.

`.orchestrator/tasks/tasks.json`, временные файлы и будущие lock-файлы являются локальным operational state и исключаются из Git. Task Context, планы, implementation changes, тесты и документация остаются версионируемыми.

Execution Record финализируется до implementation commit; commit SHA не дублируется в Task Context, поскольку восстанавливается из Git history. После успешного commit команда `complete` меняет только незатреканный registry, поэтому lifecycle `Commit → Done` не оставляет tracked changes.

История переходов статуса в первой версии не сохраняется; отдельный event log остаётся будущей capability.

## DEC-005 — Уровень зрелости внешних platform adapters

**Статус:** принято, вариант 1.

Codex profile имеет maturity `stable`, поскольку общий contract matrix и native smoke run выполнены в наблюдаемом Codex host. Google Antigravity, GitHub Copilot VS Code и Claude VS Code имеют maturity `experimental`: их общий contract matrix проходит, но независимые native host runs ещё не выполнены.

Повышение external profile до `stable` требует одного успешного native smoke run в соответствующем vendor host. Evidence обязано фиксировать host и его версию, ОС/среду выполнения, дату, запущенную проверку и результат; contract matrix также должен оставаться в состоянии `passed`.

Принятый дизайн и стратегия проверки зафиксированы в [DEC-005 Platform Maturity Design](2026-07-28-dec-005-platform-maturity-design.md).
