from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .registry_lock import RegistryLock, RegistryLockError
from .worktree_manager import (
    COMMIT_RE,
    SAFE_RUN_RE,
    WorktreeAssignment,
    WorktreeError,
    WorktreeManager,
)


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
    "INVALID_EXECUTION_MODE": 7,
    "WORKSPACE_ERROR": 8,
    "REGISTRY_LOCKED": 9,
}


@dataclass(frozen=True)
class RegistryIssue:
    code: str
    severity: str
    message: str
    path: Path | None = None


@dataclass(frozen=True)
class ExecutionSettings:
    mode: str = "serial"
    run_id: str | None = None
    max_workers: int = 1
    worktree_root: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"serial", "isolated_parallel"}:
            raise TaskManagerError(
                "INVALID_EXECUTION_MODE",
                f"Unsupported execution mode: {self.mode}",
            )
        if (
            not isinstance(self.max_workers, int)
            or isinstance(self.max_workers, bool)
            or not 1 <= self.max_workers <= 16
        ):
            raise TaskManagerError(
                "INVALID_EXECUTION_MODE",
                "max_workers must be an integer between 1 and 16",
            )
        if self.mode == "serial":
            if self.run_id is not None or self.max_workers != 1:
                raise TaskManagerError(
                    "INVALID_EXECUTION_MODE",
                    "serial mode does not accept run_id and requires max_workers=1",
                )
            return
        if (
            self.run_id is None
            or not SAFE_RUN_RE.fullmatch(self.run_id)
            or self.max_workers < 2
            or not isinstance(self.worktree_root, str)
            or not self.worktree_root.strip()
        ):
            raise TaskManagerError(
                "INVALID_EXECUTION_MODE",
                "isolated_parallel requires a valid run_id, max_workers=2..16 and worktree_root",
            )


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
    active_tasks: list[dict[str, Any]] = []
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
            active_tasks.append(task)
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
        assignment = task.get("assignment")
        if assignment is not None:
            issues.extend(_validate_assignment(assignment, task_id, registry_path))
    if len(active_tasks) > 1:
        assignments = [task.get("assignment") for task in active_tasks]
        if not all(
            isinstance(item, dict) and item.get("mode") == "isolated_parallel"
            for item in assignments
        ):
            issues.append(RegistryIssue("MULTIPLE_ACTIVE_TASKS", "ERROR", "More than one task occupies the serial execution slot", registry_path))
        else:
            workspaces = [str(item["workspace_path"]) for item in assignments]
            if len(workspaces) != len(set(workspaces)):
                issues.append(RegistryIssue("DUPLICATE_ACTIVE_WORKSPACE", "CRITICAL", "Active tasks share one workspace", registry_path))
            active_by_run: dict[str, int] = {}
            limit_by_run: dict[str, int] = {}
            for item in assignments:
                run_id = str(item["run_id"])
                active_by_run[run_id] = active_by_run.get(run_id, 0) + 1
                limit_by_run[run_id] = int(item["max_workers"])
            for run_id, count in active_by_run.items():
                if count > limit_by_run[run_id]:
                    issues.append(RegistryIssue("WORKER_LIMIT_EXCEEDED", "ERROR", f"Run {run_id} exceeds max_workers", registry_path))
    assignments_by_run: dict[str, list[dict[str, Any]]] = {}
    for task in tasks:
        assignment = task.get("assignment") if isinstance(task, dict) else None
        if isinstance(assignment, dict) and isinstance(assignment.get("run_id"), str):
            assignments_by_run.setdefault(assignment["run_id"], []).append(assignment)
    for run_id, assignments in assignments_by_run.items():
        sequences = [item.get("sequence") for item in assignments]
        workspaces = [item.get("workspace_path") for item in assignments]
        branches = [
            item.get("branch")
            for item in assignments
            if item.get("workspace_kind") == "worktree"
        ]
        limits = {item.get("max_workers") for item in assignments}
        if len(sequences) != len(set(sequences)):
            issues.append(RegistryIssue("DUPLICATE_RUN_SEQUENCE", "ERROR", f"Run {run_id} has duplicate sequence values", registry_path))
        if len(workspaces) != len(set(workspaces)):
            issues.append(RegistryIssue("DUPLICATE_RUN_WORKSPACE", "CRITICAL", f"Run {run_id} reuses a workspace", registry_path))
        if len(branches) != len(set(branches)):
            issues.append(RegistryIssue("DUPLICATE_RUN_BRANCH", "ERROR", f"Run {run_id} reuses a branch", registry_path))
        if len(limits) != 1:
            issues.append(RegistryIssue("INCONSISTENT_WORKER_LIMIT", "ERROR", f"Run {run_id} has inconsistent max_workers", registry_path))
        first = [item for item in assignments if item.get("sequence") == 1]
        if len(first) != 1 or first[0].get("workspace_kind") != "main":
            issues.append(RegistryIssue("INVALID_RUN_BOOTSTRAP", "ERROR", f"Run {run_id} must have exactly one main sequence 1 assignment", registry_path))
        if any(
            item.get("sequence") != 1 and item.get("workspace_kind") != "worktree"
            for item in assignments
        ):
            issues.append(RegistryIssue("INVALID_RUN_WORKTREE", "ERROR", f"Run {run_id} sequence 2+ must use worktrees", registry_path))
    if isinstance(next_id, int) and next_id <= max_number:
        issues.append(RegistryIssue("INVALID_NEXT_ID", "ERROR", "next_id must exceed every allocated task id", registry_path))
    contexts_root = root / CONTEXTS_DIRNAME
    if contexts_root.exists():
        for context in contexts_root.glob("TASK-*.md"):
            if context.resolve() not in referenced:
                issues.append(RegistryIssue("ORPHAN_CONTEXT", "ERROR", "Context is not registered", context))
    return issues


