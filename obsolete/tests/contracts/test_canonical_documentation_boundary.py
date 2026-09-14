from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.documentation import broken_local_links
from orchestrator.release import build_release_artifact


ROOT = Path(__file__).resolve().parents[2]


class CanonicalDocumentationBoundaryTests(unittest.TestCase):
    def test_canonical_docs_are_indexed_and_legacy_trees_are_absent(self) -> None:
        required = (
            "docs/INDEX.md",
            "docs/documentation-policy.md",
            "docs/architecture/orchestrator-core.md",
            "docs/architecture/task-layer.md",
            "docs/roadmap.md",
        )
        for relative in required:
            path = ROOT / relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(broken_local_links(path, root=ROOT), [], relative)
        self.assertFalse((ROOT / "docs/plans").exists())
        self.assertFalse((ROOT / "docs/specifications").exists())

    def test_release_contains_canonical_docs_but_no_local_development_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = build_release_artifact(ROOT, Path(temporary) / "artifact")
            self.assertTrue((artifact / "docs/INDEX.md").is_file())
            self.assertFalse((artifact / ".orchestrator").exists())
            self.assertFalse((artifact / "docs/plans").exists())
            self.assertFalse((artifact / "docs/specifications").exists())
