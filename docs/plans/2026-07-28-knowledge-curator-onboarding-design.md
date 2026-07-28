# Интеграция Knowledge Curator в Project Onboarding

## Решение

Существующий bundled skill `knowledge-curator` становится владельцем полного
lifecycle Knowledge Graph: первичная инвентаризация, подготовка proposal,
валидация, запись canonical nodes/edges, rebuild индексов и последующее
сопровождение. Отдельный дублирующий `knowledge-onboarding` skill не создаётся.

`project-onboarding` остаётся владельцем bootstrap target project и вызывает
knowledge-curation как фазу подготовки preview. Агент передаёт в onboarding
проверяемый `knowledge_graph` proposal с nodes и edges. Onboarding не принимает
его на доверии: core валидирует ontology, provenance, существование effective
endpoint nodes, конфликты и supersede cycles, затем включает итоговое содержимое
canonical JSONL в общий `plan_hash`.

До approval пользователя target project не изменяется. После approval `apply`
атомарно записывает обычные onboarding files и graph stores через тот же backup,
rollback и validation workflow. Derived indexes перестраиваются из canonical
stores и остаются ignored operational state.

## Границы

- Graph является navigation layer; source documents остаются canonical truth.
- Автоматический свободный crawl всего проекта не вводится.
- Proposal может быть пустым: onboarding создаёт пустые stores без ложных знаний.
- Source paths только project-relative; `.git`, secrets, credentials, `.env` и
  releases запрещены.
- Core ontology immutable; project ontology только additive.
- Существующие CLI и Python APIs сохраняют backward compatibility.

## Поток данных

```text
project-onboarding inspect
→ project-onboarding plan
→ knowledge-curator source inventory
→ knowledge_graph proposal
→ validate and merge with existing canonical graph
→ preview and plan_hash
→ explicit user approval
→ atomic apply
→ effective_graph validation
→ deterministic index rebuild
→ Health Check and report
```

## Контракт proposal

```json
{
  "schema_version": 1,
  "nodes": [
    {
      "id": "reports-api",
      "kind": "component",
      "label": "Reports API",
      "source": "docs/specifications/api-contract.md",
      "supersedes": null,
      "enabled": true
    }
  ],
  "edges": [
    {
      "id": "reports-api-depends-on-auth",
      "source_node": "reports-api",
      "target_node": "authorization-service",
      "relation": "depends_on",
      "source": "docs/adr/0010-api-authorization.md",
      "enabled": true
    }
  ]
}
```

`source_digest` не принимается от агента как authoritative input: core вычисляет
его из фактического файла. Existing identical IDs остаются idempotent; differing
payloads отклоняются как conflict.

## Проверки

Proposal должен проходить schema validation, ontology validation, source
authority, duplicate/conflict, supersede cycle, effective endpoint и deterministic
JSONL checks. Tests покрывают direct graph preparation, onboarding preview/apply,
stale plan, rollback, idempotency, secrets/excluded sources и index rebuild.
