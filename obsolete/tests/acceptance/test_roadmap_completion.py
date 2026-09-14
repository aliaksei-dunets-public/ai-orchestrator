from __future__ import annotations

import unittest
from pathlib import Path

from orchestrator.documentation import broken_local_links


ROOT = Path(__file__).resolve().parents[2]


class RoadmapCompletionAcceptanceTests(unittest.TestCase):
    def test_versioned_roadmap_is_canonical_and_local_plans_are_not_docs(self) -> None:
        roadmap = ROOT / "docs/roadmap.md"
        index = ROOT / "docs/INDEX.md"
        self.assertTrue(roadmap.is_file())
        self.assertIn("Project roadmap", roadmap.read_text(encoding="utf-8"))
        self.assertIn("roadmap.md", index.read_text(encoding="utf-8"))
        self.assertFalse((ROOT / "docs/plans").exists())
        self.assertTrue((ROOT / ".orchestrator/plans").is_dir())
        self.assertEqual(broken_local_links(roadmap, root=ROOT), [])
