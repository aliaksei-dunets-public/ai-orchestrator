from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class SerialExecutionBranchPolicyContractTests(unittest.TestCase):
    def test_workflows_declare_current_branch_serial_policy(self) -> None:
        execution = (ROOT / "workflows/task-execution.yaml").read_text(encoding="utf-8")
        backlog = (ROOT / "workflows/backlog-loop.yaml").read_text(encoding="utf-8")

        self.assertIn("workspace: primary", execution)
        self.assertIn("branch: current", execution)
        self.assertIn("task_branch_operations: forbidden", execution)
        self.assertIn("worktree_operations: forbidden", execution)
        self.assertIn("integration: forbidden", execution)
        self.assertIn("cleanup: forbidden", execution)
        self.assertIn("serial_branch_policy:", backlog)
        self.assertIn("forbidden: [task-branch, worktree, integration, cleanup]", backlog)

    def test_canonical_skill_preserves_serial_branch_and_isolates_git_lifecycle(self) -> None:
        skill = (ROOT / "skills/bundled/implementation-runner/SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Serial execution retains the user-selected current branch", skill)
        self.assertIn("Do not run `git switch`, `git checkout -b`, `git branch`,", skill)
        self.assertIn("`git worktree add`, merge, integration, or worktree cleanup", skill)
        self.assertIn("Only an explicit `isolated_parallel` assignment", skill)

    def test_runtime_contract_remains_assignment_free_for_serial(self) -> None:
        manager = (ROOT / "orchestrator/task_manager.py").read_text(encoding="utf-8")
        workflow = (ROOT / "workflows/task-execution.yaml").read_text(encoding="utf-8")

        self.assertIn('if settings.mode == "isolated_parallel":', manager)
        self.assertIn("sequence_2_plus: task-owned-worktree", workflow)


if __name__ == "__main__":
    unittest.main()
