from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


TASK_ID_RE = re.compile(r"TASK-(\d{4,})")
CONTEXTS_DIRNAME = "contexts"
CHECKPOINTS_DIRNAME = "checkpoints"
CRITICAL_QUESTION_RE = re.compile(
    r"(?im)^\s*-\s*(?:\[critical\]|critical\s*:|критическ(?:ий|ая)\s*:)",
)
STATUSES = {"backlog", "in_progress", "waiting_user", "blocked", "done", "cancelled"}
SLOT_STATUSES = {"in_progress", "waiting_user"}
TRANSITIONS = {
    "backlog": {"in_progress", "cancelled"},
    "in_progress": {"waiting_user", "blocked", "done", "cancelled"},
    "waiting_user": {"in_progress", "blocked", "cancelled"},
    "blocked": {"backlog", "in_progress", "cancelled"},
    "done": set(),
    "cancelled": set(),
}
EXIT_CODES = {
    "GENERAL_ERROR": 1,
    "TASK_NOT_FOUND": 2,
    "INVALID_TRANSITION": 3,
    "REGISTRY_CORRUPT": 4,
    "ACTIVE_TASK_EXISTS": 5,
    "NO_AVAILABLE_TASKS": 6,
}


@dataclass(frozen=True)
class RegistryIssue:
    code: str
    severity: str
    message: str
    path: Path | None = None


class TaskManagerError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.exit_code = EXIT_CODES.get(code, EXIT_CODES["GENERAL_ERROR"])

    def to_dict(self) -> dict[str, object]:
        return {"ok": False, "error": {"code": self.code, "message": str(self)}}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def empty_registry() -> dict[str, object]:
    return {"schema_version": 1, "next_id": 1, "tasks": []}


def _read_registry_file(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return empty_registry()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskManagerError("REGISTRY_CORRUPT", f"Cannot read registry: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskManagerError("REGISTRY_CORRUPT", "Registry root must be an object")
    return payload


def _safe_context_path(tasks_root: Path, relative: object) -> Path | None:
    if not isinstance(relative, str) or not relative:
        return None
    pure = PurePosixPath(relative)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or len(pure.parts) != 2
        or pure.parts[0] != CONTEXTS_DIRNAME
        or pure.suffix != ".md"
        or not TASK_ID_RE.fullmatch(pure.stem)
    ):
        return None
    path = (tasks_root / Path(*pure.parts)).resolve()
    try:
        path.relative_to(tasks_root.resolve())
    except ValueError:
        return None
    return path


def validate_registry(tasks_root: Path | str) -> list[RegistryIssue]:
    root = Path(tasks_root)
    registry_path = root / "tasks.json"
    try:
        payload = _read_registry_file(registry_path)
    except TaskManagerError as exc:
        return [RegistryIssue(exc.code, "ERROR", str(exc), registry_path)]
    issues: list[RegistryIssue] = []
    if payload.get("schema_version") != 1:
        issues.append(RegistryIssue("INVALID_SCHEMA_VERSION", "ERROR", "schema_version must equal 1", registry_path))
    next_id = payload.get("next_id")
    if not isinstance(next_id, int) or isinstance(next_id, bool) or next_id < 1:
        issues.append(RegistryIssue("INVALID_NEXT_ID", "ERROR", "next_id must be a positive integer", registry_path))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list):
        issues.append(RegistryIssue("INVALID_TASKS", "ERROR", "tasks must be an array", registry_path))
        return issues

    ids: set[str] = set()
    referenced: set[Path] = set()
    active = 0
    max_number = 0
    required = {"id", "title", "status", "context", "status_note", "created_at", "updated_at"}
    for index, task in enumerate(tasks):
        if not isinstance(task, dict):
            issues.append(RegistryIssue("INVALID_TASK", "ERROR", f"Task {index} must be an object", registry_path))
            continue
        missing = required - set(task)
        if missing:
            issues.append(RegistryIssue("INVALID_TASK", "ERROR", f"Task {index} missing: {sorted(missing)}", registry_path))
        task_id = task.get("id")
        match = TASK_ID_RE.fullmatch(str(task_id))
        if not match:
            issues.append(RegistryIssue("INVALID_TASK_ID", "ERROR", f"Invalid task id: {task_id}", registry_path))
        else:
            max_number = max(max_number, int(match.group(1)))
            if task_id in ids:
                issues.append(RegistryIssue("DUPLICATE_TASK_ID", "ERROR", f"Duplicate task id: {task_id}", registry_path))
            ids.add(str(task_id))
        status = task.get("status")
        if status not in STATUSES:
            issues.append(RegistryIssue("INVALID_STATUS", "ERROR", f"Invalid status for {task_id}: {status}", registry_path))
        if status in SLOT_STATUSES:
            active += 1
        context = _safe_context_path(root, task.get("context"))
        expected_context = (
            f"{CONTEXTS_DIRNAME}/{task_id}.md"
            if TASK_ID_RE.fullmatch(str(task_id))
            else None
        )
        if context is None or task.get("context") != expected_context:
            issues.append(RegistryIssue("INVALID_CONTEXT_PATH", "ERROR", f"Invalid context path for {task_id}", registry_path))
        else:
            referenced.add(context)
            if not context.is_file():
                issues.append(RegistryIssue("MISSING_CONTEXT", "ERROR", f"Missing context for {task_id}", context))
    if active > 1:
        issues.append(RegistryIssue("MULTIPLE_ACTIVE_TASKS", "ERROR", "More than one task occupies the execution slot", registry_path))
    if isinstance(next_id, int) and next_id <= max_number:
        issues.append(RegistryIssue("INVALID_NEXT_ID", "ERROR", "next_id must exceed every allocated task id", registry_path))
    contexts_root = root / CONTEXTS_DIRNAME
    if contexts_root.exists():
        for context in contexts_root.glob("TASK-*.md"):
            if context.resolve() not in referenced:
                issues.append(RegistryIssue("ORPHAN_CONTEXT", "ERROR", "Context is not registered", context))
    return issues


