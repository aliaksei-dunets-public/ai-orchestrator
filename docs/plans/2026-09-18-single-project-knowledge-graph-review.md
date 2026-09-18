# Self-review TASK-0031

**Статус:** self-review подготовки, не независимый аудит; `codex-self-review`, 2026-09-18.

План `TASK-0031/plan.md` SHA-256: `1ea06996114a13d17fa9960ad8974e09d9b798597323be73417cdc8943e3d212`. Проверены все пять acceptance criteria текущей карточки и ограничения: один Graphify graph/index/pointer; durable code+docs corpus; явное исключение `docs/plans`, `docs/reports`, `.orchestrator` и `obsolete`; no Task Manager/schema change; provider failure fallback.

План executable without hidden controller: WU-1 defines policy/snapshot, WU-2 provider/service, WU-3 docs/refresh/evidence. Work unit scopes are project-relative and dependencies form a DAG. Semantic document extraction is delegated to pinned Graphify provider; custom parser and second graph are out of scope. Mixed provider tests use deterministic fake provider; real mixed Graphify evidence is required when a backend/API is explicitly configured. Without credentials, refresh must fail closed and keep the old pointer, not silently claim a complete graph.

Findings: current TASK-0030 graph is code-only and must be treated as migration input; current Graphify upstream requires semantic backend for Markdown; default project snapshot must not include operational docs. These are addressed by `project-knowledge/v2`, legacy pointer compatibility, `include_documents` provider flag, durable allow-list and deny-list tests. Review approves proceeding to ready after immutable plan/review/package publication. Full workflow integration, incremental refresh, memory and portable delivery remain later tasks.

```json
{"findings":[],"criterion_ids":["AC-01","AC-02","AC-03","AC-04","AC-05"],"zero_context_executable":true,"approved_binding":{"plan_sha256":"1ea06996114a13d17fa9960ad8974e09d9b798597323be73417cdc8943e3d212","definition_version":1}}
```
