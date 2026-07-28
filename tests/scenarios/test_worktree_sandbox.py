from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.worktree_manager import WorktreeError, WorktreeManager
from tests.unit.test_worktree_manager import git, repository


class WorktreeSandboxScenarioTests(unittest.TestCase):
    def test_create_commit_integrate_and_owned_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            base = repository(root)
            manager = WorktreeManager(root, root / ".orchestrator/worktrees")
            assignment = manager.create("TASK-0002", "Unsafe / title", "run-1", base)
            workspace = Path(assignment.workspace_path)
            self.assertTrue(workspace.is_dir())
            self.assertEqual(manager.inspect("TASK-0002", "run-1"), assignment)

            (workspace / "feature.txt").write_text("feature\n", encoding="utf-8")
            git(workspace, "add", "feature.txt")
            git(workspace, "commit", "-q", "-m", "feature")
            commit = git(workspace, "rev-parse", "HEAD")
            manager.verify_commit(assignment, commit)
            integrated = manager.integrate(assignment, commit)
            self.assertEqual(git(root, "rev-parse", "HEAD"), integrated)
            self.assertTrue((root / "feature.txt").is_file())
            self.assertTrue(manager.cleanup(assignment, outcome="completed"))
            self.assertFalse(workspace.exists())

    def test_failure_is_preserved_and_main_cleanup_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            base = repository(root)
            manager = WorktreeManager(root, root / ".orchestrator/worktrees")
            assignment = manager.create("TASK-0002", "task", "run-1", base)
            self.assertFalse(manager.cleanup(assignment, outcome="failed"))
            self.assertTrue(Path(assignment.workspace_path).exists())
            with self.assertRaises(WorktreeError):
                manager.cleanup(
                    manager.main_assignment("TASK-0001", "run-2"),
                    outcome="completed",
                )

    def test_missing_manifest_blocks_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            base = repository(root)
            manager = WorktreeManager(root, root / ".orchestrator/worktrees")
            assignment = manager.create("TASK-0002", "task", "run-1", base)
            _, _, manifest = manager._paths("TASK-0002", "run-1")
            manifest.unlink()
            with self.assertRaises(WorktreeError):
                manager.cleanup(assignment, outcome="completed")

    def test_completed_cleanup_requires_integrated_clean_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            base = repository(root)
            manager = WorktreeManager(root, root / ".orchestrator/worktrees")
            assignment = manager.create("TASK-0002", "task", "run-1", base)
            workspace = Path(assignment.workspace_path)
            (workspace / "feature.txt").write_text("feature\n", encoding="utf-8")
            with self.assertRaisesRegex(WorktreeError, "uncommitted"):
                manager.cleanup(assignment, outcome="completed")
            git(workspace, "add", "feature.txt")
            git(workspace, "commit", "-q", "-m", "feature")
            with self.assertRaisesRegex(WorktreeError, "not integrated"):
                manager.cleanup(assignment, outcome="completed")
