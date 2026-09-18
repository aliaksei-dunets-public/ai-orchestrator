# Реестр проектных материалов

**Статус:** навигационный реестр, не доказательство реализации. С 2026-09-17 приоритет направления задают агент-центричная оркестрация и Project Knowledge Service с Graphify.

- [Разбор аудита Graph Runtime и объём TASK-0034](reports/2026-09-18-graph-runtime-audit-triage.md).
- [Уточнённый объём TASK-0034: удаление callback GraphRuntime](plans/2026-09-18-remove-callback-runtime-scope.md).
- [TASK-0034: выполненное удаление и результаты проверок](reports/2026-09-18-task-0034-callback-removal.md).
- [TASK-0034: данные измерений AgentGraphRuntime](reports/2026-09-18-task-0034-runtime-measurements.json).
- [Повторный аудит Agent Runtime: оценка замечаний](reports/2026-09-18-agent-runtime-audit-followup-triage.md).
- [Повторный аудит Agent Runtime: результаты воспроизведений](reports/2026-09-18-agent-runtime-audit-followup-evidence.json).
- [TASK-0035: дизайн исправлений повторного аудита](plans/2026-09-18-agent-runtime-audit-fixes-design.md).
- [TASK-0035: реализация, проверки и критерии](reports/2026-09-18-task-0035-agent-runtime-audit-fixes.md).
- [Обзорный граф Orchestrator](architecture/orchestrator-graph-overview.md).
- [Предложение: конфигурация workflow, подграфы и модели узлов](plans/2026-09-18-workflow-config-subgraphs-model-policy-design.md).
- [Конструктор workflow v1 — реализованный контракт](architecture/workflow-builder.md).
- [Guide: сборка процессов с агентом](guides/workflow-builder.md).
- [TASK-0036: результат и проверки конструктора](reports/2026-09-18-task-0036-workflow-builder-v1.md).
- [TASK-0037: дизайн explicit исполнения](plans/2026-09-18-workflow-execution-design.md).
- [Исполнение workflow — контракт](architecture/workflow-execution.md).
- [Guide: модели, артефакты и роли](guides/workflow-execution.md).
- [TASK-0037: результаты и границы](reports/2026-09-18-task-0037-workflow-execution.md).

- [Агент-центричная оркестрация](architecture/agent-centric-orchestration.md).
- [Project Knowledge Service](architecture/project-knowledge-service.md).
- [Проект миграции](plans/2026-09-17-agent-centric-graphify-migration-design.md).
- [Архитектурная оценка и baseline](reports/2026-09-17-agent-centric-graphify-assessment.md).
- [Реализованный AgentGraphRuntime](architecture/agent-runtime-contract.md).
- [Гайд Agent Runtime](guides/agent-runtime.md).
- [Отчёт TASK-0028](reports/2026-09-17-agent-runtime-v1.md).
- [Агентная подготовка — контракт](architecture/agent-preparation.md).
- [Агентная подготовка — guide](guides/agent-preparation.md).
- [Отчёт TASK-0029](reports/2026-09-18-agent-preparation-v1.md).
- [Self-review плана TASK-0029](plans/2026-09-18-agent-preparation-plan-review.md).
- [Реальный upstream Graphify probe](reports/2026-09-18-graphify-upstream-probe.md).
- [Guide знаний проекта](guides/project-knowledge.md).
- [Host-agent Graphify: подтверждённый дизайн TASK-0031](plans/2026-09-18-graphify-host-agent-design.md).
- [Единый код/документы граф: PoC TASK-0031](reports/2026-09-18-single-project-knowledge-graph-v1.md).
- [Реализованный Knowledge Service: отчёт TASK-0030](reports/2026-09-18-project-knowledge-service-v1.md).
- [Incremental Refresh TASK-0020: plan/review](plans/2026-09-18-task-0020-incremental-refresh-review.md).
- [Incremental Refresh TASK-0020: результаты v1](reports/2026-09-18-task-0020-incremental-refresh-v1.md).
- [KnowledgeRefreshNode: согласованный дизайн TASK-0033](plans/2026-09-18-knowledge-refresh-node-design.md).
- [KnowledgeRefreshNode TASK-0033: результаты v1](reports/2026-09-18-task-0033-knowledge-refresh-node-v1.md).
- [Self-review плана TASK-0030](plans/2026-09-18-knowledge-service-plan-review.md).
- [Агентское исполнение — контракт](architecture/agent-execution.md).
- [Агентское исполнение — guide](guides/agent-execution.md).
- [Отчёт TASK-0016](reports/2026-09-18-agent-execution-v1.md).
- [Self-review плана TASK-0016](plans/2026-09-18-agent-execution-plan-review.md).

