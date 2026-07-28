from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import shutil

from orchestrator.source_authority import SourceAuthorityError, classify_source


ROOT = Path(__file__).resolve().parents[2]


class SourceAuthorityTests(unittest.TestCase):
    def test_canonical_documentation_and_accepted_adr_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            spec = root / "docs/architecture/system.md"
            adr = root / "docs/adr/0001.md"
            spec.parent.mkdir(parents=True)
            adr.parent.mkdir(parents=True)
            spec.write_text("# Specification", encoding="utf-8")
            adr.write_text("**Status:** accepted", encoding="utf-8")
            self.assertTrue(classify_source(root, spec).authoritative)
            self.assertTrue(classify_source(root, adr).authoritative)

    def test_development_artifacts_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / ".orchestrator/specifications/system.md"
            source.parent.mkdir(parents=True)
            source.write_text("# Draft", encoding="utf-8")
            with self.assertRaisesRegex(SourceAuthorityError, "development artifacts"):
                classify_source(root, source)

    def test_dialogue_is_not_authoritative_and_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "reports/session.md"
            report.parent.mkdir()
            report.write_text("result", encoding="utf-8")
            self.assertFalse(classify_source(root, report).authoritative)
            with self.assertRaisesRegex(SourceAuthorityError, "outside"):
                classify_source(root, Path(temporary).parent / "outside.md")

    def test_language_policy_rejects_russian_and_mixed_graph_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copy(ROOT / "config/language-policy.json", root / "config.json")
            (root / "config").mkdir()
            (root / "config.json").replace(root / "config/language-policy.json")
            russian = root / "docs/guides/guide-ru.md"
            mixed = root / "docs/notes.md"
            russian.parent.mkdir(parents=True)
            russian.write_text(
                "---\nlanguage: ru\ntranslation_of: docs/guides/guide.md\n---\n# \u0420\u0443\u0441\u0441\u043a\u0438\u0439\n",
                encoding="utf-8",
            )
            mixed.write_text("# English\n\n\u0420\u0443\u0441\u0441\u043a\u0438\u0439 text\n", encoding="utf-8")
            with self.assertRaisesRegex(SourceAuthorityError, "English canonical"):
                classify_source(root, russian)
            with self.assertRaisesRegex(SourceAuthorityError, "English canonical"):
                classify_source(root, mixed)
