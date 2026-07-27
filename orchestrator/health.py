from __future__ import annotations

import json
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
        "docs/specifications/orchestrator-specification-ru.md",
        "docs/specifications/task-layer-specification-ru.md",
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
    registry = root / "registries" / "skills.json"
    payload, error = _load_json(registry)
    if error or not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
        return
    try:
        from .skill_installer import check_skill_drift

        for entry in payload["entries"]:
            if not isinstance(entry, dict) or not entry.get("enabled", False):
                continue
            skill_id = entry.get("id")
            relative = entry.get("path")
            if not isinstance(skill_id, str) or not isinstance(relative, str):
                continue
            source = (root / relative).parent
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


def run_health_checks(root: Path | str = ".", *, scope: str = "all") -> HealthReport:
    project_root = Path(root).resolve()
    findings: list[Finding] = []
    if scope not in {"all", "tasks"}:
        findings.append(_finding("INVALID_SCOPE", "ERROR", f"Unsupported health scope: {scope}"))
    elif scope == "tasks":
        findings.extend(_task_checks(project_root))
    else:
        findings.extend(_required_structure(project_root))
        findings.extend(_schema_checks(project_root))
        findings.extend(_registry_checks(project_root))
        findings.extend(_skill_projection_checks(project_root))
        findings.extend(_task_checks(project_root))
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
