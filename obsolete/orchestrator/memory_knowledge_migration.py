from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path


class MigrationError(ValueError):
    pass


@dataclass(frozen=True)
class MigrationChange:
    source: str
    target: str
    source_digest: str
    target_before_digest: str | None
    content: str
    record_count: int


@dataclass(frozen=True)
class MigrationPlan:
    project_root: str
    changes: tuple[MigrationChange, ...]
    fingerprint: str
    plan_hash: str
    record_count: int


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _safe(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise MigrationError("migration path escapes project root") from exc
    return candidate


def _jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MigrationError(f"invalid legacy JSONL at {path}:{number}") from exc
        if not isinstance(value, dict):
            raise MigrationError(f"legacy record is not an object at {path}:{number}")
        records.append(value)
    return records


def _relative_source(root: Path, value: object) -> str:
    source = Path(str(value))
    if not source.is_absolute():
        return source.as_posix()
    try:
        return source.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise MigrationError("legacy provenance source is outside the project root") from exc


def _render_records(root: Path, records: list[dict[str, object]], *, graph: bool) -> str:
    rendered: list[str] = []
    for raw in records:
        item = dict(raw)
        if item.get("schema_version", 1) != 1:
            raise MigrationError("only schema-version-1 records are supported")
        item["schema_version"] = 1
        if "source" in item:
            item["source"] = _relative_source(root, item["source"])
            source = _safe(root, str(item["source"]))
            if not source.is_file():
                raise MigrationError("legacy provenance source does not exist")
            if graph and not item.get("source_digest"):
                item["source_digest"] = _sha(source.read_bytes())
        rendered.append(_canonical(item))
    return "".join(f"{line}\n" for line in rendered)


def _change(
    root: Path,
    source_name: str,
    target_name: str,
    *,
    graph: bool,
) -> MigrationChange | None:
    source = _safe(root, source_name)
    if not source.exists():
        return None
    records = _jsonl(source)
    target = _safe(root, target_name)
    content = _render_records(root, records, graph=graph)
    return MigrationChange(
        source_name,
        target_name,
        _sha(source.read_bytes()),
        _sha(target.read_bytes()) if target.exists() else None,
        content,
        len(records),
    )


def plan_migration(project_root: Path | str) -> MigrationPlan:
    root = Path(project_root).resolve()
    candidates = (
        (".orchestrator/memory.jsonl", ".orchestrator/memory/entries.jsonl", False),
        (
            ".orchestrator/knowledge/nodes.jsonl",
            ".orchestrator/knowledge/nodes.jsonl",
            True,
        ),
        (
            ".orchestrator/knowledge/edges.jsonl",
            ".orchestrator/knowledge/edges.jsonl",
            True,
        ),
    )
    changes = tuple(
        change
        for source, target, graph in candidates
        if (change := _change(root, source, target, graph=graph)) is not None
        and (source != target or change.content.encode("utf-8") != _safe(root, target).read_bytes())
    )
    fingerprint_payload = [
        {
            "source": item.source,
            "source_digest": item.source_digest,
            "target": item.target,
            "target_before_digest": item.target_before_digest,
        }
        for item in changes
    ]
    fingerprint = _sha(_canonical(fingerprint_payload).encode("utf-8"))
    plan_payload = {
        "project_root": str(root),
        "fingerprint": fingerprint,
        "changes": [
            {
                "source": item.source,
                "target": item.target,
                "content_digest": _sha(item.content.encode("utf-8")),
                "record_count": item.record_count,
            }
            for item in changes
        ],
    }
    return MigrationPlan(
        str(root),
        changes,
        fingerprint,
        _sha(_canonical(plan_payload).encode("utf-8")),
        sum(item.record_count for item in changes),
    )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply_migration(
    project_root: Path | str,
    plan: MigrationPlan,
    *,
    approved_plan_hash: str,
) -> dict[str, object]:
    root = Path(project_root).resolve()
    if str(root) != plan.project_root or approved_plan_hash != plan.plan_hash:
        raise MigrationError("migration approval is stale")
    current = plan_migration(root)
    if current.fingerprint != plan.fingerprint or current.plan_hash != plan.plan_hash:
        raise MigrationError("migration plan is stale")
    backup_root = _safe(root, f".orchestrator/migrations/backups/{plan.plan_hash}")
    manifest: list[dict[str, object]] = []
    for change in plan.changes:
        target = _safe(root, change.target)
        current_digest = _sha(target.read_bytes()) if target.exists() else None
        if current_digest != change.target_before_digest:
            raise MigrationError("migration target changed; plan is stale")
        backup_name: str | None = None
        if target.exists():
            backup_name = f"files/{change.target}"
            backup = backup_root / backup_name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, backup)
            if _sha(backup.read_bytes()) != current_digest:
                raise MigrationError("migration backup verification failed")
        manifest.append(
            {
                "target": change.target,
                "existed": target.exists(),
                "before_digest": current_digest,
                "after_digest": _sha(change.content.encode("utf-8")),
                "backup": backup_name,
            }
        )
    for change in plan.changes:
        _atomic_write(_safe(root, change.target), change.content)
    _atomic_write(
        backup_root / "manifest.json",
        json.dumps(
            {"schema_version": 1, "plan_hash": plan.plan_hash, "files": manifest},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    return {
        "schema_version": 1,
        "status": "completed",
        "plan_hash": plan.plan_hash,
        "record_count": plan.record_count,
        "changed_paths": [item.target for item in plan.changes],
    }


def rollback_migration(project_root: Path | str, plan_hash: str) -> bool:
    root = Path(project_root).resolve()
    backup_root = _safe(root, f".orchestrator/migrations/backups/{plan_hash}")
    manifest_path = backup_root / "manifest.json"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read migration manifest: {exc}") from exc
    if payload.get("plan_hash") != plan_hash or not isinstance(payload.get("files"), list):
        raise MigrationError("migration manifest is invalid")
    for item in payload["files"]:
        target = _safe(root, str(item["target"]))
        if not target.exists() or _sha(target.read_bytes()) != item["after_digest"]:
            raise MigrationError("migration target changed since apply")
    for item in reversed(payload["files"]):
        target = _safe(root, str(item["target"]))
        if item["existed"]:
            backup = (backup_root / str(item["backup"])).resolve()
            try:
                backup.relative_to(backup_root)
            except ValueError as exc:
                raise MigrationError("migration backup path escapes root") from exc
            _atomic_write(target, backup.read_text(encoding="utf-8"))
        else:
            target.unlink()
    return all(
        (
            _safe(root, str(item["target"])).exists()
            and _sha(_safe(root, str(item["target"])).read_bytes())
            == item["before_digest"]
        )
        if item["existed"]
        else not _safe(root, str(item["target"])).exists()
        for item in payload["files"]
    )
