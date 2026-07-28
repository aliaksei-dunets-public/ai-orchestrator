from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestrator.source_authority import SourceAuthorityError, classify_source


class SourceAuthorityTests(unittest.TestCase):
    def test_spec_and_accepted_adr_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = root / "docs/specifications/system.md"
            adr = root / "docs/adr/0001.md"
            spec.parent.mkdir(parents=True)
            adr.parent.mkdir(parents=True)
            spec.write_text("# Specification", encoding="utf-8")
            adr.write_text("**Status:** accepted", encoding="utf-8")
            self.assertTrue(classify_source(root, spec).authoritative)
            self.assertTrue(classify_source(root, adr).authoritative)

    def test_dialogue_is_not_authoritative_and_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "reports/session.md"
            report.parent.mkdir()
            report.write_text("result", encoding="utf-8")
            self.assertFalse(classify_source(root, report).authoritative)
            with self.assertRaisesRegex(SourceAuthorityError, "outside"):
                classify_source(root, Path(temporary).parent / "outside.md")
