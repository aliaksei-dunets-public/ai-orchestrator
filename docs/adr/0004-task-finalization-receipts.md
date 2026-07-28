# ADR 0004: Task Finalization receipts

- Статус: accepted
- Дата: 2026-07-28

## Контекст

Execution specifications требовали обновить документацию, граф знаний и память
до commit и `done`, но runtime Backlog Loop переходил напрямую от execution к
commit/complete. `TaskManager.complete()` проверял только status и
workspace/commit evidence. Поэтому агент или direct CLI caller мог завершить
задачу, не выполнив три заявленных gate.

## Решение

Добавляется обязательный `TaskFinalizationCoordinator`, выполняемый после
implementation/reviews/security и до commit. Он получает:

- task ID и зарегистрированный Task Context;
- completed execution checkpoint;
- normalized changed paths;
- update-or-N/A dispositions Documentation Manager;
- explicit schema-version-1 Knowledge Curator proposal;
- secret-safe memory candidates.

Coordinator валидирует все входы, применяет policy-safe knowledge/memory
изменения и создаёт versioned receipt. Receipt связан digest-ами с task ID,
context revision/baseline hash, checkpoint и changed paths. `complete` принимает
receipt только из `.orchestrator/tasks/finalization/<TASK-ID>.json`, проверяет
его hash/freshness/ready state и сохраняет digest в Task Registry.

Пустой knowledge proposal и пустой memory candidate list являются допустимыми
явными no-op. Отсутствующий proposal или documentation disposition блокирует
финализацию. Instruction и non-authoritative memory требуют hash-bound approval;
до решения coordinator возвращает `waiting_user`.

Session Reporter остаётся post-loop шагом. Он создаёт отчёт и session-sourced
proposals один раз после остановки loop, не блокирует уже установленный task
status и никогда не auto-promote non-authoritative memory.

## Последствия

- Direct API/CLI и serial/isolated backlog больше не могут пропустить
  documentation/knowledge/memory finalization.
- Existing historical `done` records остаются читаемыми, но каждый новый
  completion transition требует receipt.
- Operational receipts и derived indexes не коммитятся; canonical docs, memory
  and knowledge stores коммитятся вместе с задачей.
- Pending approval останавливает commit и сохраняет checkpoint/proposal для
  idempotent resume.
- Task Manager остаётся structural gate и не становится владельцем semantic
  content.

## Rollback

Остановить execution до commit, сохранить receipt/checkpoint и вернуть runtime,
workflow, CLI/schema и skills к предыдущей версии одним commit revert.
Canonical append-only memory не удалять: ошибочные записи disable/supersede.
Knowledge corrections выполнять новым provenance-backed proposal. Historical
registry records с finalization metadata остаются additive и могут читаться как
необязательное поле старым recovery tooling.
