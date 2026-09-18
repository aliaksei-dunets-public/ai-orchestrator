# Архитектурные основания

Пути ниже разрешаются относительно найденного корня ядра. Контракты хранятся там, а не дублируются в skill.

- `docs/architecture/workflow-builder.md`: действующий формат и границы конструктора.
- `docs/guides/workflow-builder.md`: команды и пример новой композиции.
- `docs/architecture/workflow-execution.md`, `docs/guides/workflow-execution.md`: отдельный executor, host adapters, binding/roles и runnable local fixture.
- `docs/development/07-reusable-subgraph-design-rules.md`: самостоятельный результат, caller routing, версионирование и явные эффекты.
- `docs/development/03-context-node-knowledge-map-configuration.md`: defaults по специфичности; проектный patch меняет конкретный экземпляр до наследования.
- `docs/graph/01-request-routing-and-task-architecture.md`, раздел 10: логические модельные профили независимы от skill и провайдера.
- `docs/architecture/agent-centric-orchestration.md`: агент ведёт смысловую работу, ядро проверяет явные действия.
- `docs/plans/2026-09-18-workflow-config-subgraphs-model-policy-design.md`: история согласования и будущие этапы; не использовать эскиз TOML вместо действующего формата.

В v1 root TOML уже выбирает workflow: отдельный `extends` loader не поддерживается. Overlay меняет `nodes`, `model_profiles` и `runtime`. Library defaults config применяются к экземпляру; для исполнения agent наследуется только model_profile. Tool/deterministic не наследуют модель. Capability/model adapters регистрирует доверенный host; TOML не импортирует исполняемый код.
