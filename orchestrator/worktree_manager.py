from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


TASK_ID_RE = re.compile(r"TASK-[0-9]{4,}")
SAFE_RUN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
COMMIT_RE = re.compile(r"[0-9a-fA-F]{40}")


class WorktreeError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorktreeAssignment:
    task_id: str
    run_id: str
    workspace_kind: str
    workspace_path: str
    branch: str | None
    base_commit: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _run_git(root: Path, *args: str, timeout_seconds: float = 30) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise WorktreeError(f"git command unavailable or timed out: {args[0]}") from exc
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout).strip()
        raise WorktreeError(f"git {args[0]} failed: {message}")
    return completed.stdout.strip()


class WorktreeManager:
    """Create, inspect, integrate and clean task-owned Git worktrees."""

    def __init__(
        self,
        repository_root: Path | str,
        worktree_root: Path | str,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        top_level = Path(
            _run_git(self.repository_root, "rev-parse", "--show-toplevel")
        ).resolve()
        if top_level != self.repository_root:
            raise WorktreeError("repository_root must be the Git top-level directory")
        candidate = Path(worktree_root)
        if not candidate.is_absolute():
            candidate = self.repository_root / candidate
        self.worktree_root = candidate.resolve()
        if self.worktree_root == self.repository_root:
            raise WorktreeError("worktree root must not be the main workspace")
        try:
            self.repository_root.relative_to(self.worktree_root)
        except ValueError:
            pass
        else:
            raise WorktreeError("worktree root must not contain the main workspace")
        if self.worktree_root == Path(self.worktree_root.anchor):
            raise WorktreeError("worktree root must not be a filesystem root")
        self.manifest_root = self.worktree_root / ".orchestrator-ownership"

    @staticmethod
    def validate_identity(task_id: str, run_id: str) -> None:
        if not TASK_ID_RE.fullmatch(task_id):
            raise WorktreeError("invalid task id")
        if not SAFE_RUN_RE.fullmatch(run_id):
            raise WorktreeError("invalid run id")

    def current_commit(self) -> str:
        commit = _run_git(self.repository_root, "rev-parse", "HEAD")
        if not COMMIT_RE.fullmatch(commit):
            raise WorktreeError("Git returned an invalid commit id")
        return commit.lower()

    def ensure_main_clean(self) -> str:
        status = _run_git(
            self.repository_root,
            "status",
            "--porcelain",
            "--untracked-files=all",
        )
        ignored_prefix: str | None = None
        try:
            ignored_prefix = self.worktree_root.relative_to(
                self.repository_root
            ).as_posix().rstrip("/") + "/"
        except ValueError:
            pass
        dirty = []
        for line in status.splitlines():
            relative = line[3:].replace("\\", "/") if len(line) > 3 else line
            if ignored_prefix and relative.startswith(ignored_prefix):
                continue
            dirty.append(line)
        if dirty:
            raise WorktreeError("main workspace must be clean")
        return self.current_commit()

    def _paths(self, task_id: str, run_id: str) -> tuple[Path, str, Path]:
        self.validate_identity(task_id, run_id)
        run_slug = run_id.lower()
        task_slug = task_id.lower()
        workspace = (self.worktree_root / run_slug / task_slug).resolve()
        expected_parent = (self.worktree_root / run_slug).resolve()
        try:
            workspace.relative_to(expected_parent)
        except ValueError as exc:
            raise WorktreeError("worktree path escapes the configured root") from exc
        branch = f"orchestrator/{run_slug}/{task_slug}"
        manifest = self.manifest_root / run_slug / f"{task_slug}.json"
        return workspace, branch, manifest

    def main_assignment(self, task_id: str, run_id: str) -> WorktreeAssignment:
        self.validate_identity(task_id, run_id)
        base_commit = self.ensure_main_clean()
        return WorktreeAssignment(
            task_id,
            run_id,
            "main",
            str(self.repository_root),
            None,
            base_commit,
        )

    def create(
        self,
        task_id: str,
        title: str,
        run_id: str,
        base_commit: str,
    ) -> WorktreeAssignment:
        del title  # Task titles are intentionally not used in paths or branches.
        if not COMMIT_RE.fullmatch(base_commit):
            raise WorktreeError("base commit must be a full Git object id")
        workspace, branch, manifest = self._paths(task_id, run_id)
        if workspace.exists() or manifest.exists():
            raise WorktreeError("task worktree assignment already exists")
        workspace.parent.mkdir(parents=True, exist_ok=True)
        _run_git(
            self.repository_root,
            "worktree",
            "add",
            "-b",
            branch,
            str(workspace),
            base_commit,
        )
        assignment = WorktreeAssignment(
            task_id,
            run_id,
            "worktree",
            str(workspace),
            branch,
            base_commit.lower(),
        )
        try:
            manifest.parent.mkdir(parents=True, exist_ok=True)
            manifest.write_text(
                json.dumps(
                    {"schema_version": 1, **assignment.to_dict()},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
        except Exception:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(workspace)],
                cwd=self.repository_root,
                capture_output=True,
                text=True,
                check=False,
            )
            subprocess.run(
                ["git", "branch", "-D", branch],
                cwd=self.repository_root,
                capture_output=True,
                text=True,
                check=False,
            )
            raise
        return assignment

    def inspect(self, task_id: str, run_id: str) -> WorktreeAssignment:
        workspace, branch, manifest = self._paths(task_id, run_id)
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise WorktreeError(f"worktree ownership manifest is unavailable: {exc}") from exc
        expected = {
            "task_id": task_id,
            "run_id": run_id,
            "workspace_kind": "worktree",
            "workspace_path": str(workspace),
            "branch": branch,
        }
        if any(payload.get(key) != value for key, value in expected.items()):
            raise WorktreeError("worktree ownership manifest does not match the requested task")
        base_commit = payload.get("base_commit")
        if not isinstance(base_commit, str) or not COMMIT_RE.fullmatch(base_commit):
            raise WorktreeError("worktree ownership manifest has an invalid base commit")
        listed = _run_git(self.repository_root, "worktree", "list", "--porcelain")
        if f"worktree {workspace}" not in listed.replace("\\", "/").replace(
            str(workspace).replace("\\", "/"), str(workspace)
        ):
            normalized = listed.replace("\\", "/")
            if f"worktree {workspace.as_posix()}" not in normalized:
                raise WorktreeError("Git does not report the owned worktree")
        return WorktreeAssignment(
            task_id,
            run_id,
            "worktree",
            str(workspace),
            branch,
            base_commit.lower(),
        )

    def verify_commit(self, assignment: WorktreeAssignment, commit: str) -> None:
        if not COMMIT_RE.fullmatch(commit):
            raise WorktreeError("commit evidence must be a full Git object id")
        workspace = Path(assignment.workspace_path).resolve()
        if assignment.workspace_kind == "worktree":
            self.inspect(assignment.task_id, assignment.run_id)
        elif workspace != self.repository_root:
            raise WorktreeError("main assignment does not point to the repository root")
        actual = _run_git(workspace, "rev-parse", "HEAD")
        if actual.lower() != commit.lower():
            raise WorktreeError("commit evidence does not match workspace HEAD")

    def integrate(self, assignment: WorktreeAssignment, commit: str) -> str:
        if assignment.workspace_kind != "worktree" or assignment.branch is None:
            raise WorktreeError("only task worktrees can be integrated")
        self.verify_commit(assignment, commit)
        self.ensure_main_clean()
        before = self.current_commit()
        try:
            _run_git(
                self.repository_root,
                "merge",
                "--no-ff",
                assignment.branch,
                "-m",
                f"merge {assignment.task_id}",
            )
        except WorktreeError:
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=self.repository_root,
                capture_output=True,
                text=True,
                check=False,
            )
            if self.current_commit() != before:
                raise WorktreeError("integration failed and main HEAD changed")
            raise
        return self.current_commit()

    def cleanup(self, assignment: WorktreeAssignment, *, outcome: str) -> bool:
        if assignment.workspace_kind == "main":
            raise WorktreeError("main workspace must never be removed")
        if outcome not in {"completed", "cancelled", "failed"}:
            raise WorktreeError("unsupported cleanup outcome")
        if outcome == "failed":
            return False
        owned = self.inspect(assignment.task_id, assignment.run_id)
        workspace = Path(owned.workspace_path).resolve()
        if _run_git(workspace, "status", "--porcelain", "--untracked-files=all"):
            raise WorktreeError("owned worktree has uncommitted changes")
        current_branch = _run_git(workspace, "branch", "--show-current")
        if current_branch != owned.branch:
            raise WorktreeError("owned worktree is not on its assigned branch")
        if outcome == "completed":
            merged = set(
                _run_git(
                    self.repository_root,
                    "branch",
                    "--merged",
                    "HEAD",
                    "--format=%(refname:short)",
                ).splitlines()
            )
            if owned.branch not in merged:
                raise WorktreeError("completed worktree branch is not integrated into main")
        _run_git(self.repository_root, "worktree", "remove", str(workspace))
        if owned.branch:
            _run_git(self.repository_root, "branch", "-D", owned.branch)
        _, _, manifest = self._paths(owned.task_id, owned.run_id)
        manifest.unlink()
        return True
