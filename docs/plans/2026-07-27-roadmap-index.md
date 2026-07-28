# Планы реализации roadmap

Планы созданы workspace-навыком `task-creator` из канонического roadmap спецификации 0.4. Порядок выполнения задаётся зависимостями; Task Layer `T0–T9` не образует отдельный backlog.

Принятые архитектурные выборы и порядок платформ зафиксированы в [решениях пользователя](2026-07-27-decisions.md).

| Фаза | План | Зависимости |
| --- | --- | --- |
| 00 | [Архитектурная основа](2026-07-27-phase-00-architecture-foundation.md) | Нет; это корень roadmap. |
| 01 | [Каркас репозитория](2026-07-27-phase-01-repository-scaffold.md) | Фаза 0. |
| 02 | [Минимальный Health Check](2026-07-27-phase-02-minimal-health-check.md) | Фаза 1 и контракты T0. |
| 03 | [Session Reporter](2026-07-27-phase-03-session-reporter.md) | Фазы 1–2. |
| 04 | [Минимальный Task Manager](2026-07-27-phase-04-minimal-task-manager.md) | Фазы 0–2; Task Layer T0. |
| 05 | [Quick Task Creator](2026-07-27-phase-05-quick-task-creator.md) | Фаза 4. |
| 06 | [Standard и Deep Task Creator](2026-07-27-phase-06-standard-task-creator.md) | Фаза 5. |
| 07 | [Implementation Runner](2026-07-27-phase-07-implementation-runner.md) | Фазы 4 и 6. |
| 08 | [Test Design and Runner](2026-07-27-phase-08-test-design-runner.md) | Фаза 7. |
| 09 | [Task Review](2026-07-27-phase-09-task-review.md) | Фазы 7–8. |
| 10 | [Code Review](2026-07-27-phase-10-code-review.md) | Фаза 9. |
| 11 | [Security Review](2026-07-27-phase-11-security-review.md) | Фаза 10. |
| 12 | [User Review and Approval Gates](2026-07-27-phase-12-approval-gates.md) | Фазы 6 и 11. |
| 13 | [Documentation Manager](2026-07-27-phase-13-documentation-manager.md) | Фазы 7–12. |
| 14 | [Project Onboarding](2026-07-27-phase-14-project-onboarding.md) | Фазы 1–3 и 12–13. |
| 15 | [Platform Profiles](2026-07-27-phase-15-platform-profiles.md) | Фазы 2, 7 и 14. |
| 16 | [Technology Profiles](2026-07-27-phase-16-technology-profiles.md) | Фаза 15. |
| 17 | [Project Memory](2026-07-27-phase-17-project-memory.md) | Фазы 3, 11–14. |
| 18 | [Knowledge Graph](2026-07-27-phase-18-knowledge-graph.md) | Фаза 17. |
| 19 | [Backlog Loop](2026-07-27-phase-19-backlog-loop.md) | Фазы 3–13 и 17. |
| 20 | [Orchestrator Audit](2026-07-27-phase-20-orchestrator-audit.md) | Фазы 2–3, 17–19. |
| 21 | [Controlled Self-Improvement](2026-07-27-phase-21-controlled-self-improvement.md) | Фазы 12, 20. |
| 22 | [Multi-Project Validation](2026-07-27-phase-22-multi-project-validation.md) | Фазы 14–21. |
| 23 | [Stable Release 1.0](2026-07-27-phase-23-stable-release-1-0.md) | Фазы 0–22. |
| 24 | [Изоляция ядра и распределение навыков](2026-07-28-phase-24-skill-distribution.md) | Фаза 23 и [согласованный дизайн](2026-07-28-skill-distribution-design.md). |
| 25 | [Полный lifecycle памяти и графа знаний](2026-07-28-phase-25-memory-knowledge-full-lifecycle.md) | Фазы 17–19 и 24, [утверждённый дизайн](2026-07-28-memory-knowledge-full-lifecycle-design.md). |

## Общая проверка

```powershell
python .codex/skills/task-creator/scripts/validate_plan.py docs/plans/2026-07-27-phase-*.md
```
