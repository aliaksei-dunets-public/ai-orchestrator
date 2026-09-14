from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from orchestrator.onboarding_workflow import _gitignore_content


ROOT = Path(__file__).resolve().parents[2]


class CoreRepositoryBoundaryTests(unittest.TestCase):
    def test_core_orchestrator_state_is_ignored_and_untracked(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("\n.orchestrator/\n", f"\n{ignore}\n")
        tracked = subprocess.run(
            ["git", "ls-files", ".orchestrator"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(tracked.returncode, 0, tracked.stderr)
        self.assertEqual(tracked.stdout.strip(), "")
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", ".orchestrator/reports/session.md"],
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(ignored.returncode, 0)

    def test_target_gitignore_remains_selective(self) -> None:
        rendered = _gitignore_content("")
        for path in (
            ".orchestrator/tasks/tasks.json",
            ".orchestrator/tasks/checkpoints/",
            ".orchestrator/memory/proposals/",
            ".orchestrator/knowledge/indexes/",
            ".orchestrator/migrations/backups/",
        ):
            self.assertIn(path, rendered)
        for path in (
            ".orchestrator/memory/entries.jsonl",
            ".orchestrator/memory/events.jsonl",
            ".orchestrator/memory/approvals.jsonl",
            ".orchestrator/knowledge/nodes.jsonl",
            ".orchestrator/knowledge/edges.jsonl",
        ):
            self.assertNotIn(path, rendered)
        self.assertNotIn("\n.orchestrator/\n", f"\n{rendered}\n")

    def test_canonical_files_have_no_workstation_paths(self) -> None:
        leaked: list[str] = []
        roots = (
            ROOT / "AGENTS.md",
            ROOT / "README.md",
            ROOT / "README.ru.md",
            ROOT / "CHANGELOG.md",
            ROOT / "ROADMAP.md",
            ROOT / "config",
            ROOT / "docs",
            ROOT / "orchestrator",
            ROOT / "profiles",
            ROOT / "registries",
            ROOT / "skills",
            ROOT / "workflows",
        )
        candidates = (
            [item for item in roots if item.is_file()]
            + [item for base in roots if base.is_dir() for item in base.rglob("*") if item.is_file()]
        )
        for path in candidates:
            if path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py"}:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "C:\\Users\\" in text or "Documents\\development" in text or "file:///" in text:
                leaked.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(leaked, [])


if __name__ == "__main__":
    unittest.main()
