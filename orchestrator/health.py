from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}


@dataclass(frozen=True, order=True)
class Finding:
    code: str
    severity: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return asdict(self)


@dataclass(frozen=True)
class HealthReport:
    findings: tuple[Finding, ...]

    @property
    def highest_severity(self) -> str:
        if not self.findings:
            return "INFO"
        return max(self.findings, key=lambda item: SEVERITY_ORDER[item.severity]).severity

    @property
    def ok(self) -> bool:
        return SEVERITY_ORDER[self.highest_severity] < SEVERITY_ORDER["ERROR"]

    def exit_code(self, *, strict: bool = False) -> int:
        threshold = "WARNING" if strict else "ERROR"
        return int(any(SEVERITY_ORDER[item.severity] >= SEVERITY_ORDER[threshold] for item in self.findings))

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "highest_severity": self.highest_severity,
            "findings": [item.to_dict() for item in self.findings],
        }


def _finding(code: str, severity: str, message: str, path: Path | None = None) -> Finding:
    return Finding(code=code, severity=severity, message=message, path=path.as_posix() if path else None)


def _required_structure(root: Path) -> Iterable[Finding]:
    required = (
        "README.md",
        "AGENTS.md",
        "pyproject.toml",
        "orchestrator",
        "config/schemas",
        "registries",
        "skills",
        "docs/INDEX.md",
        "docs/documentation-policy.md",
        "docs/architecture/orchestrator-core.md",
        "docs/architecture/task-layer.md",
        "docs/roadmap.md",
    )
    for relative in required:
        path = root / relative
        if not path.exists():
            yield _finding("MISSING_REQUIRED_PATH", "ERROR", f"Required path is missing: {relative}", path)


