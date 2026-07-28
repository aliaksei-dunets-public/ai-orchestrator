from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.worktree_manager import WorktreeError, WorktreeManager


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def repository(root: Path) -> str:
    git(root, "init", "-q")
    git(root, "config", "user.email", "orchestrator@example.invalid")
    git(root, "config", "user.name", "Orchestrator Test")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "base")
    return git(root, "rev-parse", "HEAD")


class WorktreeManagerTests(unittest.TestCase):
    def test_rejects_untrusted_identity_and_dirty_main(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            repository(root)
            manager = WorktreeManager(root, root / ".orchestrator/worktrees")
            with self.assertRaises(WorktreeError):
                manager.create("TASK-0001", "title", "../bad", manager.current_commit())
            (root / "dirty.txt").write_text("dirty", encoding="utf-8")
            with self.assertRaises(WorktreeError):
                manager.main_assignment("TASK-0001", "run-1")

    def test_main_assignment_uses_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            commit = repository(root)
            assignment = WorktreeManager(
                root, root / ".orchestrator/worktrees"
            ).main_assignment("TASK-0001", "run-1")
            self.assertEqual(assignment.workspace_kind, "main")
            self.assertEqual(Path(assignment.workspace_path), root.resolve())
            self.assertEqual(assignment.base_commit, commit)
