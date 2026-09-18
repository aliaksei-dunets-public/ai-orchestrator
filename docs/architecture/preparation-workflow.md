# Подготовка задачи: действующий агентский путь

**Статус:** навигация и граница миграции TASK-0034, 2026-09-18. Callback PreparationWorkflow и `orchestrator.preparation_workflow` удалены; единственный поддерживаемый facade подготовки — [AgentPreparation](agent-preparation.md).

Историческая TASK-0015 реализовала Context → Analysis → Planning → Review → Package → Ready через callbacks. Её [отчёт](../reports/2026-09-17-preparation-workflow.md) сохраняет факты на дату приёмки, но не обещает поддержку старого API сейчас.

Агент явно выполняет Context/Analysis/Planning/Review и подаёт envelopes. Deterministic PreparationPrimitives проверяют формы, constraints/invariants, зависимости work units и review binding; публикуют immutable artifacts и защищённую plan projection. TaskEffectSync хранит pending/unknown cursor в памяти и сверяет публичную историю Task Manager при неизвестном эффекте. Package/Ready gates проверяют настоящие артефакты; ready не делает claim.

Task Manager остаётся каноническим владельцем задачи и lifecycle, ArtifactRepository — тел payload, AgentGraphRuntime — текущего узла/results/waits/history. Нет общей транзакции, automatic retry или restart recovery. Эквивалентность структурных контрактов не доказывает качество semantic review.

Действующие [контракт AgentPreparation](agent-preparation.md), [guide](../guides/agent-preparation.md), [миграция](../guides/preparation-workflow.md), [предметные tests](../../tests/test_agent_preparation.py).