def _load_json(path: Path) -> tuple[object | None, Finding | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, _finding("MISSING_JSON", "ERROR", "Required JSON file is missing", path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, _finding("INVALID_JSON", "ERROR", f"Cannot read JSON: {exc}", path)


def _registry_checks(root: Path) -> Iterable[Finding]:
    for path in sorted((root / "registries").glob("*.json")):
        payload, error = _load_json(path)
        if error:
            yield error
            continue
        if not isinstance(payload, dict) or payload.get("schema_version") != 1:
            yield _finding("INVALID_REGISTRY", "ERROR", "Registry must contain schema_version=1", path)
            continue
        entries = payload.get("entries")
        if not isinstance(entries, list):
            yield _finding("INVALID_REGISTRY", "ERROR", "Registry entries must be an array", path)
            continue
        seen: set[str] = set()
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                yield _finding("INVALID_REGISTRY_ENTRY", "ERROR", f"Entry {index} must be an object", path)
                continue
            entry_id = entry.get("id")
            relative = entry.get("path")
            if not isinstance(entry_id, str) or not entry_id:
                yield _finding("INVALID_REGISTRY_ENTRY", "ERROR", f"Entry {index} has no id", path)
            elif entry_id in seen:
                yield _finding("DUPLICATE_REGISTRY_ID", "ERROR", f"Duplicate id: {entry_id}", path)
            else:
                seen.add(entry_id)
            if not isinstance(relative, str) or not relative:
                yield _finding("INVALID_REGISTRY_ENTRY", "ERROR", f"Entry {index} has no path", path)
                continue
            target = (root / relative).resolve()
            try:
                target.relative_to(root.resolve())
            except ValueError:
                yield _finding("UNSAFE_REGISTRY_PATH", "CRITICAL", f"Path escapes repository: {relative}", path)
                continue
            if not target.exists():
                yield _finding("BROKEN_REGISTRY_REFERENCE", "ERROR", f"Referenced path does not exist: {relative}", target)


def _schema_checks(root: Path) -> Iterable[Finding]:
    for path in sorted((root / "config" / "schemas").glob("*.json")):
        payload, error = _load_json(path)
        if error:
            yield error
        elif not isinstance(payload, dict) or payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            yield _finding("INVALID_SCHEMA", "ERROR", "Schema must use JSON Schema draft 2020-12", path)


def _skill_projection_checks(root: Path) -> Iterable[Finding]:
    installed_root = root / ".codex" / "skills"
    if not installed_root.exists():
        return
    try:
        from .skill_installer import check_skill_drift, resolve_skill_sources

        sources = resolve_skill_sources(root, project_root=root)
        installed_ids = {
            path.name
            for path in installed_root.iterdir()
            if path.is_dir()
        }
        extra = sorted(installed_ids - set(sources))
        if extra:
            yield _finding(
                "SKILL_PROJECTION_EXTRA",
                "ERROR",
                f"Workspace projection contains unselected skills: {extra}",
                installed_root,
            )
        for skill_id, source in sources.items():
            installed = installed_root / skill_id
            drift = check_skill_drift(source, installed)
            if drift.clean:
                continue
            details = []
            if drift.missing:
                details.append(f"missing={list(drift.missing)}")
            if drift.extra:
                details.append(f"extra={list(drift.extra)}")
            if drift.changed:
                details.append(f"changed={list(drift.changed)}")
            yield _finding(
                "SKILL_PROJECTION_DRIFT",
                "ERROR",
                f"Workspace skill {skill_id} differs from canonical source: {', '.join(details)}",
                installed,
            )
    except ValueError as exc:
        yield _finding(
            "SKILL_SELECTION_INVALID",
            "ERROR",
            f"Skill selection is invalid: {exc}",
            root / ".orchestrator" / "skills.json",
        )
    except Exception as exc:  # defensive boundary: health must remain diagnostic
        yield _finding(
            "SKILL_PROJECTION_CHECK_FAILED",
            "ERROR",
            f"Workspace skill projection check failed: {exc}",
            installed_root,
        )


def _task_checks(root: Path) -> Iterable[Finding]:
    registry = root / ".orchestrator" / "tasks" / "tasks.json"
    if not registry.exists():
        yield _finding("TASK_REGISTRY_NOT_INITIALIZED", "INFO", "Task Registry is not initialized", registry)
        return
    try:
        from .task_manager import validate_registry

        for issue in validate_registry(registry.parent):
            yield _finding(issue.code, issue.severity, issue.message, issue.path)
    except Exception as exc:  # defensive boundary: health must never expose a traceback
        yield _finding("TASK_REGISTRY_CHECK_FAILED", "ERROR", f"Task Registry check failed: {exc}", registry)


def _task_workspace_checks(root: Path) -> Iterable[Finding]:
    tasks_root = root / ".orchestrator" / "tasks"
    registry = tasks_root / "tasks.json"
    if not registry.is_file():
        return
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
        tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
        if not isinstance(tasks, list):
            return
        for task in tasks:
            if not isinstance(task, dict):
                continue
            assignment = task.get("assignment")
            if not isinstance(assignment, dict):
                continue
            task_id = str(task.get("id"))
            workspace = Path(str(assignment.get("workspace_path", ""))).resolve()
            kind = assignment.get("workspace_kind")
            if kind == "main" and workspace != root:
                yield _finding(
                    "TASK_MAIN_WORKSPACE_MISMATCH",
                    "CRITICAL",
                    f"Main assignment for {task_id} does not point to repository root",
                    registry,
                )
            if kind == "worktree" and workspace == root:
                yield _finding(
                    "TASK_WORKTREE_IS_MAIN",
                    "CRITICAL",
                    f"Worktree assignment for {task_id} points to main",
                    registry,
                )
            if task.get("status") in {"in_progress", "waiting_user"} and not workspace.is_dir():
                yield _finding(
                    "TASK_WORKSPACE_MISSING",
                    "ERROR",
                    f"Active assignment for {task_id} has no workspace",
                    workspace,
                )
            base_commit = assignment.get("base_commit")
            if isinstance(base_commit, str) and (root / ".git").exists():
                check = subprocess.run(
                    ["git", "cat-file", "-e", f"{base_commit}^{{commit}}"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if check.returncode != 0:
                    yield _finding(
                        "TASK_BASE_COMMIT_MISSING",
                        "ERROR",
                        f"Assignment base commit is unavailable for {task_id}",
                        registry,
                    )
        from .registry_lock import RegistryLock, RegistryLockError

        try:
            state = RegistryLock(tasks_root).inspect()
            if state.status == "invalid":
                yield _finding(
                    "TASK_REGISTRY_LOCK_INVALID",
                    "ERROR",
                    "Task Registry lock metadata is invalid",
                    tasks_root / "checkpoints/registry.lock",
                )
            elif state.status == "stale":
                yield _finding(
                    "TASK_REGISTRY_LOCK_STALE",
                    "WARNING",
                    "Task Registry has a recoverable stale lock",
                    tasks_root / "checkpoints/registry.lock",
                )
        except RegistryLockError as exc:
            yield _finding(
                "TASK_REGISTRY_LOCK_INVALID",
                "ERROR",
                f"Task Registry lock inspection failed: {exc}",
                tasks_root / "checkpoints/registry.lock",
            )
    except (OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        yield _finding(
            "TASK_WORKSPACE_CHECK_FAILED",
            "ERROR",
            f"Task workspace validation failed: {exc}",
            registry,
        )


def _task_finalization_checks(root: Path) -> Iterable[Finding]:
    receipts = root / ".orchestrator" / "tasks" / "finalization"
    if not receipts.exists():
        return
    try:
        from .finalization import load_receipt

        for path in sorted(receipts.glob("TASK-*.json")):
            identifier = path.name.removeprefix("TASK-").removesuffix(".json")
            if len(identifier) < 4 or not identifier.isdigit():
                continue
            try:
                receipt = load_receipt(path)
            except Exception as exc:
                yield _finding(
                    "TASK_FINALIZATION_INVALID",
                    "ERROR",
                    f"Finalization receipt is invalid: {exc}",
                    path,
                )
                continue
            if receipt.pending_approval_hashes:
                yield _finding(
                    "TASK_FINALIZATION_PENDING",
                    "INFO",
                    f"{receipt.task_id} is waiting for "
                    f"{len(receipt.pending_approval_hashes)} memory approval(s)",
                    path,
                )
            elif receipt.ready_for_completion:
                yield _finding(
                    "TASK_FINALIZATION_READY",
                    "INFO",
                    f"{receipt.task_id} has completion-ready finalization evidence",
                    path,
                )
    except Exception as exc:
        yield _finding(
            "TASK_FINALIZATION_CHECK_FAILED",
            "ERROR",
            f"Task finalization validation failed: {exc}",
            receipts,
        )


def _jsonl_records(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"record {number} is not an object")
        records.append(value)
    return records


def _memory_knowledge_checks(root: Path) -> Iterable[Finding]:
    ignore = root / ".gitignore"
    ignore_text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    is_core_repository = (
        (root / "orchestrator").is_dir()
        and (root / "skills").is_dir()
        and (root / "config/knowledge-ontology.json").is_file()
        and ".orchestrator/" in {
            line.strip()
            for line in ignore_text.splitlines()
            if line.strip() and not line.startswith("#")
        }
    )
    if is_core_repository:
        return
    lifecycle_root = root / ".orchestrator"
    if not (
        (lifecycle_root / "memory").exists()
        or (lifecycle_root / "knowledge").exists()
        or (lifecycle_root / "config.json").exists()
    ):
        return
    canonical = (
        lifecycle_root / "memory/entries.jsonl",
        lifecycle_root / "memory/events.jsonl",
        lifecycle_root / "memory/approvals.jsonl",
        lifecycle_root / "knowledge/ontology.json",
        lifecycle_root / "knowledge/nodes.jsonl",
        lifecycle_root / "knowledge/edges.jsonl",
    )
    for path in canonical:
        if not path.is_file():
            yield _finding(
                "MEMORY_KNOWLEDGE_STORE_MISSING",
                "ERROR",
                "Canonical memory/knowledge store is missing",
                path,
            )
    if any(not path.is_file() for path in canonical):
        return

    text = ignore_text
    required_ignored = (
        ".orchestrator/memory/proposals/",
        ".orchestrator/knowledge/indexes/",
        ".orchestrator/migrations/backups/",
    )
    if any(value not in text for value in required_ignored):
        yield _finding(
            "MEMORY_KNOWLEDGE_GIT_POLICY",
            "ERROR",
            "Operational memory/knowledge artifacts are not fully ignored",
            ignore,
        )
    broad = {".orchestrator/", ".orchestrator/memory/", ".orchestrator/knowledge/"}
    lines = {line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#")}
    if broad & lines:
        yield _finding(
            "MEMORY_KNOWLEDGE_GIT_POLICY",
            "CRITICAL",
            "Git ignore rules hide canonical memory/knowledge stores",
            ignore,
        )

    try:
        for path in (*canonical[:3], *canonical[4:]):
            _jsonl_records(path)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        yield _finding(
            "MEMORY_KNOWLEDGE_INVALID_JSONL",
            "ERROR",
            f"Canonical JSONL is invalid: {exc}",
            path,
        )
        return

    try:
        from .memory import effective_entries

        entries = effective_entries(root)
        for entry in entries:
            source = Path(entry.source)
            if not source.is_absolute():
                source = root / source
            source = source.resolve()
            try:
                source.relative_to(root)
            except ValueError:
                yield _finding(
                    "MEMORY_PROVENANCE_UNSAFE",
                    "CRITICAL",
                    f"Memory source escapes project root: {entry.id}",
                    canonical[0],
                )
                continue
            if (
                not source.is_file()
                or hashlib.sha256(source.read_bytes()).hexdigest() != entry.source_digest
            ):
                yield _finding(
                    "MEMORY_PROVENANCE_STALE",
                    "ERROR",
                    f"Memory source is missing or stale: {entry.id}",
                    source,
                )
    except Exception as exc:
        yield _finding(
            "MEMORY_LIFECYCLE_INVALID",
            "ERROR",
            f"Memory effective state is invalid: {exc}",
            canonical[0],
        )

    try:
        from .knowledge import effective_graph, rebuild_indexes
        from .ontology import load_core_ontology, load_project_ontology, merge_ontology

        ontology = merge_ontology(
            load_core_ontology(root / "config/knowledge-ontology.json"),
            load_project_ontology(canonical[3]),
        )
        nodes, edges = effective_graph(canonical[4], canonical[5])
        for node in nodes:
            if node.kind not in ontology.node_kinds:
                raise ValueError(f"unknown node kind: {node.kind}")
            source = Path(node.source)
            if not source.is_absolute():
                source = root / source
            source = source.resolve()
            try:
                source.relative_to(root)
            except ValueError:
                yield _finding(
                    "KNOWLEDGE_PROVENANCE_UNSAFE",
                    "CRITICAL",
                    f"Knowledge node source escapes project root: {node.id}",
                    canonical[4],
                )
                continue
            if (
                not source.is_file()
                or node.source_digest is not None
                and hashlib.sha256(source.read_bytes()).hexdigest() != node.source_digest
            ):
                yield _finding(
                    "KNOWLEDGE_PROVENANCE_STALE",
                    "ERROR",
                    f"Knowledge node source is missing or stale: {node.id}",
                    source,
                )
        for edge in edges:
            if edge.relation not in ontology.relations:
                raise ValueError(f"unknown edge relation: {edge.relation}")
            source = Path(edge.source)
            if not source.is_absolute():
                source = root / source
            source = source.resolve()
            try:
                source.relative_to(root)
            except ValueError:
                yield _finding(
                    "KNOWLEDGE_PROVENANCE_UNSAFE",
                    "CRITICAL",
                    f"Knowledge edge source escapes project root: {edge.id}",
                    canonical[5],
                )
                continue
            if (
                not source.is_file()
                or edge.source_digest is not None
                and hashlib.sha256(source.read_bytes()).hexdigest() != edge.source_digest
            ):
                yield _finding(
                    "KNOWLEDGE_PROVENANCE_STALE",
                    "ERROR",
                    f"Knowledge edge source is missing or stale: {edge.id}",
                    source,
                )
        index = lifecycle_root / "knowledge/indexes/index.json"
        if index.exists():
            with tempfile.TemporaryDirectory() as temporary:
                rebuilt = rebuild_indexes(
                    canonical[4], canonical[5], Path(temporary) / "index.json"
                )
                if index.read_bytes() != rebuilt.read_bytes():
                    yield _finding(
                        "KNOWLEDGE_INDEX_STALE",
                        "ERROR",
                        "Derived knowledge index does not match canonical stores",
                        index,
                    )
    except Exception as exc:
        yield _finding(
            "KNOWLEDGE_GRAPH_INVALID",
            "ERROR",
            f"Knowledge ontology or graph is invalid: {exc}",
            canonical[3],
        )



def run_health_checks(root: Path | str = ".", *, scope: str = "all") -> HealthReport:
    project_root = Path(root).resolve()
    findings: list[Finding] = []
    if scope not in {"all", "tasks"}:
        findings.append(_finding("INVALID_SCOPE", "ERROR", f"Unsupported health scope: {scope}"))
    elif scope == "tasks":
        findings.extend(_task_checks(project_root))
        findings.extend(_task_workspace_checks(project_root))
        findings.extend(_task_finalization_checks(project_root))
    else:
        findings.extend(_required_structure(project_root))
        findings.extend(_schema_checks(project_root))
        findings.extend(_registry_checks(project_root))
        findings.extend(_skill_projection_checks(project_root))
        findings.extend(_task_checks(project_root))
        findings.extend(_task_workspace_checks(project_root))
        findings.extend(_task_finalization_checks(project_root))
        findings.extend(_memory_knowledge_checks(project_root))
    findings.sort(key=lambda item: (SEVERITY_ORDER[item.severity], item.code, item.path or "", item.message))
    return HealthReport(tuple(findings))


def format_text(report: HealthReport) -> str:
    if not report.findings:
        return "INFO HEALTHY No findings"
    return "\n".join(
        f"{item.severity} {item.code} {item.message}" + (f" [{item.path}]" if item.path else "")
        for item in report.findings
    )


def format_json(report: HealthReport) -> str:
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
