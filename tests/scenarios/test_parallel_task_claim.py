from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator.task_manager import (
    ExecutionSettings,
    TaskManager,
    TaskManagerError,
    validate_registry,
)
from tests.unit.test_task_manager import DRAFT
from tests.unit.test_worktree_manager import git


class ParallelTaskClaimScenarioTests(unittest.TestCase):
    def _repository(self, root: Path) -> TaskManager:
        git(root, "init", "-q")
        git(root, "config", "user.email", "orchestrator@example.invalid")
        git(root, "config", "user.name", "Orchestrator Test")
        (root / ".gitignore").write_text(
            ".orchestrator/tasks/tasks.json\n"
            ".orchestrator/tasks/*.tmp\n"
            ".orchestrator/tasks/checkpoints/\n"
            ".orchestrator/worktrees/\n",
            encoding="utf-8",
        )
        tasks = root / ".orchestrator/tasks"
        (tasks / "drafts").mkdir(parents=True)
        manager = TaskManager(tasks)
        manager.initialize()
        for index in range(1, 4):
            draft = tasks / "drafts" / f"{index}.md"
            draft.write_text(
                DRAFT.replace("Test task", f"Task {index}"),
                encoding="utf-8",
            )
            manager.register(draft)
        git(root, "add", ".gitignore", ".orchestrator/tasks/contexts")
        git(root, "commit", "-q", "-m", "task contexts")
        return manager

    def test_main_bootstrap_then_unique_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            manager = self._repository(root)
            settings = ExecutionSettings(
                mode="isolated_parallel",
                run_id="run-1",
                max_workers=2,
                worktree_root=".orchestrator/worktrees",
            )
            first = manager.claim_next(settings, repository_root=root)
            self.assertEqual(first["assignment"]["sequence"], 1)
            self.assertEqual(first["assignment"]["workspace_kind"], "main")
            with self.assertRaises(TaskManagerError) as blocked:
                manager.claim_next(settings, repository_root=root)
            self.assertEqual(blocked.exception.code, "WORKSPACE_ERROR")

            (root / "bootstrap.txt").write_text("ready\n", encoding="utf-8")
            git(root, "add", "bootstrap.txt")
            git(root, "commit", "-q", "-m", "bootstrap")
            bootstrap_commit = git(root, "rev-parse", "HEAD")
            manager.complete(
                first["id"],
                commit_evidence=bootstrap_commit,
                repository_root=root,
            )

            second = manager.claim_next(settings, repository_root=root)
            third = manager.claim_next(settings, repository_root=root)
            self.assertEqual(second["assignment"]["sequence"], 2)
            self.assertEqual(third["assignment"]["sequence"], 3)
            self.assertEqual(second["assignment"]["base_commit"], bootstrap_commit)
            self.assertNotEqual(
                second["assignment"]["workspace_path"],
                third["assignment"]["workspace_path"],
            )
            self.assertEqual(validate_registry(manager.tasks_root), [])
            with self.assertRaises(TaskManagerError) as limited:
                manager.claim_next(settings, repository_root=root)
            self.assertEqual(limited.exception.code, "ACTIVE_TASK_EXISTS")

    def test_restart_recovers_assignment_from_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            manager = self._repository(root)
            settings = ExecutionSettings(
                mode="isolated_parallel",
                run_id="restart",
                max_workers=2,
                worktree_root=".orchestrator/worktrees",
            )
            task = manager.claim_next(settings, repository_root=root)
            recovered = TaskManager(manager.tasks_root).assignment(task["id"])
            self.assertEqual(recovered, task["assignment"])

    def test_active_isolated_task_cannot_be_completed_or_cleaned_early(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "repo"
            root.mkdir()
            manager = self._repository(root)
            settings = ExecutionSettings(
                mode="isolated_parallel",
                run_id="guarded",
                max_workers=2,
                worktree_root=".orchestrator/worktrees",
            )
            task = manager.claim_next(settings, repository_root=root)
            commit = git(root, "rev-parse", "HEAD")
            manager.set_status(task["id"], "waiting_user", "approval")
            with self.assertRaises(TaskManagerError) as completion:
                manager.complete(
                    task["id"],
                    commit_evidence=commit,
                    repository_root=root,
                )
            self.assertEqual(completion.exception.code, "INVALID_TRANSITION")
            with self.assertRaises(TaskManagerError) as cleanup:
                manager.cleanup_assignment(
                    task["id"],
                    repository_root=root,
                    outcome="completed",
                )
            self.assertEqual(cleanup.exception.code, "WORKSPACE_ERROR")
