# Полный lifecycle памяти и графа знаний

**Дата:** 2026-07-28
**Статус:** утверждено пользователем
**Связанные фазы:** 17, 18, 19, 24 и новая фаза 25

## Контекст и цель

Текущие `orchestrator.memory` и `orchestrator.knowledge` реализуют минимальные
append-only primitives, provenance checks, supersede и детерминированную сборку
индекса. Они не владеют project-relative storage layout, не подключены к
onboarding, Task Creation, Task Execution, Session Report, CLI и Health Check,
а target project не получает memory/knowledge stores.

Цель фазы 25 — завершить lifecycle без превращения графа во второй источник
истины. Исходные спецификации, ADR, Task Context, review results и другие
подтверждённые документы остаются каноническими. Память хранит компактные
утверждения с provenance, а граф даёт структурированную навигацию между
документами, компонентами, контрактами, решениями, задачами и рисками.

Реализация сохраняет platform-neutral Core и Python 3.11 standard library.
Существующие schema-version-1 записи и публичные функции остаются читаемыми и
доступными через compatibility adapters. Новые project-store контракты
добавляются в выпуске 1.2 с previewed migration и восстановлением из резервной
копии.

## Владение данными и layout

Каждый target project владеет своими данными:

```text
.orchestrator/
├── memory/
│   ├── entries.jsonl            # tracked canonical entries
│   ├── events.jsonl             # tracked disable/supersede lifecycle
│   ├── approvals/               # tracked approval provenance
│   └── proposals/               # ignored operational candidates
└── knowledge/
    ├── ontology.json            # tracked additive project ontology
    ├── nodes.jsonl              # tracked canonical nodes
    ├── edges.jsonl              # tracked canonical edges
    └── indexes/                 # ignored reproducible indexes
```

Core поставляет runtime, schemas и неизменяемую базовую ontology. Он не хранит
данные нескольких проектов. Репозиторий AI Orchestrator использует тот же
target-owned layout для памяти о собственном развитии.

Logical append-only обеспечивается атомарной публикацией новой версии JSONL
через temporary file, `flush`/`fsync` и `os.replace`. Плохая запись не
удаляется и не меняется на месте: effective state вычисляется из canonical
entry и последующих lifecycle events. Один modifying process остаётся
поддерживаемой моделью; interprocess locking не входит в эту фазу.

## Promotion и source authority

Agent формирует proposal после task execution или Session Report. Proposal
связывает kind, content, project-relative source, source digest, confidence,
supersedes и deterministic proposal hash. До promotion proposal находится в
ignored operational storage.

Без отдельного user approval разрешено продвигать observation, lesson или
decision только из детерминированно распознанного authoritative source:

- canonical specification;
- ADR со статусом `accepted`;
- completed Task Context с финальным Execution Record;
- review result с verdict `approved`.

Диалог, Session Report, неподтверждённый документ и неизвестный source требуют
approval, привязанного к proposal hash и source digest. Для них создаётся
неизменяемый tracked approval record, который становится долговечным
provenance. `instruction` всегда требует explicit approval независимо от
source authority. Secret-like content, stale source, duplicate, конфликт ID
или несуществующий supersede блокируют persistence.

## Ontology и граф

Core ontology содержит неизменяемые node kinds:
`document`, `component`, `contract`, `decision`, `task`, `risk`.

Core relations:
`defined_by`, `depends_on`, `implements`, `affects`, `supersedes`,
`produced_by`.

Target project может только добавлять kinds и relations через
`.orchestrator/knowledge/ontology.json`. Переопределение core ID, конфликт
project definitions или использование незарегистрированного типа блокируются.
Изменение уже опубликованной семантики требует новой schema revision и
migration.

Nodes и edges имеют project-relative provenance. Edge обязан ссылаться на
effective nodes. Replacement использует explicit supersede; silent overwrite
запрещён. Derived indexes строятся только из canonical ontology, nodes и edges,
содержат lookup по kind, relation, source, incoming и outgoing adjacency и
должны воспроизводиться byte-for-byte.

## Retrieval и context pack

Retrieval не использует embeddings, внешнюю БД или network service. Запрос
строится из Task Context, затронутых путей, компонентов и явных терминов.
Детерминированный pipeline:

1. нормализует и case-folds термины;
2. выбирает active memory entries по kind, source/path и lexical overlap;
3. выбирает graph nodes по ID, label, kind и source;
4. расширяет graph neighborhood по разрешённым relations на bounded depth;
5. стабильно сортирует результат по score и ID;
6. обрезает результат по лимитам entries, nodes, edges и characters.

Context pack содержит query digest, canonical-store digest, выбранные IDs,
краткое содержание, provenance и freshness state. Disabled, superseded,
stale, secret-like и невалидные записи не попадают в pack. Одинаковые stores,
query и limits дают byte-for-byte одинаковый JSON.

Каждый Task Creation route получает pack до repository analysis; для quick
route пустой или нерелевантный pack остаётся дешёвым no-op. Task Execution
повторяет retrieval после freshness gate, чтобы не использовать устаревший
контекст. Audit может читать тот же pack, но retrieval никогда не меняет
canonical stores.

## Target onboarding, CLI и Health Check

Onboarding preview включает новые tracked stores, additive ontology,
project-config sections и Git-ignore rules для proposals/indexes. Apply
сохраняет user-owned data, не обнуляет существующие JSONL и остаётся
идемпотентным. Post-apply validation проверяет stores и rebuild indexes.
Репозиторий AI Orchestrator инициализирует тот же layout как self-hosted target,
чтобы разработка Core проходила через те же контракты, что и внешний проект.

CLI расширяется JSON-first командами:

- `orchestrator memory propose|promote|disable|list|validate|migrate`;
- `orchestrator knowledge add-node|add-edge|rebuild|query|validate`;
- `orchestrator context build`.

Health Check проверяет schemas, path containment, source existence/digest,
duplicate IDs, lifecycle references/cycles, ontology conflicts, edge
referential integrity, index freshness и Git policy. Canonical stores не
должны быть ignored; proposals и indexes должны быть ignored.

Ошибки CLI возвращаются без traceback с устойчивыми exit codes. Миграция
сначала строит preview и backup, затем применяет утверждённый plan hash.
Rollback восстанавливает исходные stores и config.

## Security, тестирование и исключённый scope

До любой записи выполняются path containment, ignored-tree rejection и
secret scan. Retrieval не читает `.env`, credentials, ignored operational
trees и release snapshots. Approval hash исключает применение решения к
изменившемуся proposal или source.

Acceptance включает unit, contract, scenario, multi-project и release tests,
детерминированный double rebuild/retrieval, migration/rollback, CLI, workflow
routing, Health Check и strict full-suite validation.

В фазу не входят embeddings, vector database, network synchronization,
multi-writer locking, cross-project shared memory, автоматическая генерация
instructions, UI и произвольный natural-language query service.
