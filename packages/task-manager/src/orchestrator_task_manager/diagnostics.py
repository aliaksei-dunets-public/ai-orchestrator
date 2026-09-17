"""Read-only диагностика единого снимка с общим guard сервиса."""
from __future__ import annotations

import json
from typing import Any, Callable

from .contracts import TASK_STATUSES, TaskError
from .repository import SQLiteTaskRepository

def health_check(repository: SQLiteTaskRepository, ready_guard: Callable[[dict[str, Any]], None]) -> list[dict[str, str]]:
    """Read-only integrity diagnostics; never invents evidence or repairs state."""
    issues: list[dict[str, str]] = []
    with repository.read_transaction() as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            issues.append({"severity": "critical", "code": "sqlite_integrity", "detail": integrity})
        rows = db.execute("SELECT id,body,version,status,title,type FROM tasks ORDER BY id").fetchall()
        event_stats = {row[0]: row[1:] for row in db.execute(
            "SELECT task_id,COUNT(*),MIN(sequence),MAX(sequence),SUM(sequence != task_version) "
            "FROM events GROUP BY task_id"
        )}
        for task_id, raw, version, row_status, title, task_type in rows:
            try:
                task = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                issues.append({"severity": "critical", "code": "snapshot_invalid", "detail": task_id})
                continue
            if not isinstance(task, dict) or any(
                not isinstance(task.get(key, default), kind)
                for key, default, kind in (("artifacts", {}, dict), ("blockers", [], list), ("user_decisions", [], list))
            ) or any(not isinstance(item, dict) for item in task.get("blockers", [])):
                issues.append({"severity": "critical", "code": "snapshot_shape_invalid", "detail": task_id})
                continue
            for blocker in task.get("blockers", []):
                evidence_refs = blocker.get("evidence_refs")
                if (not isinstance(evidence_refs, list)
                        or any(not isinstance(ref, str) for ref in evidence_refs)
                        or not isinstance(blocker.get("blocking"), bool)):
                    issues.append({"severity": "error", "code": "blocker_shape_invalid", "detail": task_id})
                    break
            if task.get("id") != task_id:
                issues.append({"severity": "error", "code": "snapshot_id_mismatch", "detail": task_id})
            columns = (version, row_status, title, task_type)
            if columns and (task.get("version"), task.get("status"), task.get("title"), task.get("type")) != columns:
                issues.append({"severity": "error", "code": "snapshot_column_mismatch", "detail": task_id})
            if not isinstance(task.get("status"), str) or task.get("status") not in TASK_STATUSES:
                issues.append({"severity": "error", "code": "status_invalid", "detail": task_id})
            status = task.get("status")
            archive = task.get("archive")
            if archive is not None:
                if not isinstance(status, str) or status not in {"completed", "cancelled"}:
                    issues.append({"severity": "error", "code": "archive_status_invalid", "detail": task_id})
                if not isinstance(archive, dict) or not archive.get("archived_at") or not archive.get("terminal_at"):
                    issues.append({"severity": "error", "code": "archive_metadata_invalid", "detail": task_id})
            count, first, last, mismatches = event_stats.get(task_id, (0, None, None, 0))
            if count != task.get("version") or first != 1 or last != count or mismatches:
                issues.append({"severity": "error", "code": "event_sequence", "detail": task_id})
            if status == "ready":
                try:
                    ready_guard(task)
                except (TaskError, KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
                    issues.append({"severity": "error", "code": "ready_guard", "detail": f"{task_id}: {exc}"})
            if status == "active" and not task.get("active_claim"):
                issues.append({"severity": "error", "code": "active_without_claim", "detail": task_id})
            if status == "blocked" and not any(
                item.get("blocking") and item.get("status") == "open" for item in task.get("blockers", [])
            ):
                issues.append({"severity": "warning", "code": "blocked_without_open_blocker", "detail": task_id})
            if status == "completed" and "completion_decision" not in task.get("artifacts", {}):
                issues.append({"severity": "error", "code": "completion_evidence", "detail": task_id})
        for task_id, sequence, payload in db.execute("SELECT task_id,sequence,payload FROM events ORDER BY task_id,sequence"):
            try:
                if not isinstance(json.loads(payload), dict):
                    raise ValueError("payload должен быть объектом")
            except (ValueError, TypeError):
                issues.append({"severity": "error", "code": "event_payload_invalid", "detail": f"{task_id}:{sequence}"})
        orphan = db.execute(
            "SELECT task_id,sequence FROM events WHERE task_id NOT IN (SELECT id FROM tasks)"
        ).fetchall()
        for task_id, sequence in orphan:
            issues.append({"severity": "error", "code": "orphan_event", "detail": f"{task_id}:{sequence}"})
        if "operations" in {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:
            for operation_id, fingerprint, result in db.execute("SELECT operation_id,fingerprint,result FROM operations"):
                if not operation_id or not fingerprint:
                    issues.append({"severity": "error", "code": "operation_metadata_invalid", "detail": operation_id or "<empty>"})
                try:
                    if not isinstance(json.loads(result), dict):
                        raise ValueError("result должен быть объектом")
                except (ValueError, TypeError):
                    issues.append({"severity": "error", "code": "operation_result_invalid", "detail": operation_id})
    return issues