def _parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise TaskManagerError("GENERAL_ERROR", "Task Context must start with frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise TaskManagerError("GENERAL_ERROR", "Task Context frontmatter is not closed") from exc
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise TaskManagerError("GENERAL_ERROR", f"Invalid frontmatter line: {line}")
        key, value = line.split(":", 1)
        key = key.strip()
        if key in fields:
            raise TaskManagerError("GENERAL_ERROR", f"Duplicate frontmatter field: {key}")
        fields[key] = value.strip().strip("\"'")
    return fields, end


def _registered_context(text: str, task_id: str, revision: int, title: str) -> str:
    fields, end = _parse_frontmatter(text)
    fields["id"] = task_id
    fields["revision"] = str(revision)
    order = ("schema_version", "id", "revision", "title", "type", "mode", "risk", "created_by")
    frontmatter = ["---"]
    for key in order:
        if key in fields:
            frontmatter.append(f"{key}: {fields[key]}")
    for key, value in fields.items():
        if key not in order and key != "status":
            frontmatter.append(f"{key}: {value}")
    frontmatter.append("---")
    body = text.splitlines()[end + 1 :]
    first_heading = next((index for index, line in enumerate(body) if line.startswith("# ")), None)
    heading = f"# {task_id} — {title}"
    if first_heading is None:
        body = ["", heading, *body]
    else:
        body[first_heading] = heading
    if "# Execution Record" not in body:
        body.extend(["", "# Execution Record", "", "## Итог выполнения", ""])
    return "\n".join([*frontmatter, *body]).rstrip() + "\n"


class TaskManager:
    def __init__(self, tasks_root: Path | str):
        self.tasks_root = Path(tasks_root).resolve()
        self.registry_path = self.tasks_root / "tasks.json"
        self.contexts_root = self.tasks_root / CONTEXTS_DIRNAME
        self.checkpoints_root = self.tasks_root / CHECKPOINTS_DIRNAME

    def _ensure_task_directory(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        resolved = directory.resolve()
        try:
            resolved.relative_to(self.tasks_root)
        except ValueError as exc:
            raise TaskManagerError(
                "GENERAL_ERROR",
                f"Task storage directory escapes tasks root: {directory}",
            ) from exc
        return resolved

    def _read(self) -> dict[str, Any]:
        payload = _read_registry_file(self.registry_path)
        issues = validate_registry(self.tasks_root) if self.registry_path.exists() else []
        if issues:
            summary = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
            raise TaskManagerError("REGISTRY_CORRUPT", summary)
        return payload

    def _write(self, payload: dict[str, Any]) -> None:
        self.tasks_root.mkdir(parents=True, exist_ok=True)
        temporary = self.registry_path.with_name(f"{self.registry_path.name}.{os.getpid()}.tmp")
        data = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.registry_path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def initialize(self) -> None:
        self._ensure_task_directory(self.contexts_root)
        self._ensure_task_directory(self.checkpoints_root)
        if not self.registry_path.exists():
            self._write(empty_registry())

    def checkpoint_path(self, task_id: str) -> Path:
        if not TASK_ID_RE.fullmatch(task_id):
            raise TaskManagerError("GENERAL_ERROR", f"Invalid task id: {task_id}")
        checkpoints_root = self._ensure_task_directory(self.checkpoints_root)
        return checkpoints_root / f"{task_id}.checkpoint.lock"

    def list_tasks(self) -> list[dict[str, Any]]:
        return [dict(task) for task in self._read()["tasks"]]

    def show(self, task_id: str) -> dict[str, Any]:
        for task in self._read()["tasks"]:
            if task["id"] == task_id:
                return dict(task)
        raise TaskManagerError("TASK_NOT_FOUND", f"Task not found: {task_id}")

    def next_task(self) -> dict[str, Any]:
        for task in self._read()["tasks"]:
            if task["status"] == "backlog":
                return dict(task)
        raise TaskManagerError("NO_AVAILABLE_TASKS", "No backlog tasks are available")

    def register(self, draft: Path | str) -> dict[str, Any]:
        payload = self._read()
        source = Path(draft)
        if not source.is_absolute():
            source = self.tasks_root / source
        source = source.resolve()
        drafts_root = (self.tasks_root / "drafts").resolve()
        try:
            source.relative_to(drafts_root)
        except ValueError as exc:
            raise TaskManagerError("GENERAL_ERROR", "Draft must be inside tasks/drafts") from exc
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise TaskManagerError("GENERAL_ERROR", f"Cannot read draft: {exc}") from exc
        fields, _ = _parse_frontmatter(text)
        required = ("schema_version", "title", "type", "mode", "risk", "created_by")
        missing = [field for field in required if not fields.get(field)]
        if missing:
            raise TaskManagerError("GENERAL_ERROR", f"Draft missing fields: {missing}")
        if fields["schema_version"] != "1":
            raise TaskManagerError("GENERAL_ERROR", "Draft schema_version must equal 1")
        if fields.get("id", "").lower() not in {"", "null", "none", "~"}:
            raise TaskManagerError("GENERAL_ERROR", "Draft must not contain an allocated id")
        if fields.get("mode") == "deep" and fields.get("approach_approved", "").lower() != "true":
            raise TaskManagerError("GENERAL_ERROR", "Deep draft requires explicit approach approval")
        open_questions = text.split("## Открытые вопросы", 1)
        if len(open_questions) == 2:
            section = open_questions[1].split("\n#", 1)[0]
            if CRITICAL_QUESTION_RE.search(section):
                raise TaskManagerError("GENERAL_ERROR", "Critical open question blocks registration")
        number = int(payload["next_id"])
        task_id = f"TASK-{number:04d}"
        contexts_root = self._ensure_task_directory(self.contexts_root)
        self._ensure_task_directory(self.checkpoints_root)
        target = contexts_root / f"{task_id}.md"
        if target.exists():
            raise TaskManagerError("REGISTRY_CORRUPT", f"Target context already exists: {target}")
        registered = _registered_context(text, task_id, 1, fields["title"])
        target.write_text(registered, encoding="utf-8", newline="\n")
        now = _now()
        record = {
            "id": task_id,
            "title": fields["title"],
            "status": "backlog",
            "context": target.relative_to(self.tasks_root).as_posix(),
            "status_note": None,
            "created_at": now,
            "updated_at": now,
        }
        payload["next_id"] = number + 1
        payload["tasks"].append(record)
        try:
            self._write(payload)
        except Exception:
            if target.exists():
                target.unlink()
            raise
        result = dict(record)
        try:
            source.unlink()
        except OSError as exc:
            result["cleanup_warning"] = f"Registered successfully but could not remove draft: {exc}"
        return result

    def _slot_occupied(self, tasks: list[dict[str, Any]], excluding: str | None = None) -> bool:
        return any(task["id"] != excluding and task["status"] in SLOT_STATUSES for task in tasks)

    def claim_next(self) -> dict[str, Any]:
        payload = self._read()
        tasks = payload["tasks"]
        if self._slot_occupied(tasks):
            raise TaskManagerError("ACTIVE_TASK_EXISTS", "A task already occupies the execution slot")
        for task in tasks:
            if task["status"] == "backlog":
                task["status"] = "in_progress"
                task["status_note"] = None
                task["updated_at"] = _now()
                self._write(payload)
                return dict(task)
        raise TaskManagerError("NO_AVAILABLE_TASKS", "No backlog tasks are available")

    def set_status(self, task_id: str, new_status: str, note: str | None = None, *, terminal_command: bool = False) -> dict[str, Any]:
        payload = self._read()
        if new_status not in STATUSES:
            raise TaskManagerError("INVALID_TRANSITION", f"Unknown status: {new_status}")
        if new_status in {"done", "cancelled"} and not terminal_command:
            raise TaskManagerError("INVALID_TRANSITION", f"Use a dedicated command to set {new_status}")
        task = next((item for item in payload["tasks"] if item["id"] == task_id), None)
        if task is None:
            raise TaskManagerError("TASK_NOT_FOUND", f"Task not found: {task_id}")
        current = task["status"]
        if new_status not in TRANSITIONS[current]:
            raise TaskManagerError("INVALID_TRANSITION", f"Transition from {current} to {new_status} is not allowed")
        if new_status == "in_progress" and self._slot_occupied(payload["tasks"], excluding=task_id):
            raise TaskManagerError("ACTIVE_TASK_EXISTS", "A task already occupies the execution slot")
        task["status"] = new_status
        task["status_note"] = note
        task["updated_at"] = _now()
        self._write(payload)
        return dict(task)

    def block(self, task_id: str, note: str) -> dict[str, Any]:
        if not note.strip():
            raise TaskManagerError("GENERAL_ERROR", "Blocking requires a non-empty note")
        return self.set_status(task_id, "blocked", note)

    def resume(self, task_id: str) -> dict[str, Any]:
        return self.set_status(task_id, "in_progress")

    def complete(self, task_id: str) -> dict[str, Any]:
        result = self.set_status(task_id, "done", terminal_command=True)
        try:
            checkpoint = self.checkpoint_path(task_id)
            checkpoint.unlink(missing_ok=True)
        except (OSError, TaskManagerError) as exc:
            result["cleanup_warning"] = (
                f"Task completed but checkpoint could not be removed: {exc}"
            )
        return result

    def cancel(self, task_id: str, note: str | None = None) -> dict[str, Any]:
        return self.set_status(task_id, "cancelled", note, terminal_command=True)