Backlog развития v1 добавлен 2026-09-16 в `plans/2026-09-16-orchestrator-roadmap-backlog-design.md`.

## Сохранённые исходные материалы

- `plans/2026-09-16-orchestrator-roadmap-backlog-design.md`

- `context-knowledge/00-project-knowledge-map-master-spec.md`
- `context-knowledge/10-semantic-layer-architecture.md`
- `context-knowledge/11-semantic-knowledge-contract.md`
- `context-knowledge/12-knowledge-refresh-subgraph.md`
- `context-knowledge/13-knowledge-refresh-contract.md`
- `context-knowledge/14-knowledge-health-audit-subgraph.md`
- `context-knowledge/15-knowledge-health-audit-contracts.md`
- `context-knowledge/16-knowledge-health-policy.md`
- `context-knowledge/17-pkm-architecture-audit.md`
- `context-knowledge/18-pkm-audit-remediation-roadmap.md`
- `development/03-context-node-knowledge-map-configuration.md`
- `development/04-development-context-node-patch.md`
- `development/05-analysis-subgraph-architecture.md`
- `development/06-implementation-analysis-contract.md`
- `development/07-reusable-subgraph-design-rules.md`
- `development/08-planning-subgraph-architecture.md`
- `development/09-implementation-plan-contract.md`
- `development/10-development-workflow-planning-patch.md`
- `development/11-plan-review-gate-architecture.md`
- `development/12-plan-review-contract.md`
- `development/13-plan-review-policy.md`
- `development/14-implementation-subgraph-architecture.md`
- `development/15-implementation-work-unit-contract.md`
- `development/16-implementation-execution-policy.md`
- `development/17-implementation-v1-single-agent-patch.md`
- `development/18-code-review-gate-architecture.md`
- `development/19-code-review-contract.md`
- `development/20-code-review-policy.md`
- `development/21-tdd-integration-architecture.md`
- `development/22-testing-subgraph-architecture.md`
- `development/23-testing-contract.md`
- `development/24-development-tdd-policy.md`
- `development/25-documentation-subgraph-architecture.md`
- `development/26-documentation-contract.md`
- `development/27-documentation-policy.md`
- `development/28-development-workflow-documentation-patch.md`
- `development/29-final-validation-gate-architecture.md`
- `development/30-final-validation-contract.md`
- `development/31-final-validation-policy.md`
- `development/32-development-workflow-final-check-patch.md`
- `development/33-development-preparation-execution-boundary.md`
- `development/34-execution-preflight-contract.md`
- `development/35-development-specification-contract.md`
- `development/36-preparation-artifact-lifecycle-policy.md`
- `development/37-superpowers-principles-adoption.md`
- `development/38-execution-workspace-strategy.md`
- `development/39-execution-workspace-policy.md`
- `graph/01-request-routing-and-task-architecture.md`
- `graph/02-request-routing-graph-template.md`
- `graph/03-task-manager-service-architecture.md`
- `graph/04-task-manager-service-contract.md`
- `graph/05-task-tracker-adapter-architecture.md`
- `graph/06-task-tracker-adapter-contract.md`
- `graph/07-task-management-integration-patch.md`
- `graph/08-task-readiness-and-execution-package.md`
- `graph/09-task-executor-loop-architecture.md`
