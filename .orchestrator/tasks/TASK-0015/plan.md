# TASK-0015 — граф подготовки до ready

## Цель и границы

Связать существующие Graph Runtime, Artifact Repository и публичный Task Manager API, не добавляя вторую FSM, SQLite runtime, обязательную specification.md или автоматическое исполнение после ready.

## Работы

1. Добавить PreparationWorkflow и PreparationError, строгие envelopes внешних Context/Analysis/Planning/Review adapters. Граф объявляет все маршруты, review ограничен двумя циклами, расширение context ограничено.
2. Публиковать структурированные context/analysis/review/package artifacts и immutable plan payload. Безопасно проецировать plan в task directory без перезаписи постороннего документа.
3. Реализовать step, resume, resume_blocked и inspect; проверять wait identity до побочных эффектов. Ожидание/блокер/решение/ссылки меняются только публичным сервисом.
4. Принимать только review с точным plan hash, definition version и coverage критериев. Закрывать prep run перед mark_ready; сохранить реальный guard сервиса. Не делать claim исполнения.
5. Синхронизацию файлов/runtime/Task Manager выполнять отдельными наблюдаемыми действиями: при отказе запрещать следующий шаг, предоставлять явный synchronize/reconcile без слепого повтора конфликта.
6. Добавить интеграционные tests happy path, waits/blocker, review revision/limit, stale binding/modified plan, внешний blocker/version conflict, malformed results и сохранность пользовательского plan. Добавить русские contract/guide/report и актуализировать roadmap/project status.

## Проверки

Предметный unittest в TemporaryDirectory; root, Task Manager и Onboarding suites, compileall, diff-check и live validate. Результат TASK-0015 остаётся awaiting_acceptance до отдельного пользовательского подтверждения.