def _validate_assignment(
    assignment: object,
    task_id: object,
    registry_path: Path,
) -> list[RegistryIssue]:
    if not isinstance(assignment, dict):
        return [RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} must be an object", registry_path)]
    required = {
        "mode",
        "run_id",
        "sequence",
        "max_workers",
        "workspace_kind",
        "workspace_path",
        "branch",
        "base_commit",
        "commit_evidence",
    }
    if set(assignment) != required:
        return [RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid fields", registry_path)]
    issues: list[RegistryIssue] = []
    if assignment.get("mode") != "isolated_parallel":
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid mode", registry_path))
    run_id = assignment.get("run_id")
    if not isinstance(run_id, str) or not SAFE_RUN_RE.fullmatch(run_id):
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid run_id", registry_path))
    sequence = assignment.get("sequence")
    workers = assignment.get("max_workers")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid sequence", registry_path))
    if not isinstance(workers, int) or isinstance(workers, bool) or not 2 <= workers <= 16:
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid max_workers", registry_path))
    kind = assignment.get("workspace_kind")
    path = assignment.get("workspace_path")
    branch = assignment.get("branch")
    if kind not in {"main", "worktree"} or not isinstance(path, str) or not Path(path).is_absolute():
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid workspace", registry_path))
    if kind == "main" and branch is not None:
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Main assignment for {task_id} must not have a branch", registry_path))
    if kind == "worktree" and (
        not isinstance(branch, str)
        or not re.fullmatch(
            r"orchestrator/[a-z0-9][a-z0-9._-]{0,63}/task-[0-9]{4,}",
            branch,
        )
    ):
        issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Worktree assignment for {task_id} has invalid branch", registry_path))
    for field in ("base_commit", "commit_evidence"):
        value = assignment.get(field)
        if field == "commit_evidence" and value is None:
            continue
        if not isinstance(value, str) or not COMMIT_RE.fullmatch(value):
            issues.append(RegistryIssue("INVALID_ASSIGNMENT", "ERROR", f"Assignment for {task_id} has invalid {field}", registry_path))
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
            try:
                with RegistryLock(self.tasks_root):
                    if not self.registry_path.exists():
                        self._write(empty_registry())
            except RegistryLockError as exc:
                raise TaskManagerError("REGISTRY_LOCKED", str(exc)) from exc

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
        try:
            with RegistryLock(self.tasks_root):
                return self._register_locked(draft)
        except RegistryLockError as exc:
            raise TaskManagerError("REGISTRY_LOCKED", str(exc)) from exc

    def _register_locked(self, draft: Path | str) -> dict[str, Any]:
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

    def claim_next(
        self,
        settings: ExecutionSettings | None = None,
        *,
        repository_root: Path | str | None = None,
    ) -> dict[str, Any]:
        resolved = settings or ExecutionSettings()
        try:
            with RegistryLock(self.tasks_root):
                return self._claim_next_locked(resolved, repository_root=repository_root)
        except RegistryLockError as exc:
            raise TaskManagerError("REGISTRY_LOCKED", str(exc)) from exc

    def _claim_next_locked(
        self,
        settings: ExecutionSettings,
        *,
        repository_root: Path | str | None,
    ) -> dict[str, Any]:
        payload = self._read()
        tasks = payload["tasks"]
        if settings.mode == "serial":
            if self._slot_occupied(tasks):
                raise TaskManagerError("ACTIVE_TASK_EXISTS", "A task already occupies the execution slot")
        else:
            active = [task for task in tasks if task["status"] in SLOT_STATUSES]
            if any(not isinstance(task.get("assignment"), dict) for task in active):
                raise TaskManagerError("ACTIVE_TASK_EXISTS", "A serial task already occupies the main workspace")
            same_run = [
                task for task in active
                if task["assignment"]["run_id"] == settings.run_id
            ]
            if len(same_run) >= settings.max_workers:
                raise TaskManagerError("ACTIVE_TASK_EXISTS", "The isolated run reached max_workers")
        for task in tasks:
            if task["status"] == "backlog":
                if settings.mode == "isolated_parallel":
                    self._assign_isolated(
                        payload,
                        task,
                        settings,
                        repository_root=repository_root,
                    )
                task["status"] = "in_progress"
                task["status_note"] = None
                task["updated_at"] = _now()
                try:
                    self._write(payload)
                except Exception:
                    assignment = task.get("assignment")
                    if (
                        settings.mode == "isolated_parallel"
                        and isinstance(assignment, dict)
                        and assignment.get("workspace_kind") == "worktree"
                    ):
                        self._cleanup_unpublished_assignment(
                            task["id"],
                            assignment,
                            repository_root=repository_root,
                        )
                    raise
                return dict(task)
        raise TaskManagerError("NO_AVAILABLE_TASKS", "No backlog tasks are available")

    def _assign_isolated(
        self,
        payload: dict[str, Any],
        task: dict[str, Any],
        settings: ExecutionSettings,
        *,
        repository_root: Path | str | None,
    ) -> None:
        run_tasks = [
            item
            for item in payload["tasks"]
            if isinstance(item.get("assignment"), dict)
            and item["assignment"].get("run_id") == settings.run_id
        ]
        sequence = max(
            (int(item["assignment"]["sequence"]) for item in run_tasks),
            default=0,
        ) + 1
        repository = (
            Path(repository_root).resolve()
            if repository_root is not None
            else self.tasks_root.parents[1].resolve()
        )
        try:
            manager = WorktreeManager(repository, settings.worktree_root or "")
            if sequence == 1:
                if any(
                    item["status"] in SLOT_STATUSES
                    and (
                        not isinstance(item.get("assignment"), dict)
                        or item["assignment"].get("workspace_kind") == "main"
                    )
                    for item in payload["tasks"]
                ):
                    raise TaskManagerError("ACTIVE_TASK_EXISTS", "The main workspace already has an active writer")
                assignment = manager.main_assignment(task["id"], settings.run_id or "")
            else:
                bootstrap = min(
                    run_tasks,
                    key=lambda item: int(item["assignment"]["sequence"]),
                )
                bootstrap_assignment = bootstrap["assignment"]
                commit = bootstrap_assignment.get("commit_evidence")
                if (
                    bootstrap["status"] != "done"
                    or bootstrap_assignment.get("workspace_kind") != "main"
                    or not isinstance(commit, str)
                    or not COMMIT_RE.fullmatch(commit)
                ):
                    raise TaskManagerError(
                        "WORKSPACE_ERROR",
                        "The main bootstrap task must complete with validated commit evidence before worktree allocation",
                    )
                assignment = manager.create(
                    task["id"],
                    task["title"],
                    settings.run_id or "",
                    commit,
                )
        except WorktreeError as exc:
            raise TaskManagerError("WORKSPACE_ERROR", str(exc)) from exc
        task["assignment"] = {
            "mode": "isolated_parallel",
            "run_id": settings.run_id,
            "sequence": sequence,
            "max_workers": settings.max_workers,
            "workspace_kind": assignment.workspace_kind,
            "workspace_path": assignment.workspace_path,
            "branch": assignment.branch,
            "base_commit": assignment.base_commit,
            "commit_evidence": None,
        }

    def _cleanup_unpublished_assignment(
        self,
        task_id: str,
        assignment: dict[str, object],
        *,
        repository_root: Path | str | None,
    ) -> None:
        repository = (
            Path(repository_root).resolve()
            if repository_root is not None
            else self.tasks_root.parents[1].resolve()
        )
        try:
            WorktreeManager(
                repository,
                _assignment_worktree_root(assignment, repository),
            ).cleanup(
                _worktree_assignment(task_id, assignment),
                outcome="cancelled",
            )
        except WorktreeError:
            # A failed rollback is intentionally preserved for explicit recovery.
            return

    def set_status(self, task_id: str, new_status: str, note: str | None = None, *, terminal_command: bool = False) -> dict[str, Any]:
        try:
            with RegistryLock(self.tasks_root):
                return self._set_status_locked(
                    task_id,
                    new_status,
                    note,
                    terminal_command=terminal_command,
                )
        except RegistryLockError as exc:
            raise TaskManagerError("REGISTRY_LOCKED", str(exc)) from exc

    def _set_status_locked(self, task_id: str, new_status: str, note: str | None = None, *, terminal_command: bool = False) -> dict[str, Any]:
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
        if new_status == "in_progress":
            assignment = task.get("assignment")
            if assignment is None and self._slot_occupied(payload["tasks"], excluding=task_id):
                raise TaskManagerError("ACTIVE_TASK_EXISTS", "A task already occupies the execution slot")
            if isinstance(assignment, dict):
                active = [
                    item
                    for item in payload["tasks"]
                    if item["id"] != task_id
                    and item["status"] in SLOT_STATUSES
                    and (
                        not isinstance(item.get("assignment"), dict)
                        or item["assignment"].get("workspace_path")
                        == assignment.get("workspace_path")
                    )
                ]
                if active:
                    raise TaskManagerError("ACTIVE_TASK_EXISTS", "The assigned workspace already has an active writer")
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

    def complete(
        self,
        task_id: str,
        *,
        commit_evidence: str | None = None,
        repository_root: Path | str | None = None,
    ) -> dict[str, Any]:
        task = self.show(task_id)
        assignment = task.get("assignment")
        if isinstance(assignment, dict):
            if not isinstance(commit_evidence, str) or not COMMIT_RE.fullmatch(commit_evidence):
                raise TaskManagerError("WORKSPACE_ERROR", "isolated task completion requires a full commit id")
            repository = (
                Path(repository_root).resolve()
                if repository_root is not None
                else self.tasks_root.parents[1].resolve()
            )
            try:
                manager = WorktreeManager(repository, _assignment_worktree_root(assignment, repository))
                manager.verify_commit(_worktree_assignment(task_id, assignment), commit_evidence)
            except WorktreeError as exc:
                raise TaskManagerError("WORKSPACE_ERROR", str(exc)) from exc
            try:
                with RegistryLock(self.tasks_root):
                    payload = self._read()
                    current = next(item for item in payload["tasks"] if item["id"] == task_id)
                    if "done" not in TRANSITIONS[current["status"]]:
                        raise TaskManagerError(
                            "INVALID_TRANSITION",
                            f"Transition from {current['status']} to done is not allowed",
                        )
                    current["assignment"]["commit_evidence"] = commit_evidence.lower()
                    current["status"] = "done"
                    current["status_note"] = None
                    current["updated_at"] = _now()
                    self._write(payload)
                    result = dict(current)
            except RegistryLockError as exc:
                raise TaskManagerError("REGISTRY_LOCKED", str(exc)) from exc
        else:
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

    def assignment(self, task_id: str) -> dict[str, object] | None:
        task = self.show(task_id)
        value = task.get("assignment")
        return dict(value) if isinstance(value, dict) else None

    def cleanup_assignment(
        self,
        task_id: str,
        *,
        repository_root: Path | str | None = None,
        outcome: str,
    ) -> bool:
        task = self.show(task_id)
        assignment = task.get("assignment")
        if not isinstance(assignment, dict):
            raise TaskManagerError("WORKSPACE_ERROR", "task has no isolated workspace assignment")
        required_status = {"completed": "done", "cancelled": "cancelled"}.get(outcome)
        if required_status is not None and task["status"] != required_status:
            raise TaskManagerError(
                "WORKSPACE_ERROR",
                f"{outcome} cleanup requires task status {required_status}",
            )
        repository = (
            Path(repository_root).resolve()
            if repository_root is not None
            else self.tasks_root.parents[1].resolve()
        )
        try:
            manager = WorktreeManager(repository, _assignment_worktree_root(assignment, repository))
            return manager.cleanup(_worktree_assignment(task_id, assignment), outcome=outcome)
        except WorktreeError as exc:
            raise TaskManagerError("WORKSPACE_ERROR", str(exc)) from exc


def _worktree_assignment(
    task_id: str,
    assignment: dict[str, object],
) -> WorktreeAssignment:
    return WorktreeAssignment(
        task_id=task_id,
        run_id=str(assignment["run_id"]),
        workspace_kind=str(assignment["workspace_kind"]),
        workspace_path=str(assignment["workspace_path"]),
        branch=assignment["branch"] if isinstance(assignment["branch"], str) else None,
        base_commit=str(assignment["base_commit"]),
    )


def _assignment_worktree_root(
    assignment: dict[str, object],
    repository_root: Path,
) -> Path:
    workspace = Path(str(assignment["workspace_path"])).resolve()
    if assignment.get("workspace_kind") == "main":
        return repository_root / ".orchestrator" / "worktrees"
    if len(workspace.parents) < 2:
        raise TaskManagerError("WORKSPACE_ERROR", "assigned worktree path has no validated root")
    return workspace.parents[1]
