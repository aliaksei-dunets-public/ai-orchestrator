from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator.documentation import broken_local_links, documentation_impact, load_documentation_map


ROOT = Path(__file__).resolve().parents[2]


class DocumentationTests(unittest.TestCase):
    def test_public_cli_change_requires_specification_and_migration(self) -> None:
        mapping = load_documentation_map(ROOT / "config/documentation-map.json")
        impacts = documentation_impact(["orchestrator/task_cli.py"], mapping)
        documents = {item.document for item in impacts}
        self.assertIn("docs/specifications/task-layer-specification-ru.md", documents)
        self.assertIn("docs/migrations/cli-contract.md", documents)

    def test_generated_and_hand_written_docs_have_owners(self) -> None:
        mapping = json.loads((ROOT / "config/documentation-map.json").read_text(encoding="utf-8"))
        self.assertTrue(all(rule.get("owner") for rule in mapping["rules"]))
        self.assertIn("generator", {rule["owner"] for rule in mapping["rules"]})
        self.assertIn("documentation-manager", {rule["owner"] for rule in mapping["rules"]})

    def test_broken_local_links_block_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            document = root / "README.md"
            document.write_text("[missing](docs/missing.md)\n", encoding="utf-8")
            self.assertEqual(broken_local_links(document, root=root), ["docs/missing.md"])
            (root / "docs").mkdir()
            (root / "docs/missing.md").write_text("ok", encoding="utf-8")
            self.assertEqual(broken_local_links(document, root=root), [])
